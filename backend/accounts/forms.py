from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from .models import Profile 


class EmailAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        label="Email address",
        widget=forms.EmailInput(attrs={
            "autofocus": True,
            "placeholder": "name@example.com",
            "autocomplete": "email",
        }),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password",
            "placeholder": "••••••••",
        }),
    )

    error_messages = {
        "invalid_login": "Please enter a correct email address and password.",
        "inactive": "This account is inactive.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        if request and request.method == 'GET':
            email = request.GET.get('email')
            if email and not self.initial.get('username'):
                self.initial['username'] = email.strip()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

class EditProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ('photo', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'].required = True
        self.fields['photo'].required = False
        if self.instance and self.instance.pk and hasattr(self.instance, 'user'):
            self.fields['email'].initial = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        taken = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk and hasattr(self.instance, 'user'):
            taken = taken.exclude(pk=self.instance.user.pk)
        if taken.exists():
            raise forms.ValidationError('Another account already uses this email.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = phone.replace('+', '').replace(' ', '').replace('-', '')
        if not digits.isdigit() or len(digits) != 10:
            raise forms.ValidationError('Enter a valid 10-digit phone number.')
        return digits

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo and isinstance(photo, UploadedFile) and photo.size > 2 * 1024 * 1024:
            raise forms.ValidationError('Photo size should not exceed 2MB.')
        return photo

    def save(self, commit=True):
        self.email_changed = False
        new_email = (self.cleaned_data.get('email') or '').strip().lower()
        if hasattr(self.instance, 'user') and self.instance.user:
            old_email = (self.instance.user.email or '').strip().lower()
            if old_email != new_email:
                self.instance.email_verified = False
                self.email_changed = True
        profile = super().save(commit=commit)
        if self.email_changed and commit:
            profile.email_verified = False
            profile.save(update_fields=['email_verified'])
        if 'email' in self.cleaned_data and hasattr(profile, 'user'):
            profile.user.email = self.cleaned_data['email']
            profile.user.save()
        return profile