from django.urls import path
from .views import RegisterView, SetTelegramChatIdView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('set-chat-id/', SetTelegramChatIdView.as_view(), name='set_chat_id'),
]
