from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from accounts import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account_views.home, name='root'),
    path('home/', account_views.home, name='home'),
    path('signup/', account_views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/edit/', account_views.edit_profile, name='edit_profile'),
    path('trips/', include('trips.urls')),
    path('chat/', include('chat.urls')),
    path('ai/', include('ai.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)