from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.text import tokenizer_from_json
from tensorflow.keras.preprocessing.sequence import pad_sequences
from .models import CustomUser
from .models import UserBookRecommendation
from django.utils.timezone import now
from .serializers import CustomUserSerializer  # Import serializer
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
import os

# Menentukan path relatif ke file model dan tokenizer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Mendapatkan direktori file views.py
model_path = os.path.join(BASE_DIR, 'models', 'lstm_model.h5')  # Path ke model
tokenizer_path = os.path.join(BASE_DIR, 'models', 'tokenizer.json')  # Path ke tokenizer

# Memuat model dan tokenizer
model = load_model(model_path)
with open(tokenizer_path, 'r') as f:
    tokenizer_data = f.read()
tokenizer = tokenizer_from_json(tokenizer_data)

MAX_SEQ_LEN = 100  # Sequence length used by the model

# Fungsi Registrasi Pengguna Baru
class RegisterUserView(APIView):
    def post(self, request):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response({
                    'message': 'User registered successfully',
                    'user': {
                        'email': user.email,
                        'username': user.username,
                        'id': user.id
                    }
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Fungsi Login Pengguna
class LoginUserView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Please provide both email and password'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(email=email)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': {
                        'email': user.email,
                        'username': user.username,
                        'id': user.id
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

# Fungsi Pencarian Buku di Google Books API
class BookSearchView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')
        max_results = 40  # Maksimal jumlah hasil per halaman
        start_index = int(request.query_params.get('startIndex', 0))  # Indeks awal untuk pagination
        google_books_url = f'https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}&startIndex={start_index}'
        response = requests.get(google_books_url)

        if response.status_code == 200:
            books = []
            for item in response.json().get('items', []):
                books.append({
                    'title': item['volumeInfo'].get('title', ''),
                    'author': ', '.join(item['volumeInfo'].get('authors', [])),
                    'description': item['volumeInfo'].get('description', ''),   
                    'thumbnail': item['volumeInfo'].get('imageLinks', {}).get('thumbnail', ''),
                    'preview_link': item['volumeInfo'].get('previewLink', ''),
                })
            print("Books to send:", books)  # Tambahkan log ini
            return Response(books, status=status.HTTP_200_OK)
        return Response({'error': 'Unable to fetch data'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Menambahkan View untuk Rekomendasi Buku
class RecommendBooksView(APIView):
    def get(self, request):
        input_text = request.query_params.get('input_text', '')
        if not input_text:
            return Response({'error': 'Input text is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Ambil data buku dari API Google Books
        books = fetch_books(input_text)
        if not books:
            return Response({'error': 'No books found'}, status=status.HTTP_404_NOT_FOUND)

        descriptions = [book['description'] for book in books if book['description']]
        if not descriptions:
            return Response({'error': 'No book descriptions found'}, status=status.HTTP_404_NOT_FOUND)

        # Tokenisasi dan padding input
        book_sequences = tokenizer.texts_to_sequences(descriptions)
        book_padded = pad_sequences(book_sequences, maxlen=MAX_SEQ_LEN)

        input_seq = tokenizer.texts_to_sequences([input_text])
        input_padded = pad_sequences(input_seq, maxlen=MAX_SEQ_LEN)

        # Prediksi embedding untuk input dan buku
        input_embedding = model.predict(input_padded)
        book_embeddings = model.predict(book_padded)

        # Menghitung kemiripan antara input dan buku
        similarity_scores = np.dot(book_embeddings, input_embedding.T).flatten()

        # Mengurutkan berdasarkan skor kemiripan
        recommended_books = sorted(zip(books, similarity_scores), key=lambda x: x[1], reverse=True)[:5]

        # Menambahkan data lengkap dari Google Books API (author, description, thumbnail, preview_link)
        for book, score in recommended_books:
            book['score'] = score  # Menambahkan skor ke data buku
            # Cek apakah thumbnail tersedia dari Google Books API
            thumbnail = self.get_thumbnail(book['title'])
            book['thumbnail'] = thumbnail  # Menambahkan thumbnail ke data buku
            # Ambil author, description, preview_link
            book['author'] = self.get_author(book['title'])  # Ambil author menggunakan fungsi get_author
            book['preview_link'] = self.get_preview_link(book['title'])  # Menambahkan preview_link
            book['description'] = book.get('description', 'No description available')

            # Menyimpan rekomendasi buku ke dalam database
            self.save_recommendation(request.user, book, score)

        result = [{"title": book["title"], "author": book["author"], "description": book["description"],
                   "categories": book["categories"], "score": book["score"], "thumbnail": book.get('thumbnail'),
                   "preview_link": book["preview_link"]} for book, score in recommended_books]
        
        return Response(result, status=status.HTTP_200_OK)

    def get_thumbnail(self, title):
        """ Mengambil thumbnail dari Google Books API berdasarkan judul buku """
        google_books_url = f"https://www.googleapis.com/books/v1/volumes?q={title}&maxResults=1"
        response = requests.get(google_books_url)
        if response.status_code == 200:
            data = response.json()
            if 'items' in data:
                return data['items'][0]['volumeInfo'].get('imageLinks', {}).get('thumbnail', '')
        return ''  # Return empty string if no thumbnail found

    def get_author(self, title):
        """ Mengambil author dari Google Books API berdasarkan judul buku """
        google_books_url = f"https://www.googleapis.com/books/v1/volumes?q={title}&maxResults=1"
        response = requests.get(google_books_url)
        if response.status_code == 200:
            data = response.json()
            if 'items' in data:
                return data['items'][0]['volumeInfo'].get('authors', ['Unknown Author'])[0]  # Ambil author pertama
        return 'Unknown Author'  # Jika tidak ada author ditemukan, kembalikan default 'Unknown Author'

    def get_preview_link(self, title):
        """ Mengambil previewLink dari Google Books API berdasarkan judul buku """
        google_books_url = f"https://www.googleapis.com/books/v1/volumes?q={title}&maxResults=1"
        response = requests.get(google_books_url)
        if response.status_code == 200:
            data = response.json()
            if 'items' in data:
                return data['items'][0]['volumeInfo'].get('previewLink', 'No preview available')
        return 'No preview available'  # Jika tidak ada previewLink ditemukan, kembalikan default

    def save_recommendation(self, user, book, score):
        """ Menyimpan rekomendasi buku ke dalam database """
        # Pastikan hanya satu rekomendasi buku per user untuk setiap judul buku
        recommendation, created = UserBookRecommendation.objects.get_or_create(
            user=user,
            book_title=book['title'],
            defaults={
                'author': book['author'],
                'description': book['description'],
                'thumbnail': book['thumbnail'],
                'preview_link': book['preview_link'],  # Menyimpan preview_link
                'score': score,
            }
        )
        # Jika rekomendasi sudah ada, update jika perlu
        if not created:
            recommendation.score = score
            recommendation.preview_link = book['preview_link']  # Update preview_link jika ada perubahan
            recommendation.save()

# Fungsi untuk mengambil data buku dari Google Books API
def fetch_books(query):
    API_URL = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5"
    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json()
        return [{'title': item["volumeInfo"]["title"], 'description': item["volumeInfo"].get("description", ""), 'categories': item["volumeInfo"].get("categories", [])} for item in data.get('items', [])]
    return []

class UserRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]  # Pastikan hanya user yang terautentikasi yang bisa mengakses

    def get(self, request):
        # Mengambil user yang sedang login
        user = request.user  

        # Ambil rekomendasi buku untuk user yang sedang login, urutkan berdasarkan waktu pembuatan
        recommendations = UserBookRecommendation.objects.filter(user=user).order_by('-created_at')

        # Format rekomendasi menjadi response
        result = [
            {
                'title': rec.book_title,
                'author': rec.author,
                'description': rec.description,
                'thumbnail': rec.thumbnail,
                'score': rec.score,
                'created_at': rec.created_at,  # Menambahkan waktu pembuatan (opsional)
            }
            for rec in recommendations
        ]

        return Response(result, status=200)