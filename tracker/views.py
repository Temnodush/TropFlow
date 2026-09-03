from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from .models import Habit
from .permissions import IsOwnerOrReadOnly
from .serializers import HabitSerializer


class HabitPagination(LimitOffsetPagination):
    """Пагинация: 5 привычек на страницу, параметры limit/offset."""

    default_limit = 5
    max_limit = 10

    def get_paginated_response(self, data):
        """Ответ с полями count/next/previous/limit/offset/results."""
        return Response({
            'count': self.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'limit': self.get_limit(self.request),
            'offset': self.get_offset(self.request),
            'results': data,
        })


class HabitViewSet(viewsets.ModelViewSet):
    """CRUD привычек: каждый пользователь работает только со своими привычками."""

    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    pagination_class = HabitPagination

    def get_queryset(self):
        """Возвращает только привычки текущего пользователя."""
        user = self.request.user
        if not user.is_authenticated:
            return Habit.objects.none()
        return Habit.objects.filter(user=user)

    def perform_create(self, serializer):
        """Привязывает привычку к текущему пользователю."""
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """Список привычек текущего пользователя (пагинация: 5 на страницу)."""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Создание привычки."""
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Получение привычки по id (только своей)."""
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Полное редактирование привычки."""
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Частичное редактирование привычки."""
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Удаление привычки."""
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def public(self, request):
        """Список публичных привычек (доступен всем, включая неавторизованных)."""
        public_habits = Habit.objects.filter(is_public=True)
        page = self.paginate_queryset(public_habits)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(public_habits, many=True)
        return Response(serializer.data)
