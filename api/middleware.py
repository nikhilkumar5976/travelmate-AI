import logging
from django.shortcuts import redirect
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class LoginRequiredAccessMiddleware:
    """
    Middleware to restrict access across TravelMate AI:
    Unauthenticated / unverified visitors can ONLY access:
    1. The public landing page ('/' or '')
    2. Authentication pages ('/auth/', '/auth/callback/')
    3. Django-allauth workflows ('/accounts/...')
    4. Authentication APIs ('/api/auth/...')
    5. Static files ('/static/...') and media assets ('/media/...')
    6. Django Admin ('/admin/...')
    7. Standard browser assets ('/favicon.ico', '/robots.txt')

    Any attempt to access internal website pages (such as /home/, /explore/, /planner/,
    destination reviews, travel itinerary generators, etc.) is blocked until the
    user completes login verification, redirecting them to the landing page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # 1. Authenticated users have full access to the website
        if request.user.is_authenticated:
            return self.get_response(request)

        # 2. Whitelist of paths accessible to unauthenticated visitors
        # Landing page
        if path == '/' or path == '':
            return self.get_response(request)

        # Auth page and callbacks
        if path.startswith('/auth/') or path == '/auth':
            return self.get_response(request)

        # Django-Allauth (Google OAuth login, callback, logout)
        if path.startswith('/accounts/'):
            return self.get_response(request)

        # Auth APIs (login, register)
        if path.startswith('/api/auth/'):
            return self.get_response(request)

        # Chatbot API (allow helpful conversational assistance on landing page)
        if path.startswith('/api/ai/chat/'):
            return self.get_response(request)

        # AI Itinerary Generator API and Planner Page
        if path.startswith('/api/generate-itinerary/'):
            return self.get_response(request)

        if path.startswith('/planner/') or path == '/planner':
            return self.get_response(request)

        # Static and media files
        if path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)

        # Django Admin portal (has its own authentication)
        if path.startswith('/admin/'):
            return self.get_response(request)

        # System/Browser icons & robots
        if path in ['/favicon.ico', '/robots.txt']:
            return self.get_response(request)

        # 3. Block unauthorized access to API endpoints
        if path.startswith('/api/'):
            logger.info("Blocked unauthenticated API access to %s", path)
            return JsonResponse({
                'success': False,
                'status': 'unauthorized',
                'message': 'Login verification required to access TravelMate AI.'
            }, status=401)

        # 4. Block unauthorized access to all website views (/home/, /explore/, /planner/, etc.)
        # Redirect directly to dedicated login page (/auth/) preserving query string if present
        logger.info("Redirected unauthenticated visitor from %s to login page", path)
        query = request.META.get('QUERY_STRING', '')
        if query:
            return redirect(f"/auth/?{query}")
        return redirect('auth')


class UserActivityLoggingMiddleware:
    """
    Middleware to automatically record user activity and interactions into the database.
    Captures:
    - Page views (/home/, /explore/, /planner/, /auth/, /)
    - Search queries
    - Response status code and execution details
    Excludes static assets, media, and frequent background polling.
    """

    EXCLUDED_PREFIXES = (
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
        '/admin/jsi18n/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Ignore static assets and system files
        for prefix in self.EXCLUDED_PREFIXES:
            if path.startswith(prefix) or path == prefix:
                return self.get_response(request)

        response = self.get_response(request)

        # Log page visits & meaningful user requests
        try:
            from .models import log_user_activity

            # Skip polling and telemetry loops
            if path.startswith('/api/activity/'):
                return response

            action_type = 'PAGE_VIEW'
            description = f"Visited {path}"
            metadata = {
                'status_code': response.status_code,
                'query_params': dict(request.GET.items()) if request.GET else {}
            }

            if path == '/' or path == '':
                description = "Visited Public Landing Page"
            elif path.startswith('/home'):
                description = "Visited Home Dashboard"
            elif path.startswith('/explore'):
                q = request.GET.get('q', '').strip()
                if q:
                    action_type = 'SEARCH'
                    description = f"Searched destinations: '{q}'"
                else:
                    description = "Browsed Destination Directory (Explore)"
            elif path.startswith('/planner'):
                dest = request.GET.get('dest', '').strip()
                if dest:
                    description = f"Opened AI Planner for destination '{dest}'"
                else:
                    description = "Opened AI Itinerary Planner"
            elif path.startswith('/auth'):
                description = "Visited Authentication Portal"
            elif path.startswith('/accounts/logout'):
                action_type = 'AUTH_LOGOUT'
                description = "User signed out"

            # Record in UserActivityLog
            log_user_activity(
                request=request,
                action_type=action_type,
                description=description,
                metadata=metadata
            )
        except Exception as e:
            logger.warning("Error in UserActivityLoggingMiddleware: %s", e)

        return response

