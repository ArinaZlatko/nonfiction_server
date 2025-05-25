from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path
from .views import *


urlpatterns = [
    path('register/', RegisterView.as_view(), name='user_register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', MyTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', user_logout, name='user_logout'),
    path('genres/', GenreListView.as_view()),
    path('books/', BookListView.as_view(), name='get_books'),
    path('books/<int:id>/', BookDetailView.as_view(), name='book-detail'),
    path('books/<int:book_id>/chapter/upload/', ChapterCreateView.as_view(), name='upload_chapter'),
    path('books/<int:book_id>/chapter/<int:chapter_id>/', ChapterDetailView.as_view(), name='chapter-detail'),
    path('books/upload/', upload_book, name='upload_book'),
]
