from django.contrib import admin
from .models import (
    Destination, Review, UserLoginLog,
    UserActivityLog, GeneratedItinerary, ChatMessageLog, SearchQueryLog
)

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'rating', 'get_reviews_count')
    list_filter = ('category',)
    search_fields = ('title', 'category', 'description')
    ordering = ('title',)

    def get_reviews_count(self, obj):
        return obj.reviews.count()
    get_reviews_count.short_description = 'Reviews'

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('username', 'destination', 'rating', 'created_at')
    list_filter = ('rating', 'created_at', 'destination')
    search_fields = ('username', 'comment')
    ordering = ('-created_at',)

@admin.register(UserLoginLog)
class UserLoginLogAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "formatted_login_time_ist")
    search_fields = ("email", "name")
    ordering = ("-login_time",)

    def formatted_login_time_ist(self, obj):
        return obj.formatted_login_time or str(obj.login_time)
    formatted_login_time_ist.short_description = "Login Time (IST)"
    formatted_login_time_ist.admin_order_field = "login_time"

@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('username', 'user_email', 'action_type', 'action_description', 'path', 'ip_address', 'created_at')
    list_filter = ('action_type',)
    search_fields = ('username', 'user_email', 'action_description', 'path', 'ip_address')
    ordering = ('-created_at',)

@admin.register(GeneratedItinerary)
class GeneratedItineraryAdmin(admin.ModelAdmin):
    list_display = ('destination', 'days', 'username', 'ai_engine', 'created_at')
    list_filter = ('destination', 'days')
    search_fields = ('destination', 'username', 'user_email')
    ordering = ('-created_at',)

@admin.register(ChatMessageLog)
class ChatMessageLogAdmin(admin.ModelAdmin):
    list_display = ('username', 'user_email', 'user_message_snippet', 'created_at')
    search_fields = ('username', 'user_email', 'user_message', 'bot_response')
    ordering = ('-created_at',)

    def user_message_snippet(self, obj):
        return (obj.user_message[:50] + '...') if len(obj.user_message) > 50 else obj.user_message
    user_message_snippet.short_description = "Message"

@admin.register(SearchQueryLog)
class SearchQueryLogAdmin(admin.ModelAdmin):
    list_display = ('query', 'category', 'results_count', 'username', 'created_at')
    search_fields = ('query', 'username', 'user_email')
    ordering = ('-created_at',)


