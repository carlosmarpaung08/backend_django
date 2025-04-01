from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

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
                    'author': ', '.join(item['volumeInfo'].get('authors', [])),\
                    'description': item['volumeInfo'].get('description', ''),   
                    'thumbnail': item['volumeInfo'].get('imageLinks', {}).get('thumbnail', ''),
                    'preview_link': item['volumeInfo'].get('previewLink', ''),
                })
            return Response(books, status=status.HTTP_200_OK)
        return Response({'error': 'Unable to fetch data'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)