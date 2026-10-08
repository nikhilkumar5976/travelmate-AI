from django.urls import path
from .views import (
    home_view, explore_view, auth_view, planner_view, landing_view,
    add_review, google_login_callback, register_user_api, login_user_api,
    generate_itinerary_view, generate_itinerary_api, chatbot_api,
    log_client_activity_api, get_activity_history_api
)

urlpatterns = [
    path('', landing_view, name='landing'),
    path('home/', home_view, name='index'),
    path('home/', home_view, name='home'),
    path('destination/<str:destination_id>/add-review/', add_review, name='add_review'),
    path('explore/', explore_view, name='explore'),
    path('auth/', auth_view, name='auth'),
    path('auth/callback/', google_login_callback, name='google_login_callback'),
    path('api/auth/register/', register_user_api, name='register_user_api'),
    path('api/auth/login/', login_user_api, name='login_user_api'),
    path('planner/', planner_view, name='planner'),
    # Dynamic Gemini AI Travel Planner Endpoint (GET /api/generate-itinerary/?destination=Mathura&days=3)
    path('api/generate-itinerary/', generate_itinerary_view, name='generate_itinerary'),
    path('api/ai/planner/', generate_itinerary_api, name='api_generate_itinerary'),
    path('api/ai/chat/', chatbot_api, name='api_chatbot'),

    # User Activity Telemetry & History Endpoints
    path('api/activity/log/', log_client_activity_api, name='log_client_activity_api'),
    path('api/activity/history/', get_activity_history_api, name='get_activity_history_api'),
]

