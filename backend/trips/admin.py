from django.contrib import admin
from .models import Trip, TripMember, Invitation

admin.site.register(Trip)
admin.site.register(TripMember)
admin.site.register(Invitation)