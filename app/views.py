from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework.views import APIView
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
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_book(request):
    serializer = BookCreateSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        book = serializer.save()
        return JsonResponse({'success': True, 'book_id': book.id})
    else:
        return JsonResponse({'error': serializer.errors}, status=400)


class BookListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        books = Book.objects.filter(is_visible=True).select_related('author').prefetch_related('genres')
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)