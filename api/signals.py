import logging
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in as django_user_logged_in
try:
    from allauth.account.signals import (
        user_logged_in as allauth_user_logged_in,
        user_signed_up as allauth_user_signed_up,
    )
except ImportError:
    allauth_user_logged_in = None
    allauth_user_signed_up = None

from api.models import UserLoginLog, get_ist_now

logger = logging.getLogger(__name__)

def record_user_once(user=None, email=None, name=None):
    """
    Saves a user's details only ONCE upon initial registration or first login.
    If the user already exists in UserLoginLog (matched case-insensitively by email),
    subsequent/recurring logins will NOT create duplicate records.
    Login time is strictly recorded according to Indian Standard Time (IST).
    """
    try:
        user_email = ""
        user_name = ""

        if user:
            user_email = getattr(user, 'email', '') or f"{getattr(user, 'username', 'nomad')}@travelmate.ai"
            user_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or getattr(user, 'username', 'User')

        if email:
            user_email = email
        if name:
            user_name = name

        user_email = (user_email or '').strip().lower()
        if not user_email:
            return None, False

        # Check if this user was already registered / recorded previously
        if UserLoginLog.objects.filter(email__iexact=user_email).exists():
            logger.info("User '%s' already exists in UserLoginLog; skipping duplicate log.", user_email)
            return None, False

        # First time registration/login: save the record once with IST timestamp
        record = UserLoginLog.objects.create(
            email=user_email,
            name=user_name or user_email.split('@')[0],
            login_time=get_ist_now()
        )
        logger.info("First-time registration recorded in UserLoginLog for '%s' (%s) at IST: %s.", user_email, user_name, record.formatted_login_time)

        return record, True
    except Exception as e:
        logger.warning("Error in record_user_once for user '%s': %s", email or getattr(user, 'email', ''), e)
        return None, False

@receiver(django_user_logged_in)
def on_django_login(sender, request, user, **kwargs):
    record_user_once(user=user)

if allauth_user_logged_in:
    @receiver(allauth_user_logged_in)
    def on_allauth_login(sender, request, user, **kwargs):
        record_user_once(user=user)

if allauth_user_signed_up:
    @receiver(allauth_user_signed_up)
    def on_allauth_signup(sender, request, user, **kwargs):
        record_user_once(user=user)


