from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TelegramChatIdSerializer, UserRegistrationSerializer


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя."""

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class SetTelegramChatIdView(APIView):
    """Привязка Telegram chat_id к текущему пользователю."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TelegramChatIdSerializer(data=request.data)
        if serializer.is_valid():
            chat_id = serializer.validated_data['chat_id']
            user = request.user
            user.telegram_chat_id = chat_id
            user.save()
            return Response(
                {'message': 'Telegram chat ID успешно привязан'},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
