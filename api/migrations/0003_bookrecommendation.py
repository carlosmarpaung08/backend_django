# Generated by Django 5.1.5 on 2025-02-28 06:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_customuser_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('google_book_id', models.CharField(max_length=100, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('authors', models.TextField(blank=True, null=True)),
                ('published_date', models.CharField(blank=True, max_length=50, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('page_count', models.IntegerField(blank=True, null=True)),
                ('categories', models.TextField(blank=True, null=True)),
                ('thumbnail', models.URLField(blank=True, max_length=255, null=True)),
                ('preview_link', models.URLField(blank=True, max_length=255, null=True)),
                ('average_rating', models.FloatField(default=0)),
                ('recommended_at', models.DateTimeField(auto_now_add=True)),
                ('score', models.FloatField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'google_book_id')},
            },
        ),
    ]
