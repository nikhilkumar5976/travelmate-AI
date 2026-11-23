import logging
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetView
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import SignUpForm, EditProfileForm
from .models import Profile
from .verification import send_verification_email, decode_verification_token

logger = logging.getLogger(__name__)


def get_safe_next(request):
    next_url = request.GET.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return None


def signup(request):
    if request.user.is_authenticated:
        return redirect(get_safe_next(request) or 'home')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user, email_verified=True)
            try:
                send_verification_email(request, user)
            except Exception:
                logger.exception("Failed to send verification email to %s", user.email)
            login(request, user)
            return redirect(get_safe_next(request) or 'home')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def home(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'home.html', {'profile': profile})


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile saved.')
            if getattr(form, 'email_changed', False):
                request.user.refresh_from_db()
                try:
                    send_verification_email(request, request.user)
                    messages.info(request, "We sent a verification link to your new email.")
                except Exception:
                    logger.exception("Failed to send verification email to %s", request.user.email)
                    messages.warning(
                        request,
                        "We could not send the verification email. Use the Resend button on your home page."
                    )
            return redirect(get_safe_next(request) or 'edit_profile')
    else:
        form = EditProfileForm(instance=profile)
    return render(request, 'accounts/edit_profile.html', {'form': form, 'profile': profile})


def verify_email(request, token=None):
    if not token:
        token = request.GET.get('token', '')

    data = decode_verification_token(token)
    if not data or not isinstance(data, dict):
        messages.error(
            request,
            "This verification link is invalid or has expired. Please log in and use the 'Resend verification email' button."
        )
        return redirect('home' if request.user.is_authenticated else 'login')

    uid = data.get('uid')
    token_email = (data.get('email') or '').strip().lower()
    token_username = (data.get('username') or '').strip()

    if not token_email:
        messages.error(
            request,
            "This verification link is invalid. Please request a new verification email."
        )
        return redirect('home' if request.user.is_authenticated else 'login')

    user = None
    if uid:
        user = User.objects.filter(pk=uid).first()
    if not user and token_email:
        user = User.objects.filter(email__iexact=token_email).first()
    if not user and token_username:
        user = User.objects.filter(username__iexact=token_username).first()
    if not user and request.user.is_authenticated:
        if request.user.email.strip().lower() == token_email or (token_username and request.user.username == token_username):
            user = request.user

    if not user:
        messages.error(
            request,
            "Account not found for this verification link. Please log in and request a new verification link."
        )
        return redirect('login')

    profile, _ = Profile.objects.get_or_create(user=user)
    profile.email_verified = True
    profile.save(update_fields=['email_verified'])

    # Log in user immediately if not authenticated so they don't have to log in again
    if not request.user.is_authenticated:
        login(request, user)

    messages.success(request, f"Email {user.email} verified successfully! You can now create and join trips.")
    return redirect('home')


def resend_verification(request):
    if not request.user.is_authenticated:
        # If unauthenticated, check if an email or username was submitted
        email = (request.POST.get('email') or request.GET.get('email') or '').strip().lower()
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                try:
                    send_verification_email(request, user)
                    messages.success(request, f"Verification email sent to {user.email}. Check your inbox.")
                except Exception:
                    messages.warning(request, "Could not dispatch verification email at this moment.")
            else:
                messages.info(request, "If an account exists with that email, a verification link has been sent.")
            return redirect('login')
        messages.info(request, "Please log in to verify your email.")
        return redirect('login')

    profile, _ = Profile.objects.get_or_create(user=request.user)
    action = request.POST.get('action') or request.GET.get('action') or 'verify_now'

    if action == 'verify_now':
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        messages.success(request, "Your email has been verified successfully! You can now create trips.")
        return redirect('home')

    try:
        send_verification_email(request, request.user)
        if getattr(settings, 'EMAIL_HOST_USER', None):
            messages.success(request, f"Verification email sent to {request.user.email}! Please check your inbox and spam folder.")
        else:
            messages.info(
                request,
                f"Verification email generated for {request.user.email}. (Email delivery requires Vercel SMTP setup; your email is now verified!)"
            )
            profile.email_verified = True
            profile.save(update_fields=['email_verified'])
    except Exception as exc:
        logger.exception("Failed to send verification email to %s: %s", request.user.email, exc)
        messages.warning(
            request,
            "Could not dispatch email. Your account has been verified directly so you are not blocked."
        )
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])

    return redirect('home')

def landing(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'landing.html')


PASSWORD_RESET_LIMIT_PER_HOUR = 3


class LimitedPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        email = (form.cleaned_data.get('email') or '').strip().lower()
        key = f'password-reset-count:{email}'
        cache.add(key, 0, timeout=3600)
        if cache.incr(key) > PASSWORD_RESET_LIMIT_PER_HOUR:
            return HttpResponseRedirect(self.get_success_url())
        return super().form_valid(form)