import logging
from django.contrib.auth import get_user_model
from accounts.models import Profile

logger = logging.getLogger(__name__)


class EphemeralUserRestoreMiddleware:
    """
    On serverless environments (such as Vercel) where the local database is ephemeral
    across cold starts or multiple container instances, this middleware checks
    if the incoming request has a valid signed session for a user that does not yet
    exist in the current instance's local database.

    If missing, it reinstates the user account and profile on the fly so
    AuthenticationMiddleware can authenticate the user without logging them out.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            session = getattr(request, 'session', None)
            if session:
                user_id = session.get('_auth_user_id')
                username = session.get('persisted_username')
                if user_id and username:
                    UserModel = get_user_model()
                    if not UserModel.objects.filter(pk=user_id).exists():
                        email = session.get('persisted_email', '')
                        password_hash = session.get('persisted_password_hash', '')
                        user = UserModel(
                            id=user_id,
                            username=username,
                            email=email,
                            password=password_hash,
                            is_active=True,
                        )
                        user.save()
                        Profile.objects.get_or_create(
                            user=user,
                            defaults={'email_verified': True}
                        )
                        logger.info("Restored ephemeral user %s (id=%s) to local container DB.", username, user_id)
        except Exception as exc:
            logger.debug("EphemeralUserRestoreMiddleware error: %s", exc)

        return self.get_response(request)
