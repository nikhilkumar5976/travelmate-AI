from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path, reverse_lazy
from django.views.static import serve

from accounts import views as account_views
from accounts.forms import EmailAuthenticationForm

urlpatterns = [
    path('', account_views.landing, name='landing'),
    path('admin/', admin.site.urls),
    path('home/', account_views.home, name='home'),
    path('signup/', account_views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        form_class=EmailAuthenticationForm,
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password-reset/', account_views.LimitedPasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.txt',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
    path('verify-email/<str:token>/', account_views.verify_email, name='verify_email'),
    path('verify-email/<str:token>', account_views.verify_email),
    path('verify-email/', account_views.verify_email, name='verify_email_query'),
    path('resend-verification/', account_views.resend_verification, name='resend_verification'),
    path('profile/edit/', account_views.edit_profile, name='edit_profile'),
    path('trips/', include('trips.urls')),
    path('chat/', include('chat.urls')),
    path('places/', include('places.urls')),
    path('ai/', include('ai.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

def serve_media(request, path):
    import base64
    from pathlib import Path
    media_file = Path(settings.MEDIA_ROOT) / path
    if not media_file.exists():
        session = getattr(request, 'session', None)
        if session:
            persisted_photo_data = session.get('persisted_photo_data')
            persisted_photo_name = session.get('persisted_photo_name', '')
            if persisted_photo_data and (persisted_photo_name == path or persisted_photo_name.endswith(path) or path.endswith(persisted_photo_name)):
                try:
                    media_file.parent.mkdir(parents=True, exist_ok=True)
                    raw_b64 = persisted_photo_data
                    if ',' in raw_b64:
                        raw_b64 = raw_b64.split(',', 1)[1]
                    media_file.write_bytes(base64.b64decode(raw_b64))
                except Exception:
                    pass

    try:
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    except Exception:
        repo_media = settings.BASE_DIR / 'media'
        if repo_media.exists():
            return serve(request, path, document_root=repo_media)
        raise

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATICFILES_DIRS[0]}),
]