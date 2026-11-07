from django.urls import path
from . import views

urlpatterns = [
    path('chatbot/', views.chatbot_reply, name='chatbot_reply'),
]