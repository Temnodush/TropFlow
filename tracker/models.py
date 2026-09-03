from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Habit(models.Model):
    """Модель привычки."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='habits',
        verbose_name='Пользователь'
    )
    place = models.CharField(
        max_length=255,
        verbose_name='Место'
    )
    time = models.TimeField(
        verbose_name='Время выполнения'
    )
    action = models.CharField(
        max_length=255,
        verbose_name='Действие'
    )
    is_pleasant = models.BooleanField(
        default=False,
        verbose_name='Приятная привычка'
    )
    related_habit = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Связанная привычка',
        help_text='Может быть указана только для полезных привычек'
    )
    periodicity = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Периодичность (дни)',
        help_text='Количество дней между выполнениями (1–7)'
    )
    reward = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Вознаграждение'
    )
    time_to_complete = models.PositiveSmallIntegerField(
        verbose_name='Время на выполнение (сек)',
        help_text='Не более 120 секунд'
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name='Публичная привычка'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_reminded = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Привычка'
        verbose_name_plural = 'Привычки'
        ordering = ['-id']

    def __str__(self):
        return f'{self.user} - {self.action}'

    def clean(self):
        """
        Валидация на уровне модели.
        """
        # 1. Нельзя одновременно заполнять reward и related_habit
        if self.reward and self.related_habit:
            raise ValidationError(
                'Нельзя одновременно указывать вознаграждение и связанную привычку.'
            )

        # 2. Время выполнения не больше 120 секунд
        if self.time_to_complete > 120:
            raise ValidationError(
                'Время выполнения не должно превышать 120 секунд.'
            )

        # 3. Связанная привычка должна быть приятной (если указана)
        if self.related_habit and not self.related_habit.is_pleasant:
            raise ValidationError(
                'Связанная привычка должна быть приятной.'
            )

        # 4. У приятной привычки не может быть вознаграждения или связанной привычки
        if self.is_pleasant:
            if self.reward:
                raise ValidationError(
                    'Приятная привычка не может иметь вознаграждение.'
                )
            if self.related_habit:
                raise ValidationError(
                    'Приятная привычка не может иметь связанную привычку.'
                )

        # 5. Периодичность от 1 до 7 дней
        if not (1 <= self.periodicity <= 7):
            raise ValidationError(
                'Периодичность должна быть от 1 до 7 дней.'
            )

    def save(self, *args, **kwargs):
        # Вызываем валидацию перед сохранением
        self.full_clean()
        super().save(*args, **kwargs)
