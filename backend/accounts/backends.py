from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

UserModel = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL using email address as primary
    login credential, with username supported as fallback.
    Matches case-insensitively.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD) or kwargs.get('email')
        if not username or not password:
            return None

        identifier = str(username).strip()

        # Look up by email first (case-insensitive), then by username
        user = UserModel.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier)
        ).order_by('-is_superuser', '-is_staff', 'id').first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
