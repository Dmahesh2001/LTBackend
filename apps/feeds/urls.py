from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CommentDetailView, PostCommentListView, PostViewSet

router = SimpleRouter()
router.register('posts', PostViewSet, basename='post')

urlpatterns = [
    *router.urls,
    path('posts/<int:post_pk>/comments/', PostCommentListView.as_view(), name='post-comments'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
]
