import base64
import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from accounts.models import Profile

logger = logging.getLogger(__name__)


class EphemeralUserRestoreMiddleware:
    """
    On serverless environments (such as Vercel) where the local database and filesystem
    are ephemeral across cold starts or multiple container instances, this middleware
    checks if the incoming request has a valid signed session cookie.

    It restores:
      1. User credentials (id, username, email, password)
      2. Complete profile attributes (phone number, verification status)
      3. Profile photo metadata and recreates the photo file on disk in MEDIA_ROOT
    so that page reloads never lose the user's completed profile, phone number, or photo.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            session = getattr(request, 'session', None)
            if session:
                user_id = session.get('_auth_user_id')
                username = session.get('persisted_username')
                persisted_phone = session.get('persisted_phone')
                persisted_photo_name = session.get('persisted_photo_name')
                persisted_photo_data = session.get('persisted_photo_data')

                if user_id and username:
                    UserModel = get_user_model()
                    user = UserModel.objects.filter(pk=user_id).first()
                    if not user:
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
                        logger.info("Restored ephemeral user %s (id=%s) to local container DB.", username, user_id)

                    profile, _ = Profile.objects.get_or_create(user=user)
                    updated_fields = []

                    if persisted_phone and profile.phone != persisted_phone:
                        profile.phone = persisted_phone
                        updated_fields.append('phone')

                    if persisted_photo_name and profile.photo.name != persisted_photo_name:
                        profile.photo.name = persisted_photo_name
                        updated_fields.append('photo')

                    if not profile.email_verified:
                        profile.email_verified = True
                        updated_fields.append('email_verified')

                    if updated_fields:
                        profile.save(update_fields=updated_fields)

                    # Ensure the profile photo file is present in MEDIA_ROOT on this container
                    if persisted_photo_name and persisted_photo_data:
                        media_path = Path(settings.MEDIA_ROOT) / persisted_photo_name
                        if not media_path.exists():
                            try:
                                media_path.parent.mkdir(parents=True, exist_ok=True)
                                raw_b64 = persisted_photo_data
                                if ',' in raw_b64:
                                    raw_b64 = raw_b64.split(',', 1)[1]
                                media_path.write_bytes(base64.b64decode(raw_b64))
                            except Exception as exc:
                                logger.debug("Could not restore photo file to MEDIA_ROOT: %s", exc)

        except Exception as exc:
            logger.debug("EphemeralUserRestoreMiddleware error: %s", exc)

        return self.get_response(request)
