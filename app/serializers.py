from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from django.conf import settings
import os
from .models import *


User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, validators=[UniqueValidator(queryset=User.objects.all())])
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name', 'surname', 'role')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user
    
    
class BookCreateSerializer(serializers.ModelSerializer):
    genres = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.filter(is_active=True), many=True
    )
    cover = serializers.ImageField(write_only=True)

    class Meta:
        model = Book
        fields = ['title', 'description', 'cover', 'genres']

    def create(self, validated_data):
        genres = validated_data.pop('genres')
        cover_file = validated_data.pop('cover')
        author = self.context['request'].user

        # Создаем книгу
        book = Book.objects.create(
            author=author,
            is_visible=True,
            hidden_comment='',
            **validated_data
        )

        # Сохраняем обложку вручную
        book_dir = os.path.join(settings.BASE_DIR, 'static', 'books', str(book.id))
        os.makedirs(book_dir, exist_ok=True)
        cover_path = os.path.join(book_dir, 'cover.jpg')

        with open(cover_path, 'wb') as f:
            for chunk in cover_file.chunks():
                f.write(chunk)

        book.cover = f"/static/books/{book.id}/cover.jpg"
        book.save()

        book.genres.set(genres)
        return book


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'surname']


class BookSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True)
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ['id', 'title', 'description', 'author', 'genres', 'cover']