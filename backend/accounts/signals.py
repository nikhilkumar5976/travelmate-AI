import logging
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .profile_utils import generate_avatar_data_uri

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def persist_session_user(sender, request, user, **kwargs):
    """
    Ensure the logged-in user's essential identity, phone, and avatar are saved in the
    signed session cookie so that across serverless instances and page reloads, the user's
    complete profile and photo persist permanently without vanishing.
    """
    if request and hasattr(request, 'session'):
        try:
            request.session['persisted_username'] = user.username
            request.session['persisted_email'] = user.email or ''
            request.session['persisted_password_hash'] = user.password or ''

            profile = getattr(user, 'profile', None)
            if profile:
                if profile.phone:
                    request.session['persisted_phone'] = profile.phone
                if profile.photo:
                    request.session['persisted_photo_name'] = profile.photo.name
                    if not request.session.get('persisted_photo_data'):
                        try:
                            data_uri = generate_avatar_data_uri(profile.photo)
                            if data_uri:
                                request.session['persisted_photo_data'] = data_uri
                        except Exception:
                            pass
                request.session['profile_completed'] = profile.is_complete()

            request.session.modified = True
        except Exception as exc:
            logger.debug('Could not persist session user data: %s', exc)
