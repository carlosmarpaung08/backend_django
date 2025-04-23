from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.text import tokenizer_from_json
from tensorflow.keras.preprocessing.sequence import pad_sequences
from .models import CustomUser, ReadingHistory
from .serializers import CustomUserSerializer, ReadingHistorySerializer
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
import os

# Path relatif model dan tokenizer
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, 'models', 'autoencoder_unsupervised.h5')
tokenizer_path = os.path.join(BASE_DIR, 'models', 'tokenizer.json')

# Load model & tokenizer
model = load_model(model_path)
with open(tokenizer_path, 'r') as f:
    tokenizer_data = f.read()
tokenizer = tokenizer_from_json(tokenizer_data)

MAX_SEQ_LEN = 100

# === Utility function ===
API_KEY = "AIzaSyA9bUaNLlFeSWw_H9sFjpejBDCLlOmIxxA"

def fetch_books(query):
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5&key={API_KEY}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        return [{
            'title': item["volumeInfo"].get("title", ""),
            'description': item["volumeInfo"].get("description", ""),
            'categories': item["volumeInfo"].get("categories", [])
        } for item in data.get('items', [])]
    return []

# === Register ===
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
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# === Login ===
class LoginUserView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Please provide both email and password'}, status=status.HTTP_400_BAD_REQUEST)

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
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)

# === Book Search ===
class BookSearchView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')
        max_results = 40
        start_index = int(request.query_params.get('startIndex', 0))
        url = f'https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={max_results}&startIndex={start_index}&key={API_KEY}'
        response = requests.get(url)

        if response.status_code == 200:
            books = []
            for item in response.json().get('items', []):
                books.append({
                    'title': item['volumeInfo'].get('title', ''),
                    'author': ', '.join(item['volumeInfo'].get('authors', [])),
                    'description': item['volumeInfo'].get('description', ''),
                    'thumbnail': item['volumeInfo'].get('imageLinks', {}).get('thumbnail', ''),
                    'preview_link': item['volumeInfo'].get('previewLink', '')
                })
            return Response(books, status=status.HTTP_200_OK)
        return Response({'error': 'Unable to fetch data'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# === Recommendation View ===
class RecommendBooksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        histories = ReadingHistory.objects.filter(user=request.user).order_by('-clicked_at')[:3]
        if not histories:
            return Response({'error': 'Belum ada riwayat bacaan'}, status=status.HTTP_400_BAD_REQUEST)

        input_texts = [h.book_title for h in histories]
        input_embeddings = []

        for text in input_texts:
            seq = tokenizer.texts_to_sequences([text])
            padded = pad_sequences(seq, maxlen=MAX_SEQ_LEN)
            embedding = model.predict(padded)
            input_embeddings.append(embedding[0])

        avg_embedding = np.mean(input_embeddings, axis=0)

        # Ambil buku dari semua riwayat pencarian
        books = []
        for text in input_texts:
            books.extend(fetch_books(text))

        if not books:
            return Response({'error': 'Tidak ada buku ditemukan dari Google Books API'}, status=status.HTTP_404_NOT_FOUND)

        descriptions = [b["description"] for b in books if b.get("description")]
        if not descriptions:
            return Response({'error': 'Tidak ada deskripsi buku'}, status=status.HTTP_404_NOT_FOUND)

        book_sequences = tokenizer.texts_to_sequences(descriptions)
        book_padded = pad_sequences(book_sequences, maxlen=MAX_SEQ_LEN)
        book_embeddings = model.predict(book_padded)

        similarity_scores = np.dot(book_embeddings, avg_embedding.T).flatten()

        # Menghindari duplikasi buku berdasarkan judul
        unique_books = {}
        for book, score in zip(books, similarity_scores):
            if book["title"] not in unique_books:
                unique_books[book["title"]] = {
                    "title": book["title"],
                    "author": book["author"],
                    "description": book["description"],
                    "categories": book.get("categories", []),
                    "score": score,
                    "thumbnail": book["thumbnail"],
                    "preview_link": book["preview_link"]
                }

        # Urutkan berdasarkan score
        recommended_books = sorted(unique_books.values(), key=lambda x: x['score'], reverse=True)[:15]

        # Kirim hasil rekomendasi yang sudah disaring
        return Response(recommended_books, status=status.HTTP_200_OK)

    def get_thumbnail(self, title):
        url = f"https://www.googleapis.com/books/v1/volumes?q={title}&maxResults=1"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            if 'items' in data:
                return data['items'][0]['volumeInfo'].get('imageLinks', {}).get('thumbnail', '')
        return ''

    def get_author(self, title):
        url = f"https://www.googleapis.com/books/v1/volumes?q={title}&maxResults=1"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            if 'items' in data:
                return data['items'][0]['volumeInfo'].get('authors', ['Unknown Author'])[0]
        return 'Unknown Author'

    def get_preview_link(self, title):
        url = f"https://www.googleapis.com/books/v1/volumes?q={title}&maxResults=1"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            if 'items' in data:
                return data['items'][0]['volumeInfo'].get('previewLink', 'No preview available')
        return 'No preview available'

# === Refresh Token ===
class RefreshAccessTokenView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
            return Response({'access': new_access_token}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_400_BAD_REQUEST)

# === Reading History View ===
class ReadingHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        title = request.data.get('book_title')
        if not title:
            return Response({'error': 'Book title is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        ReadingHistory.objects.create(user=request.user, book_title=title)
        return Response({'message': 'Reading history saved'}, status=status.HTTP_201_CREATED)

    def get(self, request):
        histories = ReadingHistory.objects.filter(user=request.user).order_by('-clicked_at')
        serializer = ReadingHistorySerializer(histories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
