from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Place(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Food'),
        ('sightseeing', 'Sightseeing'),
        ('stay', 'Stay'),
        ('shopping', 'Shopping'),
        ('nature', 'Nature'),
        ('adventure', 'Adventure'),
        ('nightlife', 'Nightlife'),
        ('other', 'Other'),
    ]
    PRICE_CHOICES = [
        (0, 'Free'),
        (1, 'Cheap'),
        (2, 'Medium'),
        (3, 'Expensive'),
    ]

    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='place_images/', blank=True)
    price_level = models.PositiveSmallIntegerField(choices=PRICE_CHOICES, default=1)
    latitude = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['city', 'name']

    def __str__(self):
        return f'{self.name} ({self.city})'