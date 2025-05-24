import os
from django.contrib.auth.models import AbstractUser
from django.db import models
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


# --- Путь до изображений ---
def chapter_image_upload_path(instance, filename):
    return os.path.join('books', str(instance.chapter.book.id), 'chapters', str(instance.chapter.id), filename)


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


# --- Изображения главы ---
class ChapterImage(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to=chapter_image_upload_path)

    def __str__(self):
        return f"Image for {self.chapter.title}"


# --- Комментарий ---
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True, related_name='comments')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True, blank=True, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.book and not self.chapter:
            raise ValidationError("Комментарий должен быть к книге или к главе.")

    def __str__(self):
        target = self.book or self.chapter
        return f"Комментарий от {self.user} к {target}"


# --- Оценка книги ---
class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='ratings')
    value = models.PositiveSmallIntegerField()  # 1-5

    class Meta:
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user} поставил {self.value} для {self.book}"


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
