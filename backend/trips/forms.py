from django import forms
from .models import Trip, TripMember, Invitation, INTEREST_CHOICES

MAX_DAYS = 15


class TripForm(forms.ModelForm):
    interests = forms.MultipleChoiceField(
        choices=INTEREST_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        error_messages={'required': 'Pick at least one interest.'},
    )

    class Meta:
        model = Trip
        fields = ('destination', 'num_days', 'budget', 'interests')
        labels = {
            'num_days': 'Number of days',
            'budget': 'Total budget',
        }

    def clean_destination(self):
        destination = self.cleaned_data['destination'].strip()
        if len(destination) < 2:
            raise forms.ValidationError('Enter a destination.')
        return destination

    def clean_num_days(self):
        days = self.cleaned_data['num_days']
        if days < 1 or days > MAX_DAYS:
            raise forms.ValidationError(f'Choose between 1 and {MAX_DAYS} days.')
        return days

    def clean_budget(self):
        budget = self.cleaned_data['budget']
        if budget <= 0:
            raise forms.ValidationError('Budget must be greater than 0.')
        return budget

class InviteForm(forms.Form):
    email = forms.EmailField()

    def __init__(self, *args, trip=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.trip = trip

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if TripMember.objects.filter(trip=self.trip, user__email__iexact=email).exists():
            raise forms.ValidationError('This person is already in the trip.')
        if Invitation.objects.filter(trip=self.trip, email__iexact=email, status='pending').exists():
            raise forms.ValidationError('An invitation to this email is already pending.')
        return email