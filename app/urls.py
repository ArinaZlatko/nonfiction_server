from django.urls import path
from .views import *


urlpatterns = [
    path('register/', RegisterView.as_view(), name='user_register'),
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', MyTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', user_logout, name='user_logout'),
    path('writers/', WriterListView.as_view(), name='get_writers'),
    path('genres/', GenreListView.as_view()),
    path('books/', BookListView.as_view(), name='get_books'),
    path('mybooks/', MyBooksView.as_view(), name='get_my_books'),
    path('books/<int:id>/edit/', BookUpdateView.as_view(), name='edit_book'),
    path('books/<int:id>/delete/', BookDeleteView.as_view(), name='delete_book'),
    path('books/<int:id>/comments/', BookCommentsListView.as_view(), name='book-comments-list'),
    path('books/<int:id>/comment/upload/', CreateCommentView.as_view(), name='create_comment'),
    path('books/<int:id>/', BookDetailView.as_view(), name='book-detail'),
    path('books/upload/', upload_book, name='upload_book'),
    path('books/<int:book_id>/chapter/<int:chapter_id>/edit/', ChapterUpdateView.as_view(), name='edit_chapter'),
    path('books/<int:book_id>/chapter/<int:chapter_id>/delete/', ChapterDeleteView.as_view(), name='delete_chapter'),
    path('books/<int:book_id>/chapter/<int:chapter_id>/', ChapterDetailView.as_view(), name='chapter-detail'),
    path('books/<int:book_id>/chapter/upload/', ChapterCreateView.as_view(), name='upload_chapter'),
]
