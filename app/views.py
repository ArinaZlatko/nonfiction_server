from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import BasePermission
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
from django.db.models import Count, Q
import json
import os

from .models import *
from .serializers import *

User = get_user_model()
    

# --- Проверка роли ---
class IsWriter(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'writer'
    
    
# --- Добавление роли на клиент ---
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


# --- Логика на обновление токена ---
class MyTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
   
    
# Регистрация
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


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

    
# --- Добавление книги ---
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsWriter])
def upload_book(request):
    serializer = BookCESerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        book = serializer.save()
        return JsonResponse({'success': True, 'book_id': book.id})
    else:
        return JsonResponse({'error': serializer.errors}, status=400)
    
        
# --- Редактирование книги ---
class BookUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsWriter]
    queryset = Book.objects.all()
    serializer_class = BookCESerializer
    lookup_field = 'id'

    def perform_update(self, serializer):
        book = self.get_object()
        if book.author != self.request.user:
            raise PermissionDenied("Вы не являетесь автором этой книги.")
        return serializer.save()


# --- Писатели ---
class WriterListView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        search = request.query_params.get('search', '')

        writers = User.objects.annotate(book_count=Count('book')) \
                              .filter(role='writer', book_count__gt=0)

        if search:
            writers = writers.filter(first_name__icontains=search)

        writers = writers.order_by('first_name')

        serializer = WriterSerializer(writers, many=True)
        return Response(serializer.data)
    

# --- Все жанры ---
class GenreListView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        genres = Genre.objects.filter(is_active=True)
        serializer = GenreSerializer(genres, many=True)
        return Response(serializer.data)
    

# --- Все книги ---
class BookListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        books = Book.objects.filter(is_visible=True).select_related('author').prefetch_related('genres')

        genre_ids = request.query_params.getlist('genre')
        author_id = request.query_params.get('author')
        search = request.query_params.get('search')
        sort_field = request.query_params.get('sort_field')
        sort_direction = request.query_params.get('sort_direction', 'asc')
        order_prefix = '' if sort_direction == 'asc' else '-'

        if genre_ids:
            books = books.filter(genres__id__in=genre_ids) \
                         .annotate(matched_genres=Count('genres', filter=Q(genres__id__in=genre_ids), distinct=True)) \
                         .filter(matched_genres=len(genre_ids))

        if author_id:
            books = books.filter(author__id=author_id)

        if search:
            books = books.filter(
                Q(title__icontains=search) |
                Q(author__first_name__icontains=search) |
                Q(author__last_name__icontains=search) |
                Q(author__surname__icontains=search)
            )

        if sort_field == 'rating':
            books = books.annotate(average_rating=Avg('comments__rating'))
            books = books.filter(average_rating__isnull=False)

        if sort_field:
            if sort_field == 'rating':
                books = books.order_by(f"{order_prefix}average_rating")
            elif sort_field == 'date':
                books = books.order_by(f"{order_prefix}created_at")
            else:
                books = books.order_by(f"{order_prefix}{sort_field}")

        books = books.distinct()

        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)


# --- Книги авторизованного пользователя ---
class MyBooksView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]

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
    permission_classes = [IsAuthenticated, IsWriter]
    queryset = Book.objects.all()
    serializer_class = BookDetailSerializer
    lookup_field = 'id'

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("Вы не можете удалить эту книгу.")
        return super().perform_destroy(instance)
    
    
# --- Создание главы ---
class ChapterCreateView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]
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
    permission_classes = [IsAuthenticated, IsWriter]
    serializer_class = ChapterUpdateSerializer

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
    permission_classes = [IsAuthenticated, IsWriter]
    serializer_class = ChapterDetailSerializer

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
class BookCommentsListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, id):
        all_comments = Comment.objects.filter(book_id=id).order_by('-created_at')
        current_user_comment = None

        if request.user.is_authenticated:
            try:
                current_user_comment_obj = all_comments.get(user=request.user)
                current_user_comment = CommentSerializer(current_user_comment_obj).data
                all_comments = all_comments.exclude(user=request.user)
            except Comment.DoesNotExist:
                pass

        other_comments_serialized = CommentSerializer(all_comments, many=True).data

        return Response({
            "user_comment": current_user_comment,
            "other_comments": other_comments_serialized
        })
    

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
