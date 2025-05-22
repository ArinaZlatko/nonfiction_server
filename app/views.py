from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework import generics
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
import json
import os

from .models import Book
from .serializers import RegisterSerializer

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_book(request):
    user = request.user  # Теперь это точно авторизованный User

    title = request.POST.get('title')
    description = request.POST.get('description')
    cover_file = request.FILES.get('cover')

    if not title or not description or not cover_file:
        return JsonResponse({'error': 'Необходимы title, description и cover'}, status=400)

    # Создаем книгу
    book = Book.objects.create(
        title=title,
        description=description,
        author=user,
        is_visible=True,
        hidden_comment=''
    )

    # Сохраняем обложку
    book_dir = os.path.join(settings.BASE_DIR, 'static', 'books', str(book.id))
    os.makedirs(book_dir, exist_ok=True)
    cover_path = os.path.join(book_dir, 'cover.jpg')
    with open(cover_path, 'wb') as f:
        for chunk in cover_file.chunks():
            f.write(chunk)

    book.cover = f"/static/books/{book.id}/cover.jpg"
    book.save()

    return JsonResponse({'success': True, 'book_id': book.id})

