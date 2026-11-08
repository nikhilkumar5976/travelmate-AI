import secrets
import uuid

from django.conf import settings
from django.db import models

INTEREST_CHOICES = [
    ('food', 'Food'),
    ('nature', 'Nature'),
    ('history', 'History and culture'),
    ('adventure', 'Adventure'),
    ('shopping', 'Shopping'),
    ('nightlife', 'Nightlife'),
    ('relaxation', 'Relaxation'),
    ('beaches', 'Beaches'),
]


def generate_token():
    return secrets.token_urlsafe(32)


class Trip(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_trips'
    )
    destination = models.CharField(max_length=200)
    num_days = models.PositiveIntegerField()
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    interests = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True, default='')
    budget_warning = models.TextField(blank=True, default='')

    def __str__(self):
        return f'{self.destination} ({self.num_days} days)'


class TripMember(models.Model):
    ROLE_CHOICES = [('owner', 'Owner'), ('member', 'Member')]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trip_memberships'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('trip', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f'{self.user.username} in {self.trip.destination}'


class Invitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.email} -> {self.trip.destination} ({self.status})'