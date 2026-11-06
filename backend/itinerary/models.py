from django.db import models


class Day(models.Model):
    trip = models.ForeignKey('trips.Trip', on_delete=models.CASCADE, related_name='days')
    day_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['day_number']
        unique_together = ('trip', 'day_number')

    def __str__(self):
        return f'Day {self.day_number} - {self.trip.destination}'


class Stop(models.Model):
    TIME_CHOICES = [('morning', 'Morning'), ('afternoon', 'Afternoon'), ('evening', 'Evening')]
    CATEGORY_CHOICES = [
        ('food', 'Food'),
        ('sightseeing', 'Sightseeing'),
        ('stay', 'Stay'),
        ('transport', 'Transport'),
        ('activity', 'Activity'),
    ]

    day = models.ForeignKey(Day, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_of_day = models.CharField(max_length=10, choices=TIME_CHOICES, default='morning')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='activity')
    estimated_cost_per_person = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name
