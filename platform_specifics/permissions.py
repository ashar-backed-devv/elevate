from rest_framework import permissions

class AllowReadOrAdminWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS for all users (authenticated or not)
        if request.method in permissions.SAFE_METHODS:
            return True
        # Allow POST, PUT, DELETE for admins only
        return request.user and (request.user.is_staff or request.user.is_superuser)

class AllowCreateOrAdminWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Allow POST for all users (authenticated or not)
        if request.method == 'POST':
            return True
        # Allow PUT, DELETE for admins only
        return request.user and (request.user.is_staff or request.user.is_superuser)