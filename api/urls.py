from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import BookSearchView, RegisterUserView, LoginUserView, RecommendBooksView

urlpatterns = [
    path('search/', BookSearchView.as_view(), name='book-search'),
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', LoginUserView.as_view(), name='login'),
    path('recommend/', RecommendBooksView.as_view(), name='recommend-books'),  # Menambahkan URL untuk rekomendasi buku
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
