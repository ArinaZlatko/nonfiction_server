from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path
from .views import RegisterView, user_logout


urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='user_register'),
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/logout/', user_logout, name='user_logout'),
]
