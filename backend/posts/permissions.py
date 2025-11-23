from rest_framework import permissions


# * This IsAdminOrReadOnly name means: if you're an admin, you have permission to access all the view, but if you're not an admin, you can only read data (GET http method) using this view.
class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read access to any user (including anonymous),
    but only allow write (POST, PUT, PATCH, DELETE) access to users
    who are staff (admins).
    """

    def has_permission(self, request, view):
        # 1. Check for Read-Only Permissions (GET, HEAD, OPTIONS)
        # permissions.SAFE_METHODS is a tuple containing ('GET', 'HEAD', 'OPTIONS').
        if request.method in permissions.SAFE_METHODS:
            # If the request method is safe, permission is granted to everyone.
            return True

        # 2. Check for Write Permissions (POST, PUT, PATCH, DELETE)
        # If the method is NOT safe, the user must be authenticated and be a staff member.
        return request.user and request.user.is_staff


class IsAuthorOrAdmin(permissions.BasePermission):
    """
    Allow access to the object only if the user is the author OR is an admin.
    This is used for PUT/PATCH/DELETE on existing comments.
    """

    def has_object_permission(self, request, view, obj):
        # Admins (staff) always have permission
        if request.user and request.user.is_staff:
            return True

        # Otherwise, only the object's author has permission
        return obj.author == request.user
