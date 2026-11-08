from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Place


@login_required
def explore(request):
    places = Place.objects.filter(is_active=True)

    city = request.GET.get('city', '').strip()
    category = request.GET.get('category', '').strip()
    if city:
        places = places.filter(city__iexact=city)
    if category:
        places = places.filter(category=category)

    cities = (
        Place.objects.filter(is_active=True)
        .order_by('city')
        .values_list('city', flat=True)
        .distinct()
    )

    return render(request, 'places/explore.html', {
        'places': places,
        'cities': cities,
        'categories': Place.CATEGORY_CHOICES,
        'selected_city': city,
        'selected_category': category,
    })