from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    BookSearchView,
    RegisterUserView,
    LoginUserView,
    RecommendBooksView,
    RefreshAccessTokenView,
    ReadingHistoryView, 
)

urlpatterns = [
    path('search/', BookSearchView.as_view(), name='book-search'),
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', LoginUserView.as_view(), name='login'),
    path('recommend/', RecommendBooksView.as_view(), name='recommend-books'),
    path('history/', ReadingHistoryView.as_view(), name='reading-history'),
    path('token/refresh/', RefreshAccessTokenView.as_view(), name='refresh-token'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
