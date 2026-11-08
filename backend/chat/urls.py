from django.urls import path
from . import views

urlpatterns = [
    path('<int:trip_id>/', views.trip_chat, name='trip_chat'),
    path('<int:trip_id>/messages/', views.chat_messages_api, name='chat_messages_api'),
]
