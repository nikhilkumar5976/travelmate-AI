import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

from itinerary.models import Day, Stop
from .llm import call_llm
from .prompts import build_itinerary_prompt

VALID_TIMES = {'morning', 'afternoon', 'evening'}
VALID_CATEGORIES = {'food', 'sightseeing', 'stay', 'transport', 'activity'}


class ItineraryError(Exception):
    pass


def parse_itinerary(text, num_days):
    start, end = text.find('{'), text.rfind('}')
    if start == -1 or end == -1:
        raise ItineraryError('The AI reply did not contain JSON.')
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        raise ItineraryError('The AI reply was not valid JSON.')

    days = data.get('days')
    if not isinstance(days, list) or len(days) != num_days:
        raise ItineraryError('The AI returned the wrong number of days.')
    for day in days:
        if not isinstance(day, dict) or not isinstance(day.get('stops'), list) or not day['stops']:
            raise ItineraryError('A day had no stops.')
    return data


def to_cost(value):
    try:
        cost = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')
    if cost < 0 or cost > Decimal('99999999'):
        return Decimal('0')
    return cost.quantize(Decimal('0.01'))


@transaction.atomic
def save_itinerary(trip, data):
    trip.days.all().delete()
    for position, day_data in enumerate(data['days'], start=1):
        day = Day.objects.create(
            trip=trip,
            day_number=position,
            title=str(day_data.get('title', ''))[:200],
        )
        for order, stop in enumerate(day_data['stops']):
            time_of_day = stop.get('time_of_day')
            category = stop.get('category')
            Stop.objects.create(
                day=day,
                name=str(stop.get('name', 'Stop'))[:200],
                description=str(stop.get('description', '')),
                time_of_day=time_of_day if time_of_day in VALID_TIMES else 'morning',
                category=category if category in VALID_CATEGORIES else 'activity',
                estimated_cost_per_person=to_cost(stop.get('estimated_cost_per_person', 0)),
                order=order,
            )
    trip.summary = str(data.get('summary', ''))
    trip.budget_warning = str(data.get('budget_warning', ''))
    trip.save()


def generate_itinerary(trip):
    travelers = trip.members.count()
    prompt = build_itinerary_prompt(trip, travelers, settings.TRIP_CURRENCY)
    last_error = None
    for _ in range(2):
        reply = call_llm(prompt)
        try:
            data = parse_itinerary(reply, trip.num_days)
        except ItineraryError as error:
            last_error = error
            continue
        save_itinerary(trip, data)
        return
    raise last_error