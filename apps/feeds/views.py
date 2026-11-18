from django.db.models import Count, Exists, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Comment, Like, Post, SavedPost
from .permissions import IsCommentAuthorOrReadOnly, IsPostAuthorForChanges
from .serializers import (
    CommentSerializer,
    LikeSerializer,
    LikeStatusSerializer,
    PostSerializer,
    PostUpdateSerializer,
    SavedPostSerializer,
    SaveStatusSerializer,
)


class FeedPagination(CursorPagination):
    """
    Cursor pagination for infinite scroll: new posts arriving while scrolling don't shift
    pages or cause duplicates. Follow `next` until it is null.
    """

    ordering = '-created_at'
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50


class SavedPostPagination(FeedPagination):
    ordering = '-saved_at'


class CommentPagination(FeedPagination):
    ordering = 'created_at'


def _count(queryset):
    """Correlated COUNT(*) subquery, avoiding the row multiplication of several joined Counts."""
    counts = queryset.order_by().values('post').annotate(count=Count('pk')).values('count')
    return Coalesce(Subquery(counts, output_field=IntegerField()), Value(0))


def posts_for(user):
    """Posts with like/comment counts and the viewer's liked/saved state."""
    return Post.objects.select_related('author').annotate(
        like_count=_count(Like.objects.filter(post=OuterRef('pk'))),
        comment_count=_count(Comment.objects.filter(post=OuterRef('pk'))),
        is_liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=user)),
        is_saved=Exists(SavedPost.objects.filter(post=OuterRef('pk'), user=user)),
    )


@extend_schema_view(
    list=extend_schema(
        summary='Get the feed',
        description='All posts, newest first. Filter by `author` to show one user\'s posts.',
        parameters=[
            OpenApiParameter('author', OpenApiTypes.INT, description='Only posts by this user ID.'),
        ],
    ),
    retrieve=extend_schema(summary='Get a post'),
    create=extend_schema(
        summary='Create a post',
        description='Send as `multipart/form-data` to upload an image. Needs a caption, an image, or both.',
        responses={201: PostSerializer},
    ),
    partial_update=extend_schema(
        summary='Edit a post\'s caption',
        description='Author only. The image cannot be changed after posting.',
        request=PostUpdateSerializer,
        responses={200: PostSerializer},
    ),
    destroy=extend_schema(summary='Delete a post', description='Author (or staff) only.'),
)
@extend_schema(tags=['Feed'])
class PostViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated, IsPostAuthorForChanges]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = FeedPagination
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # schema generation has no real user
            return Post.objects.none()
        queryset = posts_for(self.request.user)
        if self.action == 'list' and (author := self.request.query_params.get('author')):
            if not author.isdigit():
                raise ValidationError({'author': 'Must be a user ID.'})
            queryset = queryset.filter(author_id=author)
        return queryset

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return PostUpdateSerializer
        return PostSerializer

    def _post_response(self, pk, status_code):
        post = self.get_queryset().get(pk=pk)
        return Response(PostSerializer(post, context=self.get_serializer_context()).data, status=status_code)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user)
        return self._post_response(post.pk, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()
        return self._post_response(post.pk, status.HTTP_200_OK)

    def perform_destroy(self, instance):
        instance.image.delete(save=False)
        instance.delete()

    # Likes

    def _like_status(self, post, liked):
        return Response({'liked': liked, 'like_count': Like.objects.filter(post=post).count()})

    @extend_schema(summary='Like a post', request=None, responses={200: LikeStatusSerializer})
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Like a post. Liking a post you already liked does nothing."""
        post = self.get_object()
        Like.objects.get_or_create(user=request.user, post=post)
        return self._like_status(post, liked=True)

    @extend_schema(summary='Unlike a post', request=None, responses={200: LikeStatusSerializer})
    @like.mapping.delete
    def unlike(self, request, pk=None):
        """Remove your like. Unliking a post you haven't liked does nothing."""
        post = self.get_object()
        Like.objects.filter(user=request.user, post=post).delete()
        return self._like_status(post, liked=False)

    @extend_schema(summary='List who liked a post', responses={200: LikeSerializer(many=True)})
    @action(detail=True, methods=['get'], pagination_class=FeedPagination)
    def likes(self, request, pk=None):
        post = self.get_object()
        queryset = Like.objects.filter(post=post).select_related('user')
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(LikeSerializer(page, many=True).data)

    # Saves (bookmarks, private to each user)

    @extend_schema(summary='Save a post', request=None, responses={200: SaveStatusSerializer})
    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        """Save a post to your private saved list. Saving it again does nothing."""
        post = self.get_object()
        SavedPost.objects.get_or_create(user=request.user, post=post)
        return Response({'saved': True})

    @extend_schema(summary='Unsave a post', request=None, responses={200: SaveStatusSerializer})
    @save.mapping.delete
    def unsave(self, request, pk=None):
        post = self.get_object()
        SavedPost.objects.filter(user=request.user, post=post).delete()
        return Response({'saved': False})

    @extend_schema(
        summary='List your saved posts',
        description='Most recently saved first.',
        responses={200: SavedPostSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], pagination_class=SavedPostPagination)
    def saved(self, request):
        saved_at = SavedPost.objects.filter(post=OuterRef('pk'), user=request.user).values('created_at')[:1]
        queryset = posts_for(request.user).filter(is_saved=True).annotate(saved_at=Subquery(saved_at))
        page = self.paginate_queryset(queryset)
        serializer = SavedPostSerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)


@extend_schema_view(
    get=extend_schema(summary='List comments on a post', description='Oldest first.'),
    post=extend_schema(summary='Comment on a post'),
)
@extend_schema(tags=['Comments'])
class PostCommentListView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    pagination_class = CommentPagination

    def get_post(self):
        return get_object_or_404(Post, pk=self.kwargs['post_pk'])

    def get_queryset(self):
        return Comment.objects.filter(post=self.get_post()).select_related('author')

    def perform_create(self, serializer):
        serializer.save(post=self.get_post(), author=self.request.user)


@extend_schema_view(
    get=extend_schema(summary='Get a comment'),
    patch=extend_schema(summary='Edit a comment', description='Comment author only.'),
    delete=extend_schema(
        summary='Delete a comment',
        description='The comment\'s author, the post\'s author, or staff.',
        responses={204: OpenApiResponse(description='Deleted.')},
    ),
)
@extend_schema(tags=['Comments'])
class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCommentAuthorOrReadOnly]
    queryset = Comment.objects.select_related('author', 'post')
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']
