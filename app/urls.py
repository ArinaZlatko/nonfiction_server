from django.urls import path
from .views import *


urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('login/', MyTokenObtainPairView.as_view()),
    path('token/refresh/', MyTokenRefreshView.as_view()),
    path('logout/', user_logout),
    path('writers/', WriterListView.as_view()),
    path('genres/', GenreListView.as_view()),
    path('books/', BookListView.as_view()),
    path('mybooks/', MyBooksView.as_view()),
    path('books/<int:id>/edit/', BookUpdateView.as_view()),
    path('books/<int:id>/delete/', BookDeleteView.as_view()),
    path('books/<int:id>/comments/', BookCommentsListView.as_view()),
    path('books/<int:id>/comment/upload/', CreateCommentView.as_view()),
    path('books/<int:id>/', BookDetailView.as_view()),
    path('books/upload/', upload_book),
    path('books/<int:book_id>/chapter/<int:chapter_id>/edit/', ChapterUpdateView.as_view()),
    path('books/<int:book_id>/chapter/<int:chapter_id>/delete/', ChapterDeleteView.as_view()),
    path('books/<int:book_id>/chapter/<int:chapter_id>/', ChapterDetailView.as_view()),
    path('books/<int:book_id>/chapter/upload/', ChapterCreateView.as_view()),
]
