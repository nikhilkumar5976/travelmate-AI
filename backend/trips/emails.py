import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse

logger = logging.getLogger(__name__)


def send_invitation_email(invitation, request=None):
    """
    Dispatches an invitation email via Django's mail system containing
    unique absolute URLs for accepting and rejecting the invite.
    """
    if request:
        accept_url = request.build_absolute_uri(reverse('accept_invitation', args=[invitation.token]))
        reject_url = request.build_absolute_uri(reverse('reject_invitation', args=[invitation.token]))
        detail_url = request.build_absolute_uri(reverse('invitation', args=[invitation.token]))
    else:
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
        accept_url = f"{site_url}{reverse('accept_invitation', args=[invitation.token])}"
        reject_url = f"{site_url}{reverse('reject_invitation', args=[invitation.token])}"
        detail_url = f"{site_url}{reverse('invitation', args=[invitation.token])}"

    trip = invitation.trip
    inviter = invitation.invited_by.username
    subject = f"{inviter} invited you to join a trip to {trip.destination} on TravelMate AI"

    text_content = (
        f"Hi!\n\n"
        f"{inviter} invited you to join a {trip.num_days}-day trip to {trip.destination} on TravelMate AI.\n\n"
        f"To ACCEPT this invitation, click:\n{accept_url}\n\n"
        f"To REJECT this invitation, click:\n{reject_url}\n\n"
        f"You can also review full trip details here:\n{detail_url}\n\n"
        f"If you did not expect this invitation, you can safely ignore this email.\n"
    )

    html_content = f"""
    <div style="background-color: #0b1530; color: #e8f0ff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 32px 16px;">
      <div style="max-width: 520px; margin: 0 auto; background: #111e42; border: 1px solid rgba(255,255,255,0.12); border-radius: 18px; padding: 32px 24px;">
        <h2 style="color: #fb923c; margin-top: 0; font-size: 20px;">TravelMate AI</h2>
        <h1 style="color: #e8f0ff; font-size: 24px; margin: 12px 0 16px;">You're invited on a trip!</h1>
        <p style="color: #a9b8d9; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
          <strong style="color: #e8f0ff;">{inviter}</strong> invited you to join a <strong style="color: #e8f0ff;">{trip.num_days}-day</strong> trip to <strong style="color: #38bdf8;">{trip.destination}</strong>.
        </p>
        <div style="margin: 24px 0;">
          <a href="{accept_url}" style="display: inline-block; padding: 12px 24px; border-radius: 999px; background: #fb923c; color: #1b1005; font-weight: 700; text-decoration: none; font-size: 14px; margin-right: 12px; margin-bottom: 8px;">
            Accept Invitation
          </a>
          <a href="{reject_url}" style="display: inline-block; padding: 12px 24px; border-radius: 999px; background: rgba(248,113,113,0.15); border: 1px solid rgba(248,113,113,0.4); color: #fca5a5; font-weight: 600; text-decoration: none; font-size: 14px; margin-bottom: 8px;">
            Reject Invitation
          </a>
        </div>
        <p style="color: #7f93b8; font-size: 13px; line-height: 1.5; margin-top: 24px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 18px;">
          Trip details & alternative response: <a href="{detail_url}" style="color: #38bdf8;">{detail_url}</a>
        </p>
      </div>
    </div>
    """

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=[invitation.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)
    return True
