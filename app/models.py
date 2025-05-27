import os
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.conf import settings


# --- Пользователь  ---
class User(AbstractUser):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    surname = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)

    ROLE_CHOICES = (
        ('reader', 'Reader'),
        ('writer', 'Writer'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='reader')

    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"


# --- Жанр ---
class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


# --- Книга ---
class Book(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    genres = models.ManyToManyField(Genre, related_name='books')
    cover = models.CharField(max_length=255, blank=True)

    is_visible = models.BooleanField(default=True)
    hidden_comment = models.TextField(blank=True)

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if not self.genres.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError("У книги должен быть хотя бы один жанр.")


# --- Глава ---
class Chapter(models.Model):
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=255)
    content = models.TextField()
    order = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('book', 'order')
        ordering = ['order']

    def __str__(self):
        return f"{self.book.title} - {self.title}"


# --- Путь до изображений ---
def chapter_image_upload_path(instance, filename):
    return os.path.join('books', str(instance.chapter.book.id), 'chapters', str(instance.chapter.id), filename)


# --- Изображения ---
class ChapterImage(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=chapter_image_upload_path)
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.chapter.title} - Image {self.order}: {self.caption or self.image.name}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    rating = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')

    def clean(self):
        if not self.content:
            raise ValidationError("Комментарий не может быть пустым.")
        if self.rating is None:
            raise ValidationError("Оценка обязательна.")
        if not (1 <= self.rating <= 5):
            raise ValidationError("Оценка должна быть от 1 до 5.")

    def __str__(self):
        return f"Комментарий от {self.user} к книге '{self.book}' с оценкой {self.rating}"


# --- Избранное ---
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='favorited_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')


# --- Уведомление ---
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Уведомление для {self.user}: {self.message[:50]}"
