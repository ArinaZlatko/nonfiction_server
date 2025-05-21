from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

from .serializers import RegisterSerializer


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
            return JsonResponse({"message": "Logout successful"}, status=205)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
