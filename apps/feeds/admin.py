from django.contrib import admin

from .models import Comment, Like, Post, SavedPost


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ['author', 'text', 'created_at']
    readonly_fields = ['created_at']
    raw_id_fields = ['author']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'short_caption', 'created_at']
    search_fields = ['caption', 'author__email']
    date_hierarchy = 'created_at'
    raw_id_fields = ['author']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CommentInline]

    @admin.display(description='Caption')
    def short_caption(self, obj):
        return obj.caption[:60]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'author', 'text', 'created_at']
    search_fields = ['text', 'author__email']
    raw_id_fields = ['post', 'author']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['post', 'user', 'created_at']
    raw_id_fields = ['post', 'user']


@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ['post', 'user', 'created_at']
    raw_id_fields = ['post', 'user']
