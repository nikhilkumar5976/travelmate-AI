import base64
import logging
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse

logger = logging.getLogger(__name__)

TOKEN_SALT = 'email-verify'
TOKEN_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds


def _urlsafe_encode(raw_string: str) -> str:
    """Encode a string to URL-safe base64 without padding or colons."""
    return base64.urlsafe_b64encode(raw_string.encode('utf-8')).decode('ascii').rstrip('=')


def _urlsafe_decode(encoded_string: str) -> str:
    """Decode a URL-safe base64 string back to original string."""
    padding = '=' * (-len(encoded_string) % 4)
    return base64.urlsafe_b64decode((encoded_string + padding).encode('ascii')).decode('utf-8')


def generate_verification_token(user):
    """
    Build a signed URL-safe token containing user ID, username, and current email.
    The resulting token is clean base64url characters only [A-Za-z0-9_-],
    with no colons or special characters that email clients could break.
    """
    raw_token = signing.dumps(
        {
            'uid': user.pk,
            'username': user.username,
            'email': user.email,
        },
        salt=TOKEN_SALT,
    )
    return _urlsafe_encode(raw_token)


def decode_verification_token(token):
    """
    Verify and load token payload. Supports:
    1. Base64url-encoded signed tokens (new clean format)
    2. Raw colon-separated signed tokens (backwards compatibility)
    """
    if not token:
        return None

    clean_token = token.strip()
    candidate_tokens = []

    # Try decoding base64url wrapper first
    try:
        candidate_tokens.append(_urlsafe_decode(clean_token))
    except Exception:
        pass

    # Also try the token directly (in case it is already raw signed token)
    candidate_tokens.append(clean_token)

    for cand in candidate_tokens:
        try:
            data = signing.loads(cand, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
            if isinstance(data, dict):
                return data
        except signing.BadSignature:
            continue
        except Exception:
            continue

    return None


def build_verification_link(request, token):
    """
    Build full absolute HTTPS URL for the verify_email endpoint.
    Guarantees HTTPS protocol on production/Vercel.
    """
    path = reverse('verify_email', kwargs={'token': token})
    site_url = getattr(settings, 'SITE_URL', '').strip()
    if not site_url and getattr(settings, 'IS_VERCEL', False):
        site_url = 'https://travelmate-ai-lovat.vercel.app'

    if site_url:
        base = site_url.rstrip('/')
        if not base.startswith(('http://', 'https://')):
            base = f"https://{base}"
        return f"{base}{path}"

    if request:
        uri = request.build_absolute_uri(path)
        if getattr(settings, 'IS_VERCEL', False) and uri.startswith('http://'):
            uri = 'https://' + uri[7:]
        return uri

    return f"https://travelmate-ai-lovat.vercel.app{path}"


def send_verification_email(request, user):
    """
    Generates a verification token, constructs email body (both text & HTML),
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

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 24px;">
  <div style="max-width: 560px; margin: 0 auto; background: #1e293b; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
    <div style="margin-bottom: 24px;">
      <h1 style="color: #f8fafc; font-size: 22px; margin: 0 0 8px 0;">Verify your email address</h1>
      <p style="color: #94a3b8; font-size: 15px; margin: 0;">Hi <strong>{user.username}</strong>,</p>
    </div>
    <p style="color: #cbd5e1; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
      Welcome to TravelMate AI! Please confirm your email address by clicking the button below so you can plan trips, invite companions, and generate custom AI itineraries.
    </p>
    <div style="margin: 28px 0; text-align: center;">
      <a href="{verify_url}" style="background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 16px; display: inline-block;">
        Verify Email Address
      </a>
    </div>
    <p style="color: #64748b; font-size: 13px; line-height: 1.5; margin: 24px 0 8px 0;">
      If the button above does not work, copy and paste this link into your browser:
    </p>
    <p style="color: #f97316; font-size: 12px; word-break: break-all; margin: 0 0 24px 0;">
      <a href="{verify_url}" style="color: #f97316; text-decoration: underline;">{verify_url}</a>
    </p>
    <hr style="border: none; border-top: 1px solid #334155; margin: 24px 0 16px 0;">
    <p style="color: #475569; font-size: 12px; margin: 0;">
      If you did not create a TravelMate AI account, you can safely ignore this email.
    </p>
  </div>
</body>
</html>"""

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[user.email],
        html_message=html_body,
        fail_silently=False,
    )
