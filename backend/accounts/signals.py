import logging
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def persist_session_user(sender, request, user, **kwargs):
    """
    Ensure the logged-in user's essential identity is saved in the signed session cookie
    so that on serverless instances without shared disk storage, the user can be
    consistently authenticated without random logouts.
    """
    if request and hasattr(request, 'session'):
        try:
            request.session['persisted_username'] = user.username
            request.session['persisted_email'] = user.email or ''
            request.session['persisted_password_hash'] = user.password or ''
            request.session.modified = True
        except Exception as exc:
            logger.debug('Could not persist session user data: %s', exc)
