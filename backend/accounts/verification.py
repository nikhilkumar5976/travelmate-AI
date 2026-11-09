from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse

TOKEN_SALT = 'email-verify'
TOKEN_MAX_AGE = 60 * 60 * 24 * 3  # 3 days in seconds


def generate_verification_token(user):
    """
    Build a signed URL-safe token containing user ID and current email.
    """
    return signing.dumps({'uid': user.pk, 'email': user.email}, salt=TOKEN_SALT)


def decode_verification_token(token):
    """
    Verify and load token payload. Returns dict on success, None on BadSignature or expiry.
    """
    try:
        return signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
    except signing.BadSignature:
        return None


def build_verification_link(request, token):
    """
    Build full absolute URL for the verify_email endpoint.
    If settings.SITE_URL is set, use SITE_URL.rstrip('/') + path,
    otherwise request.build_absolute_uri(path).
    """
    path = reverse('verify_email', kwargs={'token': token})
    site_url = getattr(settings, 'SITE_URL', '')
    if site_url:
        return f"{site_url.rstrip('/')}{path}"
    if request:
        return request.build_absolute_uri(path)
    return path


def send_verification_email(request, user):
    """
    Generates a verification token, constructs the email body,
    and dispatches the verification email to the user.
    """
    token = generate_verification_token(user)
    verify_url = build_verification_link(request, token)

    subject = "Verify your TravelMate AI email"
    body = (
        f"Hi {user.username},\n\n"
        f"Please verify your email address for TravelMate AI by clicking the link below:\n\n"
        f"{verify_url}\n\n"
        f"If you did not create this account, you can ignore this email."
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[user.email],
        fail_silently=False,
    )

