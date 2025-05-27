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
    
    
# Метод сохранения обложки книги
def save_cover_file(book, cover_file):
    book_dir = os.path.join(settings.BASE_DIR, 'static', 'books', str(book.id))
    os.makedirs(book_dir, exist_ok=True)
    cover_path = os.path.join(book_dir, 'cover.jpg')

    with open(cover_path, 'wb') as f:
        for chunk in cover_file.chunks():
            f.write(chunk)

    book.cover = f"/static/books/{book.id}/cover.jpg"
    book.save()
    

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']
        
        
class BookCESerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    genre_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Genre.objects.all(),
        write_only=True,
        source='genres'
    )
    cover = serializers.ImageField(required=False, allow_null=True)  # <- Это ключевой момент

    class Meta:
        model = Book
        fields = ['title', 'description', 'cover', 'genres', 'genre_ids']

    def create(self, validated_data):
        genres = validated_data.pop('genres', [])
        cover_file = validated_data.pop('cover', None)
        author = self.context['request'].user

        book = Book.objects.create(
            author=author,
            is_visible=True,
            hidden_comment='',
            **validated_data
        )

        if cover_file:
            save_cover_file(book, cover_file)

        if genres:
            book.genres.set(genres)

        return book

    def update(self, instance, validated_data):
        genres = validated_data.pop('genres', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if genres is not None:
            instance.genres.set(genres)

        instance.save()
        return instance


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
        
        
class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['id', 'title', 'order']


class BookDetailSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    genres = GenreSerializer(many=True)
    chapters = ChapterSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = ['id', 'title', 'description', 'author', 'genres', 'cover', 'chapters']
    
    
class ChapterImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChapterImage
        fields = ['id', 'image', 'caption', 'order']
        extra_kwargs = {
            'image': {'read_only': True}
        }

    def to_internal_value(self, data):
        return {
            'id': data.get('id'),
            'caption': data.get('caption'),
            'order': data.get('order')
        }
 
        
class ChapterUploadSerializer(serializers.Serializer):
    title = serializers.CharField()
    content = serializers.CharField()


class ChapterUpdateSerializer(serializers.ModelSerializer):
    images = ChapterImageSerializer(many=True)

    class Meta:
        model = Chapter
        fields = ['id', 'title', 'content', 'images']

    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.save()

        images_data = validated_data.get('images', [])

        for img_data in images_data:
            image_id = img_data.get('id')
            try:
                chapter_image = ChapterImage.objects.get(id=image_id, chapter=instance)
                chapter_image.caption = img_data.get('caption', chapter_image.caption)
                chapter_image.order = img_data.get('order', chapter_image.order)
                chapter_image.save()
            except ChapterImage.DoesNotExist:
                continue

        return instance


class ChapterDetailSerializer(serializers.ModelSerializer):
    images = ChapterImageSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'title', 'content', 'order', 'images']
