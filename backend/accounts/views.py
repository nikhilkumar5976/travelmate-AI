from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import PasswordResetView
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import SignUpForm, EditProfileForm
from .models import Profile


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
            Profile.objects.create(user=user)
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
            return redirect(get_safe_next(request) or 'edit_profile')
    else:
        form = EditProfileForm(instance=profile)
    return render(request, 'accounts/edit_profile.html', {'form': form, 'profile': profile})

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
