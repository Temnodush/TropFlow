from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Регистрация пользователя по email и паролю."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'telegram_chat_id']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Пароли не совпадают.'})
        try:
            validate_password(data['password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        telegram_chat_id = validated_data.pop('telegram_chat_id', None)
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            telegram_chat_id=telegram_chat_id,
        )


class TelegramChatIdSerializer(serializers.Serializer):
    """Сериализатор для привязки Telegram chat_id."""

    chat_id = serializers.CharField(max_length=100)
