from rest_framework import serializers

from .models import Habit


class HabitSerializer(serializers.ModelSerializer):
    """Сериализатор привычки с валидацией бизнес-правил."""

    class Meta:
        model = Habit
        fields = [
            'id', 'user', 'place', 'time', 'action',
            'is_pleasant', 'related_habit', 'periodicity',
            'reward', 'time_to_complete', 'is_public',
        ]
        read_only_fields = ['user']  # пользователь проставляется из request

    def _merged(self, attrs, field, default=None):
        """Значение поля с учётом частичного обновления (PATCH)."""
        if field in attrs:
            return attrs[field]
        if self.instance is not None:
            return getattr(self.instance, field, default)
        return default

    def validate(self, attrs):
        """Валидация бизнес-правил (учитывает сохранённые значения при PATCH)."""
        reward = self._merged(attrs, 'reward')
        related_habit = self._merged(attrs, 'related_habit')
        is_pleasant = self._merged(attrs, 'is_pleasant', False)
        time_to_complete = self._merged(attrs, 'time_to_complete', 0)
        periodicity = self._merged(attrs, 'periodicity', 1)

        # Нельзя одновременно указывать вознаграждение и связанную привычку
        if reward and related_habit:
            raise serializers.ValidationError(
                {'non_field_errors': 'Нельзя одновременно указывать вознаграждение и связанную привычку.'}
            )

        # Время выполнения не больше 120 секунд
        if time_to_complete > 120:
            raise serializers.ValidationError(
                {'time_to_complete': 'Время выполнения не должно превышать 120 секунд.'}
            )

        # Связанная привычка должна быть приятной
        if related_habit and not related_habit.is_pleasant:
            raise serializers.ValidationError(
                {'related_habit': 'Связанная привычка должна быть приятной.'}
            )

        # У приятной привычки не может быть вознаграждения или связанной привычки
        if is_pleasant:
            if reward:
                raise serializers.ValidationError(
                    {'reward': 'Приятная привычка не может иметь вознаграждение.'}
                )
            if related_habit:
                raise serializers.ValidationError(
                    {'related_habit': 'Приятная привычка не может иметь связанную привычку.'}
                )

        # Периодичность от 1 до 7 дней
        if not 1 <= periodicity <= 7:
            raise serializers.ValidationError(
                {'periodicity': 'Периодичность должна быть от 1 до 7 дней.'}
            )

        return attrs

    def create(self, validated_data):
        # Автоматически подставляем пользователя из контекста (передаётся во view)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
