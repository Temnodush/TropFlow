from django.contrib import admin

from .models import Habit


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'place', 'time', 'is_pleasant', 'periodicity', 'is_public')
    list_filter = ('is_pleasant', 'is_public', 'periodicity')
    search_fields = ('action', 'place', 'user__email')
    raw_id_fields = ('user', 'related_habit')
