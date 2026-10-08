import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from api.models import UserLoginLog

logger = logging.getLogger(__name__)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom Allauth Social Account Adapter:
    1. Automatically links Google account to an existing local Django user
       if the email matches, avoiding account conflict / duplicate signup errors.
    2. Logs the authenticated user into UserLoginLog.
    """

    def pre_social_login(self, request, sociallogin):
        # If the social account is already linked to a user, nothing to do
        if getattr(sociallogin, 'account', None) and sociallogin.account.pk:
            return

        # Extract verified email from the social login payload
        email = None
        if sociallogin.email_addresses:
            for email_address in sociallogin.email_addresses:
                if email_address.verified:
                    email = email_address.email
                    break
            if not email and sociallogin.email_addresses:
                email = sociallogin.email_addresses[0].email
        elif sociallogin.user and sociallogin.user.email:
            email = sociallogin.user.email

        if not email:
            return

        # Check if an existing User already has this email
        try:
            existing_user = User.objects.get(email__iexact=email)
            # Connect the social login directly to this existing user!
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass
        except User.MultipleObjectsReturned:
            existing_user = User.objects.filter(email__iexact=email).first()
            if existing_user:
                sociallogin.connect(request, existing_user)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        try:
            from api.signals import record_user_once
            record_user_once(user=user)
        except Exception as e:
            logger.warning("Failed to record UserLoginLog on social signup: %s", e)
        return user

