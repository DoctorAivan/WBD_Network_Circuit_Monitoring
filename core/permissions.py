from rest_framework.permissions import BasePermission

# Validate authenticated permission
class Authenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

# Validate visitors permission
class Visitors(BasePermission):
    def has_permission(self, request, view):
        return not request.user.is_authenticated

# Check user permission
def check_user_permission(user, permissions):
    if user and user.is_authenticated:
        return True
    else:
        return False
