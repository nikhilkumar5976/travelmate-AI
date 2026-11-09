from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_trips, name='my_trips'),
    path('new/', views.create_trip, name='create_trip'),
    path('<int:trip_id>/', views.trip_detail, name='trip_detail'),
    path('<int:trip_id>/edit/', views.edit_trip, name='edit_trip'),
    path('<int:trip_id>/delete/', views.delete_trip, name='delete_trip'),
    path('<int:trip_id>/generate/', views.generate_itinerary_view, name='generate_itinerary'),
    path('<int:trip_id>/invite/', views.invite_member, name='invite_member'),
    path('<int:trip_id>/invitations/<int:invitation_id>/cancel/', views.cancel_invitation, name='cancel_invitation'),
    path('<int:trip_id>/leave/', views.leave_trip, name='leave_trip'),
    path('<int:trip_id>/members/<int:user_id>/remove/', views.remove_member, name='remove_member'),
    path('invitations/<uuid:token>/', views.invitation_detail, name='invitation'),
    path('invitations/<uuid:token>/accept/', views.accept_invitation, name='accept_invitation'),
    path('invitations/<uuid:token>/reject/', views.reject_invitation, name='reject_invitation'),
    path('invitations/<uuid:token>/respond/', views.respond_invitation, name='respond_invitation'),
]