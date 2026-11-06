from django.urls import path
from . import views

urlpatterns = [
    path('', views.trip_list, name='trip_list'),
    path('new/', views.create_trip, name='create_trip'),
    path('<int:trip_id>/', views.trip_detail, name='trip_detail'),
]
