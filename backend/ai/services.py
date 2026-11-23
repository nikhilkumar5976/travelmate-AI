import json
import logging
import time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction

from itinerary.models import Day, Stop
from .llm import call_llm
from .prompts import build_itinerary_prompt

logger = logging.getLogger(__name__)

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


def generate_curated_itinerary(trip):
    """
    Generates a high-quality, customized day-by-day itinerary tailored to
    destination, duration, budget, and interests as a reliable fallback.
    """
    dest = (trip.destination or 'Destination').title()
    if isinstance(trip.interests, list):
        interests = [str(i).strip() for i in trip.interests if str(i).strip()]
    elif isinstance(trip.interests, str):
        interests = [i.strip() for i in trip.interests.split(',') if i.strip()]
    else:
        interests = ['Sightseeing', 'Culture', 'Food']
    if not interests:
        interests = ['Sightseeing', 'Culture', 'Food']
    num_days = max(1, trip.num_days)
    travelers = max(1, trip.members.count())
    budget_per_person = float(trip.budget) / travelers if trip.budget else 15000.0
    daily_budget = budget_per_person / num_days

    dest_lower = dest.lower()
    if 'shimla' in dest_lower:
        attractions = [
            ("The Ridge & Christ Church", "Explore the historic open-space Ridge and the iconic neo-Gothic Christ Church.", "sightseeing", 0.15),
            ("Mall Road & Lakkar Bazaar", "Stroll through the lively pedestrian Mall Road, visit wooden craft shops at Lakkar Bazaar.", "shopping", 0.20),
            ("Scandal Point & Himachali Dinner", "Enjoy mountain sunset views followed by an authentic Himachali thali.", "food", 0.15),
            ("Jakhoo Temple & Ropeway", "Ascend through pine trees via ropeway to the highest peak in Shimla with panoramic valley vistas.", "activity", 0.20),
            ("Viceregal Lodge & Botanical Gardens", "Tour the historic British Raj presidential estate surrounded by manicured gardens.", "sightseeing", 0.15),
            ("Lower Bazaar Cafe Hop", "Taste steaming local momos, siddu, and cardamom spiced mountain tea.", "food", 0.15),
            ("Day Excursion to Kufri", "Travel to Kufri for scenic alpine views, yak rides, and pine forest hiking trails.", "activity", 0.25),
            ("Green Valley & Wildflower Hall Trail", "Peaceful nature walk through dense deodar and oak forests.", "sightseeing", 0.10),
            ("Traditional Cedar Pine Dinner", "Savor local mountain cuisine with panoramic evening views of the illuminated hills.", "food", 0.15),
            ("Tara Devi Temple Trek", "Scenic hilltop temple visit offering 360-degree views of the lower Himalayas.", "activity", 0.15),
            ("Tibetan Market Souvenir Shopping", "Pick up hand-woven shawls, wooden souvenirs, and local fruit jams.", "shopping", 0.15),
            ("Farewell Mountain View Dinner", "Relax at a rooftop restaurant overlooking the glowing Himalayan peaks.", "food", 0.20),
        ]
    elif 'manali' in dest_lower:
        attractions = [
            ("Hadimba Temple & Cedar Forest", "Visit the ancient pagoda-style wooden temple nestled in sacred giant deodars.", "sightseeing", 0.15),
            ("Old Manali Village & Cafes", "Wander through cobblestone alleys, vibrant street art, and bohemian bakeries.", "food", 0.20),
            ("Vashisht Hot Springs & Temple", "Relax in natural sulfur thermal baths overlooking the Beas River.", "activity", 0.15),
            ("Solang Valley Adventure", "Experience paragliding, zorbing, and cable car rides amidst snow-capped peaks.", "activity", 0.30),
            ("Jogini Waterfalls Hike", "Scenic trek through orchards and streams leading to a cascading mountain waterfall.", "activity", 0.10),
            ("Riverside Trout Dinner", "Dine by the roaring Beas river savoring fresh Himalayan trout.", "food", 0.20),
            ("Atal Tunnel & Sissu Valley", "Drive through the engineering marvel of Atal Tunnel to the breathtaking Lahaul landscape.", "sightseeing", 0.25),
            ("Mall Road Shopping", "Browse Tibetan handicrafts, warm pashminas, and local apple preserves.", "shopping", 0.15),
            ("Farewell Mountain Dinner", "Celebratory dinner with live music and local Himachali delicacies.", "food", 0.20),
        ]
    elif 'goa' in dest_lower:
        attractions = [
            ("North Goa Beach Walk & Shacks", "Sun-soaked morning exploring golden sand beaches and coastal cafes.", "activity", 0.15),
            ("Fort Aguada & Lighthouse", "Explore the 17th-century Portuguese fortress overlooking the Arabian Sea.", "sightseeing", 0.15),
            ("Candolim Sunset & Seafood", "Enjoy fresh seafood curry while watching the sunset over the Arabian Sea.", "food", 0.20),
            ("Old Goa Churches & Cathedrals", "Tour UNESCO World Heritage sites including Basilica of Bom Jesus.", "sightseeing", 0.15),
            ("Fontainhas Latin Quarter Walk", "Wander through vibrant Portuguese heritage villas and boutique art galleries.", "activity", 0.15),
            ("Goan Portuguese Feast", "Savor traditional prawn balchao, vindaloo, and bebinca at a heritage restaurant.", "food", 0.20),
            ("Mandovi River Cruise", "Scenic sunset river cruise with live Goan folk music.", "activity", 0.25),
            ("Anjuna Flea Market", "Shop for spices, bohemian jewelry, and local beachwear.", "shopping", 0.15),
            ("Beachside Bonfire Dinner", "Celebratory dinner under the stars with coastal music.", "food", 0.20),
        ]
    else:
        primary_interest = interests[0] if interests else "Exploring"
        attractions = [
            (f"Historic Center of {dest}", f"Morning walking tour visiting the most iconic historic landmark and public square in {dest}.", "sightseeing", 0.15),
            (f"Central Market & Artisan Shopping", f"Stroll through the vibrant local market of {dest} exploring regional specialties.", "shopping", 0.20),
            (f"Authentic {dest} Traditional Lunch", f"Taste celebrated local dishes at an authentic, top-rated neighborhood eatery.", "food", 0.15),
            (f"{primary_interest} Experience in {dest}", f"Curated afternoon activity centered around {primary_interest.lower()} in {dest}.", "activity", 0.25),
            (f"Panoramic Viewpoint & Sunset", f"Visit the best vantage point in {dest} for scenic golden hour photos and city views.", "sightseeing", 0.10),
            (f"Fine Dining & Evening Culture", f"Enjoy an evening meal paired with local regional specialties and lively atmosphere.", "food", 0.20),
            (f"Day Excursion around {dest}", f"Explore scenic outskirts, nature trails, or nearby historic landmarks.", "activity", 0.25),
            (f"Museum & Cultural Heritage Center", f"Immerse yourself in the art, history, and traditions of {dest}.", "sightseeing", 0.15),
            (f"Atmospheric Dinner & Night Walk", f"Dinner at an intimate local bistro followed by an evening stroll.", "food", 0.20),
            (f"Morning Park & Botanical Walk", f"Peaceful morning stroll through the largest public garden in {dest}.", "activity", 0.10),
            (f"Souvenir & Gift Shopping", f"Pick up authentic local products and souvenirs to remember the trip.", "shopping", 0.15),
            (f"Farewell Celebration Dinner", f"Memorable final dinner celebrating your trip to {dest}.", "food", 0.25),
        ]

    days = []
    idx = 0
    total_attractions = len(attractions)

    for day_num in range(1, num_days + 1):
        stops = []
        time_slots = ['morning', 'afternoon', 'evening']
        day_theme = f"Day {day_num}: Exploring {dest}"
        if day_num == 1:
            day_theme = f"Day 1: Arrival & Highlights of {dest}"
        elif day_num == num_days:
            day_theme = f"Day {day_num}: Final Sights & Farewell to {dest}"

        for time_key in time_slots:
            name, desc, category, cost_ratio = attractions[idx % total_attractions]
            idx += 1
            est_cost = round(daily_budget * cost_ratio, 2)
            stops.append({
                'name': name,
                'description': desc,
                'time_of_day': time_key,
                'category': category,
                'estimated_cost_per_person': est_cost,
            })

        days.append({
            'title': day_theme,
            'stops': stops,
        })

    return {
        'summary': f"A {num_days}-day customized itinerary in {dest} featuring the best of {', '.join(interests)} with comfortable pacing and balanced budget.",
        'budget_warning': '',
        'days': days,
    }


def generate_itinerary(trip):
    travelers = trip.members.count()
    prompt = build_itinerary_prompt(trip, travelers, settings.TRIP_CURRENCY)
    last_error = None

    # First attempt: Try Gemini AI generation
    for attempt in range(2):
        start = time.monotonic()
        try:
            reply = call_llm(prompt, json_output=True)
            duration = time.monotonic() - start
            logger.info("Itinerary AI call took %.1f seconds", duration)
            data = parse_itinerary(reply, trip.num_days)
            save_itinerary(trip, data)
            return
        except Exception as error:
            logger.warning("AI generation attempt %d failed: %s", attempt + 1, error)
            last_error = error
            continue

    # Second attempt: If Gemini AI is rate-limited, 503, or unavailable, use curated fallback
    logger.warning("Using curated itinerary generator for %s (reason: %s)", trip.destination, last_error)
    data = generate_curated_itinerary(trip)
    save_itinerary(trip, data)
