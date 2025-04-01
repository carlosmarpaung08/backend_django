from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


# Model untuk menyimpan rekomendasi buku per pengguna
class UserBookRecommendation(models.Model):  
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # Relasi dengan user
    book_title = models.CharField(max_length=255)  # Judul buku
    author = models.CharField(max_length=255)  # Penulis buku
    description = models.TextField()  # Deskripsi buku
    thumbnail = models.URLField(null=True, blank=True)  # Thumbnail gambar buku
    score = models.FloatField()  # Skor kemiripan atau relevansi buku
    created_at = models.DateTimeField(auto_now_add=True)  # Tanggal rekomendasi dibuat
    preview_link = models.URLField(max_length=255, null=True, blank=True)  # Menambahkan preview_link

    class Meta:
        unique_together = ['user', 'book_title']  # Pastikan satu buku hanya direkomendasikan satu kali per pengguna

    def __str__(self):
        return f"{self.book_title} - {self.user.email}"
