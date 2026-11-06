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


class Trip(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_trips'
    )
    destination = models.CharField(max_length=200)
    num_days = models.PositiveIntegerField()
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    interests = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

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