from rest_framework import serializers

from apps.users.models import User

from .models import Comment, Like, Post


class AuthorSerializer(serializers.ModelSerializer):
    """Public view of a user. Never exposes email or phone number."""

    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'full_name']
        read_only_fields = fields


class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    like_count = serializers.IntegerField(read_only=True, default=0)
    comment_count = serializers.IntegerField(read_only=True, default=0)
    is_liked = serializers.BooleanField(read_only=True, default=False, help_text='Whether you liked this post.')
    is_saved = serializers.BooleanField(read_only=True, default=False, help_text='Whether you saved this post.')

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'caption', 'image',
            'like_count', 'comment_count', 'is_liked', 'is_saved',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {'image': {'help_text': 'JPG, PNG or WebP, up to 10 MB.'}}

    def validate(self, attrs):
        if not attrs.get('caption', '').strip() and not attrs.get('image'):
            raise serializers.ValidationError('A post needs a caption, an image, or both.')
        return attrs


class PostUpdateSerializer(serializers.ModelSerializer):
    """Only the caption can be edited after posting."""

    class Meta:
        model = Post
        fields = ['caption']

    def validate_caption(self, value):
        if not value.strip() and not self.instance.image:
            raise serializers.ValidationError('A post without an image needs a caption.')
        return value


class SavedPostSerializer(PostSerializer):
    saved_at = serializers.DateTimeField(read_only=True)

    class Meta(PostSerializer.Meta):
        fields = [*PostSerializer.Meta.fields, 'saved_at']


class LikeSerializer(serializers.ModelSerializer):
    """A user who liked a post."""

    user = AuthorSerializer(read_only=True)
    liked_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Like
        fields = ['user', 'liked_at']


class LikeStatusSerializer(serializers.Serializer):
    liked = serializers.BooleanField()
    like_count = serializers.IntegerField()


class SaveStatusSerializer(serializers.Serializer):
    saved = serializers.BooleanField()


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'post', 'created_at', 'updated_at']

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Comment cannot be empty.')
        return value
