from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsPostAuthorForChanges(BasePermission):
    """
    Only the author can edit a post; the author or staff can delete it.
    Other actions on a post (reading, liking, saving) are open to any signed-in user.
    """

    def has_object_permission(self, request, view, obj):
        is_author = obj.author_id == request.user.id
        if view.action == 'destroy':
            return is_author or request.user.is_staff
        if view.action in ('update', 'partial_update'):
            return is_author
        return True


class IsCommentAuthorOrReadOnly(BasePermission):
    """
    Only the comment's author can edit it. The comment's author, the post's author
    (moderating their own post) or staff can delete it.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if obj.author_id == request.user.id:
            return True
        if request.method == 'DELETE':
            return request.user.is_staff or obj.post.author_id == request.user.id
        return False
