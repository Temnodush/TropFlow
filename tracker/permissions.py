from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение: только владелец может редактировать/удалять.
    Для публичных привычек разрешён просмотр всем (в том числе анонимам).
    """

    def has_object_permission(self, request, view, obj):
        # Для безопасных методов (GET, HEAD, OPTIONS) доступ всегда разрешён
        if request.method in permissions.SAFE_METHODS:
            return True
        # Для остальных методов проверяем владельца
        return obj.user == request.user
