from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.generics import ListAPIView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import MultiPartParser
from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
import json
import os

from .models import *
from .serializers import *

User = get_user_model()

# Регистрация
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MyTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
    
# Выход
@csrf_exempt
def user_logout(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get("refresh")

            if token is None:
                return JsonResponse({"error": "Refresh token is required"}, status=400)
            
            token_obj = RefreshToken(token)
            token_obj.blacklist()
            return JsonResponse({}, status=205)
        except Exception as e:
            return JsonResponse({}, status=205)


class GenreListView(APIView):
    def get(self, request):
        genres = Genre.objects.filter(is_active=True)
        serializer = GenreSerializer(genres, many=True)
        return Response(serializer.data)
    
    
# --- Добавление книги ---
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_book(request):
    serializer = BookCESerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        book = serializer.save()
        return JsonResponse({'success': True, 'book_id': book.id})
    else:
        return JsonResponse({'error': serializer.errors}, status=400)
    
        
# --- Редактирование книги ---
class BookUpdateView(generics.UpdateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookCESerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        book = self.get_object()
        if book.author != self.request.user:
            raise PermissionDenied("Вы не являетесь автором этой книги.")
        return serializer.save()


# --- Отображение карточкой ---
class BookListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        books = Book.objects.filter(is_visible=True).select_related('author').prefetch_related('genres')
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)
    

# --- Книги авторизованного пользователя ---
class MyBooksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        books = Book.objects.filter(author=request.user).select_related('author').prefetch_related('genres')
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)


# --- Детальное отображение ---
class BookDetailView(generics.RetrieveAPIView):
    queryset = Book.objects.prefetch_related('genres', 'chapters').select_related('author')
    serializer_class = BookDetailSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        is_owner = request.user.is_authenticated and instance.author == request.user
        data['is_owner'] = is_owner

        return Response(data)
    

# --- Удаление книги ---
class BookDeleteView(generics.DestroyAPIView):
    queryset = Book.objects.all()
    serializer_class = BookDetailSerializer
    lookup_field = 'id'
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("Вы не можете удалить эту книгу.")
        return super().perform_destroy(instance)
    
    
# --- Создание главы ---
class ChapterCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, book_id):
        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return Response({'detail': 'Книга не найдена'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChapterUploadSerializer(data=request.data)
        if serializer.is_valid():
            title = serializer.validated_data['title']
            content = serializer.validated_data['content']

            # Найдём следующий order
            last_order = Chapter.objects.filter(book=book).aggregate(models.Max('order'))['order__max'] or 0
            order = last_order + 1

            # Создаём главу с уникальным порядком
            chapter = Chapter.objects.create(book=book, title=title, content=content, order=order)

            images = request.FILES.getlist('images')
            captions = request.data.getlist('captions')
            orders = request.data.getlist('orders')

            chapter_dir = os.path.join(settings.BASE_DIR, 'static', 'books', str(book.id), 'chapters', str(chapter.id))
            os.makedirs(chapter_dir, exist_ok=True)

            for i, image in enumerate(images):
                caption = captions[i] if i < len(captions) else ''
                image_order = int(orders[i]) if i < len(orders) and orders[i].isdigit() else None

                if image_order is None:
                    last_image_order = ChapterImage.objects.filter(chapter=chapter).aggregate(models.Max('order'))['order__max'] or 0
                    image_order = last_image_order + 1

                image_path = os.path.join(chapter_dir, image.name)
                with open(image_path, 'wb+') as f:
                    for chunk in image.chunks():
                        f.write(chunk)

                relative_path = f"/static/books/{book.id}/chapters/{chapter.id}/{image.name}"

                ChapterImage.objects.create(
                    chapter=chapter,
                    image=relative_path,
                    caption=caption,
                    order=image_order
                )

            return Response({
                'id': chapter.id,
                'message': 'Глава успешно добавлена'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- Просмотр главы ---
class ChapterDetailView(generics.RetrieveAPIView):
    serializer_class = ChapterDetailSerializer

    def get_queryset(self):
        return Chapter.objects.prefetch_related('images')

    def get_object(self):
        queryset = self.get_queryset()
        book_id = self.kwargs['book_id']
        chapter_id = self.kwargs['chapter_id']
        try:
            return queryset.get(id=chapter_id, book_id=book_id)
        except Chapter.DoesNotExist:
            raise NotFound('Chapter not found')
        

# --- Редактирование главы ---
class ChapterUpdateView(generics.UpdateAPIView):
    serializer_class = ChapterUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chapter.objects.filter(book__id=self.kwargs['book_id'])

    def get_object(self):
        try:
            chapter = self.get_queryset().get(id=self.kwargs['chapter_id'])
            if chapter.book.author != self.request.user:
                raise PermissionDenied("Вы не можете редактировать эту главу.")
            return chapter
        except Chapter.DoesNotExist:
            raise NotFound("Глава не найдена")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# --- Удаление главы ---
class ChapterDeleteView(generics.DestroyAPIView):
    serializer_class = ChapterDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chapter.objects.filter(book__id=self.kwargs['book_id'])

    def get_object(self):
        try:
            chapter = self.get_queryset().get(id=self.kwargs['chapter_id'])
            if chapter.book.author != self.request.user:
                raise PermissionDenied("Вы не можете удалить эту главу.")
            return chapter
        except Chapter.DoesNotExist:
            raise NotFound("Глава не найдена")
 

# --- Создание комментария ---
class CreateCommentView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(book__id=self.kwargs['book_id'])

    def perform_create(self, serializer):
        book_id = self.kwargs['id']
        serializer.save(user=self.request.user, book_id=book_id)


# --- Комментарии к книге ---
class BookCommentsListView(ListAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        book_id = self.kwargs.get('id')
        return Comment.objects.filter(book_id=book_id).order_by('-created_at')
    

# --- Редактирование комментария ---
class EditCommentView(generics.UpdateAPIView):
    serializer_class = EditCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        book_id = self.kwargs.get('book_id')
        comment_id = self.kwargs.get('comment_id')

        try:
            comment = Comment.objects.get(id=comment_id, book__id=book_id)
        except Comment.DoesNotExist:
            raise NotFound("Комментарий не найден.")

        if comment.user != self.request.user:
            raise PermissionDenied("Вы не можете редактировать чужой комментарий.")

        return comment


# --- Удаление комментария ---
class DeleteCommentView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        book_id = self.kwargs.get('book_id')
        comment_id = self.kwargs.get('comment_id')

        try:
            comment = Comment.objects.get(id=comment_id, book__id=book_id)
        except Comment.DoesNotExist:
            raise NotFound("Комментарий не найден.")

        if comment.user != self.request.user:
            raise PermissionDenied("Вы не можете удалить чужой комментарий.")

        return comment
