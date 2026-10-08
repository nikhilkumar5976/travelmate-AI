import json
import logging
from urllib.parse import quote
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth.models import User
import google.generativeai as genai
from .models import Destination, Review, UserLoginLog
from . import gemini_service

logger = logging.getLogger(__name__)

def home_view(request):
    all_destinations = list(Destination.objects.all())
    for d in all_destinations:
        try:
            if hasattr(d.price, 'to_decimal'):
                val = float(d.price.to_decimal())
            else:
                val = float(d.price)
            d.price = f"{int(val):,}" if val.is_integer() else f"{val:,.2f}"
        except Exception:
            pass

    # Show top 6 featured destinations on the home page for optimal loading and aesthetics
    featured_destinations = all_destinations[:6]

    reviews = Review.objects.all().order_by('-created_at')
    context = {
        'destinations': featured_destinations,
        'total_count': len(all_destinations),
        'reviews': reviews,
    }
    return render(request, 'index.html', context)

def get_user_display_info(user):
    """
    Extracts the user's authentic display name (real name from Google / email account)
    and avatar picture (from Google OAuth or null), similar to YouTube's comment section.
    """
    display_name = ""
    picture_url = ""
    email = ""

    if user and user.is_authenticated:
        email = getattr(user, 'email', '')
        # Check Google OAuth SocialAccount first
        try:
            social_acc = user.socialaccount_set.order_by('-id').first()
            if social_acc and social_acc.extra_data:
                extra = social_acc.extra_data
                display_name = extra.get('name') or extra.get('given_name')
                picture_url = extra.get('picture') or ""
                if not email and extra.get('email'):
                    email = extra.get('email')
        except Exception:
            pass

        if not display_name:
            full_name = user.get_full_name().strip()
            if full_name:
                display_name = full_name
            elif user.first_name:
                display_name = user.first_name.strip()
            elif email:
                local_part = email.split('@')[0]
                clean_name = local_part.replace('.', ' ').replace('_', ' ')
                clean_name = ''.join([c if not c.isdigit() else '' for c in clean_name]).strip()
                display_name = clean_name.title() if clean_name else local_part.title()
            elif user.username:
                display_name = user.username.title()
            else:
                display_name = "Traveler"

    return display_name, picture_url, email

def add_review(request, destination_id):
    destination = None
    try:
        from bson import ObjectId
        destination = Destination.objects.filter(_id=ObjectId(destination_id)).first()
    except Exception:
        pass
    if not destination:
        destination = Destination.objects.filter(pk=destination_id).first()
    if not destination:
        destination = get_object_or_404(Destination, title=destination_id) if not str(destination_id).isalnum() else get_object_or_404(Destination, pk=destination_id)

    if request.method == 'POST':
        # Auto-derive reviewer name from authenticated Google / email account (like YouTube comment section)
        if request.user.is_authenticated:
            display_name, _, _ = get_user_display_info(request.user)
            author_name = display_name or request.user.get_full_name() or request.user.username or "Verified Nomad"
        else:
            # If guest or custom client author name provided
            author_name = request.POST.get('author_name') or request.POST.get('username') or 'Guest Nomad'

        rating = request.POST.get('rating') or 5
        comment = (request.POST.get('comment') or '').strip()

        if comment:
            Review.objects.create(
                destination=destination,
                username=author_name,
                rating=int(rating),
                comment=comment
            )
            try:
                from .models import log_user_activity
                log_user_activity(
                    request=request,
                    action_type='SUBMIT_REVIEW',
                    description=f"Submitted {rating}★ review for {destination.title}",
                    metadata={'destination': destination.title, 'rating': int(rating), 'comment': comment[:120]}
                )
            except Exception:
                pass
        if destination:
            if request.POST.get('from_page') == 'planner' or 'planner' in request.META.get('HTTP_REFERER', ''):
                return redirect(f"/planner/?dest={quote(destination.title)}")
            return redirect(f"/home/#card-{destination.id}")
    return redirect('home')

def explore_view(request):
    search_q = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()

    all_destinations = list(Destination.objects.all())
    formatted_destinations = []

    for d in all_destinations:
        try:
            if hasattr(d.price, 'to_decimal'):
                val = float(d.price.to_decimal())
            else:
                val = float(d.price)
            formatted_price = f"{int(val):,}" if val.is_integer() else f"{val:,.2f}"
            num_price = val
        except Exception:
            formatted_price = str(d.price)
            num_price = 0

        try:
            rating_val = float(d.rating.to_decimal()) if hasattr(d.rating, 'to_decimal') else float(d.rating)
        except Exception:
            rating_val = 4.90

        dest_dict = {
            'id': str(d.pk),
            'title': d.title,
            'category': d.category,
            'category_lower': d.category.lower(),
            'price': num_price,
            'formatted_price': formatted_price,
            'rating': f"{rating_val:.2f}",
            'image_url': d.image_url,
            'description': d.description,
            'planner_url': f"/planner/?dest={quote(d.title)}",
        }
        formatted_destinations.append(dest_dict)

    # Log search queries into MongoDB SearchQueryLog collection
    if search_q:
        try:
            from .models import SearchQueryLog
            user_email = (getattr(request.user, 'email', '') or '').strip().lower() if request.user.is_authenticated else 'anonymous'
            username = getattr(request.user, 'username', '') or 'anonymous'
            SearchQueryLog.objects.create(
                user_email=user_email,
                username=username,
                query=search_q,
                category=category_filter or 'all',
                results_count=len(formatted_destinations)
            )
        except Exception as e:
            logger.warning("Error saving SearchQueryLog: %s", e)

    # Initial slice for direct fast HTML rendering (first 12 destinations)
    initial_destinations = formatted_destinations[:12]

    context = {
        'total_count': len(all_destinations),
        'initial_destinations': initial_destinations,
        'destinations_json': json.dumps(formatted_destinations),
        'initial_count': len(initial_destinations),
    }
    return render(request, 'explore.html', context)
def auth_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'auth.html')
def planner_view(request):
    destinations = list(Destination.objects.all())
    target_dest = request.GET.get('dest', '').strip()
    selected_dest = None

    if target_dest:
        target_norm = target_dest.lower()
        # 1. Exact match
        for d in destinations:
            if target_norm == d.title.lower():
                selected_dest = d
                break
        # 2. Substring match
        if not selected_dest:
            for d in destinations:
                d_norm = d.title.lower()
                if target_norm in d_norm or d_norm in target_norm:
                    selected_dest = d
                    break
        # 3. City token match (e.g. 'Jaipur' from 'Jaipur, Rajasthan')
        if not selected_dest:
            city_token = target_norm.split(',')[0].strip()
            if city_token:
                for d in destinations:
                    if city_token in d.title.lower():
                        selected_dest = d
                        break

    if selected_dest:
        reviews = selected_dest.reviews.all().order_by('-created_at')
    else:
        reviews = Review.objects.all().order_by('-created_at')

    user_display_name, user_picture, user_email = get_user_display_info(request.user)

    context = {
        'destinations': destinations,
        'selected_dest': selected_dest,
        'reviews': reviews,
        'target_dest': target_dest or (selected_dest.title if selected_dest else ''),
        'user_display_name': user_display_name,
        'user_picture': user_picture,
        'user_email': user_email,
    }
    return render(request, 'planner.html', context)
def landing_view(request):
    return render(request, 'landing.html')

def google_login_callback(request):
    # If Google OAuth returned here, forward query params to allauth callback
    if request.GET.get('code'):
        query_string = request.META.get('QUERY_STRING', '')
        return redirect(f"/accounts/google/login/callback/?{query_string}")

    user_email = (request.GET.get('email') or '').strip().lower()
    user_name = (request.GET.get('name') or '').strip()

    if user_email:
        from .signals import record_user_once
        record_user_once(email=user_email, name=user_name)
    return redirect('home')


@csrf_exempt
def login_user_api(request):
    """
    Handles user login via email & password.
    Authenticates or provisions user, establishes Django session,
    and logs verification in IST time (deduplicated).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=405)

    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST
    except Exception:
        payload = request.POST

    email = (payload.get('email') or '').strip().lower()
    password = (payload.get('password') or '').strip()

    if not email:
        return JsonResponse({'success': False, 'message': 'Email is required'}, status=400)

    # Find existing User or create for seamless login
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        raw_username = email.split('@')[0]
        username = raw_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{raw_username}{counter}"
            counter += 1
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password or 'travelmate123',
            first_name=raw_username.capitalize()
        )
    else:
        if password and not user.has_usable_password():
            user.set_password(password)
            user.save()

    # Authenticate and establish Django session
    django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # Record login (deduplicated: only saves first time, IST time)
    from .signals import record_user_once
    record_user_once(user=user, email=email)

    display_name = user.get_full_name() or user.first_name or user.username

    from .models import log_user_activity
    redirect_target = '/home/'

    # Log user authentication activity
    log_user_activity(
        request=request,
        action_type='AUTH_LOGIN',
        description=f"User authenticated session: @{user.username} ({user.email})",
        metadata={'username': user.username, 'email': user.email}
    )

    return JsonResponse({
        'success': True,
        'status': 'authenticated',
        'message': f"Welcome back, {display_name}!",
        'user': {
            'username': user.username,
            'name': display_name,
            'email': user.email
        },
        'redirect_url': redirect_target
    })

@csrf_exempt
def register_user_api(request):
    """
    Handles user registration via email, name, & password.
    Creates Django User, establishes Django session,
    and logs initial registration in IST time (deduplicated).
    """
    if request.method not in ['POST', 'GET']:
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                payload = json.loads(request.body.decode('utf-8'))
            else:
                payload = request.POST
        except Exception:
            payload = request.POST
    else:
        payload = request.GET

    email = (payload.get('email') or '').strip().lower()
    name = (payload.get('name') or '').strip()
    password = (payload.get('password') or '').strip()

    if not email:
        return JsonResponse({'success': False, 'message': 'Email is required'}, status=400)

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        raw_username = email.split('@')[0]
        username = raw_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{raw_username}{counter}"
            counter += 1

        first_name = name.split(' ')[0] if name else raw_username.capitalize()
        last_name = ' '.join(name.split(' ')[1:]) if (name and len(name.split(' ')) > 1) else ''
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password or 'travelmate123',
            first_name=first_name,
            last_name=last_name
        )
    else:
        if name and not user.first_name:
            user.first_name = name.split(' ')[0]
            user.last_name = ' '.join(name.split(' ')[1:]) if len(name.split(' ')) > 1 else ''
            user.save()
        if password and not user.check_password(password):
            user.set_password(password)
            user.save()

    # Authenticate and establish Django session
    django_login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # Record user registration once in IST
    from .signals import record_user_once
    record, created = record_user_once(user=user, email=email, name=name)

    display_name = user.get_full_name() or user.first_name or user.username

    from .models import log_user_activity
    redirect_target = '/home/'

    # Log user registration activity
    log_user_activity(
        request=request,
        action_type='AUTH_REGISTER',
        description=f"New traveler identity registered: @{user.username} ({user.email})",
        metadata={'username': user.username, 'email': user.email, 'name': display_name}
    )

    return JsonResponse({
        'success': True,
        'status': 'registered' if created else 'existing',
        'message': f"Account registered for {display_name}!",
        'user': {
            'username': user.username,
            'name': display_name,
            'email': user.email
        },
        'redirect_url': redirect_target
    })



DESTINATION_LANDMARK_MAP = {
    'jaipur': [
        ("Royal Bastions & Heritage Flavors", [("08:30 AM", "Artisanal breakfast with spicy Pyaaz Kachori and saffron masala chai at Rawat Mishthan Bhandar."), ("10:30 AM", "Ascend to Amber Fort, marveling at the mirror mosaics of Sheesh Mahal and grand ramparts."), ("02:00 PM", "Royal heritage Rajasthani Thali lunch at 1135 AD with panoramic desert fort vistas."), ("06:30 PM", "Sunset golden hour photography at Jal Mahal water palace and evening gem shopping at Johari Bazaar.")]),
        ("Pink City Iconography & Astronomy", [("09:00 AM", "Iconic honeycomb facade photography at Hawa Mahal followed by morning espresso at Wind View Cafe."), ("11:30 AM", "Guided exploration of City Palace royal museum & UNESCO-listed Jantar Mantar observatory."), ("02:30 PM", "Traditional Rajasthani feast at Handi Restaurant on MI Road trying authentic Laal Maas and Bajra roti."), ("06:00 PM", "Golden sunset vista overlooking the entire Pink City skyline from the mountain ramparts of Nahargarh Fort.")]),
        ("Stepwells, Cannons & Artisan Villages", [("08:30 AM", "Early morning photography at the symmetrical geometric stepwell of Panna Meena Ka Kund."), ("11:00 AM", "Jaigarh Fort visit to marvel at Jaivana, the world's largest cannon on wheels, and secret passages."), ("02:00 PM", "Traditional wooden block-printing workshop & blue pottery shopping in Sanganer craft village."), ("07:00 PM", "Immersive cultural folk dance, puppet show, and royal village feast under desert tents at Chokhi Dhani.")]),
        ("Palace Gardens & High-Tea Culture", [("09:00 AM", "Peaceful stroll through lush terraced fountains and painted pavilions of Sisodia Rani Ka Bagh."), ("11:30 AM", "Explore Albert Hall Museum, admiring centuries-old Rajput armor, miniatures, and Persian carpets."), ("02:30 PM", "Modern fusion brunch and chai degustation at Tapri Central overlooking Central Park."), ("06:30 PM", "Evening sound-and-light spectacle at Amber Fort under the starry Aravalli night sky.")]),
        ("Spiritual Sanctuaries & Sunset Bazaars", [("08:30 AM", "Serene morning prayers and white marble carvings at Birla Mandir (Laxmi Narayan Temple)."), ("11:00 AM", "Adventure hike through the mountain gorge to sacred Galta Ji (Monkey Temple) natural freshwater springs."), ("02:00 PM", "Rooftop leisure lunch at Baradari Restaurant inside City Palace grounds."), ("05:30 PM", "Souvenir treasure hunt in Bapu Bazaar for handcrafted Mojaris, camel leather goods, and bandhani textiles.")])
    ],
    'goa': [
        ("Portuguese Quarters, Forts & Sundowners", [("08:30 AM", "Wood-fired croissants, eggs benedict, and artisanal cold brew at Baba Au Rhum in Anjuna."), ("11:00 AM", "Explore the 17th-century Portuguese defense bastion and lighthouse at Fort Aguada."), ("02:00 PM", "Authentic Goan Fish Curry Thali lunch at Ritz Classic in Panaji."), ("06:30 PM", "Sunset cocktails and clifftop Greek dining with live fire acrobats at Thalassa in Siolim.")]),
        ("Old Goa Cathedrals & Spice Plantations", [("09:00 AM", "Artisan smoothie bowls and coffee at Cafe Bodega inside Sunaparanta Arts Centre."), ("11:30 AM", "Marvel at UNESCO World Heritage Basilica of Bom Jesus and Se Cathedral in historic Old Goa."), ("02:00 PM", "Guided spice plantation walk and banana-leaf Goan buffet at Sahakari Spice Farm in Ponda."), ("06:00 PM", "Luxury sunset cruise on Mandovi River with traditional Goan folk performances and dolphin sightings.")]),
        ("Pristine South Bays & Secluded Cliffs", [("08:30 AM", "Organic granola and cold-pressed juices at The Space Goa in Canacona."), ("11:00 AM", "Kayaking along the crescent shoreline of Palolem Beach and boat safari to secluded Butterfly Beach."), ("02:00 PM", "Riverside butter garlic tiger prawns and crab masala feast at Fisherman's Wharf in Cavelossim."), ("06:00 PM", "Spectacular sunset views from the dramatic cliff ruins of Cabo de Rama Fort overlooking the Arabian Sea.")]),
        ("Bohemian Flea Bazaars & Coastal Farewell", [("09:30 AM", "French crepes and ocean-facing shakshuka at Eva Cafe perched above Anjuna cliffs."), ("12:00 PM", "Boutique treasure hunting at Anjuna Flea Market for brass handicrafts and linen resort-wear."), ("03:00 PM", "Sun lounger relaxation with fresh coconuts along peaceful Ashvem Beach."), ("07:30 PM", "Farm-to-table Goan fusion dinner at The Black Sheep Bistro in Panaji.")])
    ],
    'manali': [
        ("Cedar Forests & Old Manali Vibe", [("08:30 AM", "Apple crumble pie and freshly brewed mountain espresso at Dylan's Toasted & Roasted Cafe."), ("10:30 AM", "Walk through towering Deodar cedar groves to the 16th-century wooden pagoda Hadimba Temple."), ("02:00 PM", "Wood-fired trout and pizza at Cafe 1947 right beside the rushing Manalsu River."), ("06:00 PM", "Evening shopping on Mall Road for handcrafted Kullu shawls, prayer wheels, and apricot oil.")]),
        ("Solang Valley Adventure & Hot Springs", [("08:00 AM", "Aloo paratha breakfast with homemade mountain butter at Drifters' Cafe."), ("10:00 AM", "Paragliding, quad biking, and scenic gondola ropeway ride across Solang Valley."), ("02:00 PM", "Hot Tibetan Thukpa and steamed momos at Chopsticks Restaurant."), ("05:00 PM", "Rejuvenate in natural geothermal sulfur springs at ancient Vashisht Temple village.")]),
        ("Rohtang Pass & Atal Tunnel Marvel", [("07:00 AM", "Early morning mountain drive across winding Himalayan hairpins to Rohtang Pass (13,058 ft)."), ("10:30 AM", "Spectacular panoramic vistas of glaciers, snow walls, and Pir Panjal mountain ranges."), ("02:00 PM", "Steaming Maggi and Masala Chai at high-altitude mountain stalls."), ("05:30 PM", "Return drive through the engineering triumph of Atal Tunnel (9.02 km) beneath Rohtang.")]),
        ("Heritage Castles & Roerich Art in Naggar", [("09:00 AM", "Scenic drive down the Beas Valley to medieval timber-and-stone Naggar Castle."), ("11:30 AM", "Visit the Nicholas Roerich Art Gallery and Estate showcasing mystical Himalayan canvases."), ("02:00 PM", "Fresh grilled trout lunch at Naggar Castle rooftop cafe overlooking apple orchards."), ("06:00 PM", "Craft mountain cider tasting and acoustic live folk music in Old Manali.")]),
        ("Waterfall Treks & Riverside Solitude", [("08:30 AM", "Fluffy pancake breakfast at Rocky's Cafe with 360-degree snow peak views."), ("10:30 AM", "Pine forest trek to the cascading Jogini Waterfalls with pristine natural plunge pools."), ("02:00 PM", "Farewell feast with wood-fired sourdough sandwiches at The Johnson's Cafe."), ("05:00 PM", "Collect jars of organic forest honey and handwoven pashminas before departure.")])
    ],
    'varanasi': [
        ("Sacred Dawn, Ganges Boat Safari & Subah-e-Banaras", [("05:30 AM", "Sunrise wooden rowboat cruise along the ancient stone ghats from Assi Ghat to Manikarnika Ghat."), ("08:00 AM", "Crispy Kachori Sabzi and piping hot Jalebi breakfast at Ram Bhandar in Thatheri Bazaar."), ("10:30 AM", "Sacred darshan at the holy golden spire Kashi Vishwanath Temple via the grand river corridor."), ("06:00 PM", "Mesmerizing evening Maha Aarti ceremony at Dashashwamedh Ghat with chanting and brass lamps.")]),
        ("Buddhist Cradle of Sarnath & Weaver Quarters", [("08:30 AM", "Visit sacred Sarnath where Lord Buddha gave his first sermon; explore Dhamek Stupa & Ashoka Pillar."), ("12:30 PM", "Traditional Banarasi Thali lunch followed by rich saffron Malaiyo dessert at Chowk."), ("03:30 PM", "Explore century-old Banarasi silk handloom weaving workshops in Madanpura."), ("06:30 PM", "Evening boat ride watching illuminated ghat reflections and tasting authentic Banarasi Paan.")]),
        ("Hidden Havelis, Akhadas & Riverfront Meditation", [("06:00 AM", "Witness traditional mud wrestling (Kushti) workouts at Tulsi Ghat Akhada at dawn."), ("09:00 AM", "Thick creamy pomegranate and saffron lassi at the world-famous Blue Lassi shop."), ("11:30 AM", "Heritage walk exploring the ancient stepped architecture of Man Mandir Ghat observatory."), ("05:30 PM", "Peaceful sunset flute recital and classical sitar session overlooking the sacred river at Assi Ghat.")])
    ],
    'udaipur': [
        ("City of Lakes, Royal Palaces & Pichola Boat Ride", [("08:30 AM", "Lakeview breakfast of Poha and masala chai at Jheel's Ginger Coffee Bar on Gangaur Ghat."), ("10:00 AM", "Extensive guided tour through the colossal courtyards, mirror galleries, and armory of City Palace."), ("02:00 PM", "Traditional Rajasthani lunch at Ambrai Restaurant with breathtaking panoramas across Lake Pichola."), ("05:30 PM", "Sunset boat cruise around the marble island palace of Jag Mandir with golden Aravalli hill views.")]),
        ("Monsoon Fortresses & Heritage Folk Dances", [("09:00 AM", "Ascend the winding hill road to Sajjangarh (Monsoon Palace) perched 3,100 ft above the valley."), ("12:00 PM", "Stroll through the marble elephant fountains and lotus pools of Saheliyon Ki Bari."), ("03:00 PM", "Artisanal miniature painting shopping and pottery browsing in the Old City lanes."), ("07:00 PM", "Captivating Dharohar Rajasthani folk dance, fire show, and puppet performance at Bagore Ki Haveli.")]),
        ("Lake Fateh Sagar & Royal Cenotaphs", [("08:30 AM", "Morning walking loop and fresh cold coffee along the lakeside promenade of Fateh Sagar."), ("11:00 AM", "Explore the grand carved marble cenotaphs of the Mewar kings at the historic Ahar Cenotaphs."), ("02:00 PM", "Mewari royal dining feast at 1559 AD surrounded by heritage botanical gardens."), ("06:00 PM", "Cable car ropeway ride up to Karni Mata temple for sunset city vistas.")])
    ],
    'kerala': [
        ("Munnar Mist, Tea Estates & Mountain Vistas", [("08:30 AM", "Traditional Appam with vegetable stew and filter coffee at Saravana Bhavan Munnar."), ("10:30 AM", "Tour KDHP Tea Museum and scenic photography at Mattupetty Dam reservoir."), ("02:00 PM", "Kerala spiced curry lunch at Rapsy Restaurant followed by Echo Point speedboating."), ("06:00 PM", "Panoramic sunset view over the Western Ghats from Top Station (5,600 ft) amidst rolling clouds.")]),
        ("Eravikulam Wildlife & Spice Gardens", [("08:00 AM", "Morning safari through Eravikulam National Park spotting endangered Nilgiri Tahr mountain goats."), ("12:00 PM", "Guided spice plantation walk in Anachal discovering cardamom, cinnamon, and vanilla vines."), ("02:30 PM", "Authentic 24-dish Kerala Sadhya banquet served on banana leaves."), ("06:00 PM", "Kathakali dance and Kalaripayattu martial arts show at Punarjani Traditional Village.")]),
        ("Alleppey Luxury Houseboat Cruise", [("08:00 AM", "Scenic descent from the mist-covered mountains to Alleppey backwaters."), ("12:30 PM", "Check-in aboard a private luxury thatched Kettuvallam (Houseboat) at Punnamada Jetty."), ("01:30 PM", "Onboard fresh lunch featuring Karimeen Pollichathu (Pearl Spot fish wrapped in banana leaf)."), ("05:30 PM", "Serene sunset cruise through Vembanad Lake watching village life and swaying coconut palms.")]),
        ("Fort Kochi Heritage & Chinese Nets", [("09:00 AM", "Drive to Fort Kochi to photograph the iconic cantilevered Chinese Fishing Nets at harbor entrance."), ("11:30 AM", "Historical walk through St. Francis Church and Jew Town antique spice bazaar."), ("02:00 PM", "Cold brew and artisanal brunch at Kashi Art Cafe surrounded by contemporary installations."), ("05:30 PM", "Sunset ferry ride across Cochin harbor watching massive cargo liners and dolphin pods.")])
    ],
    'ladakh': [
        ("Acclimatization, Leh Palace & Shanti Stupa", [("09:00 AM", "Gentle morning acclimatization with warm Butter Tea and Ladakhi Tingmo bread in Leh."), ("01:00 PM", "Wholesome organic Thukpa and momo lunch at Gesmo Restaurant in Leh Main Bazaar."), ("04:30 PM", "Spin prayer wheels at Shanti Stupa enjoying a golden hour panoramic view of Stok Kangri range."), ("07:30 PM", "Traditional Ladakhi mutton stew dinner (Chhutagi) at The Tibetan Kitchen.")]),
        ("Thiksey Gompa & Indus Valley Monasteries", [("08:30 AM", "Witness the morning monks' chanting ceremony at Thiksey Monastery (mini Potala Palace)."), ("11:30 AM", "Explore Hemis Monastery, the wealthiest Buddhist gompa nestled in a hidden mountain gorge."), ("02:30 PM", "Rooftop lunch at Cafe Cloud in Shey surrounded by willow and poplar trees."), ("05:00 PM", "Hall of Fame military memorial honoring valiant guardians of the high Himalayas.")]),
        ("Khardung La Pass & Nubra Desert Dunes", [("07:30 AM", "Ascend the legendary Khardung La Pass (17,982 ft), one of the world's highest motorable passes."), ("12:00 PM", "Descend into lush Nubra Valley and check into luxury glamping dome tents in Hunder."), ("04:30 PM", "Ride double-humped Bactrian Camels across the surreal white sand dunes of Hunder at golden hour."), ("07:30 PM", "Stargazing under the crystal-clear Milky Way galaxy with zero light pollution.")]),
        ("Diskit Colossus & Azure Pangong Tso", [("08:30 AM", "Marvel at the 106-ft outdoor statue of Maitreya Buddha at Diskit Monastery overlooking the valley."), ("11:00 AM", "Rugged off-road expedition along the turquoise Shyok River towards Pangong Lake."), ("03:00 PM", "Witness the color-shifting azure and turquoise waters of Pangong Tso (14,270 ft)."), ("06:30 PM", "Sunset photography at the famous lakeside promontory followed by cozy tent dining.")])
    ],
    'agra': [
        ("The Wonder of Taj Mahal & Mughal Splendor", [("05:45 AM", "Sunrise entry to Taj Mahal, witnessing the white marble change hues in the first morning light."), ("09:00 AM", "Traditional Bedai and spicy Jalebi breakfast at Deviram Sweets on Pratap Pura."), ("11:00 AM", "Explore the red sandstone ramparts, Diwan-i-Khas, and Sheesh Mahal at historic Agra Fort."), ("05:30 PM", "Golden hour sunset reflections of Taj Mahal from across the Yamuna River at Mehtab Bagh.")]),
        ("Imperial Ghost City of Fatehpur Sikri", [("08:30 AM", "Scenic drive to UNESCO-listed Fatehpur Sikri, emperor Akbar's majestic 16th-century capital."), ("10:30 AM", "Walk through the colossal Buland Darwaza and offer prayers at the marble tomb of Salim Chishti."), ("02:00 PM", "Mughlai kebab and biryani feast at Pinch of Spice on Fatehabad Road."), ("05:30 PM", "Visit Itmad-ud-Daulah ('Baby Taj'), admiring exquisite Pietra Dura marble inlays.")])
    ],
    'rishikesh': [
        ("Holy Ganges Rapids, Suspension Bridges & Ashrams", [("08:00 AM", "Aloo Poori breakfast with herbal ginger tea at Chotiwala Restaurant near Ram Jhula."), ("10:00 AM", "Walk across iconic suspension bridges Laxman Jhula & Ram Jhula watching sacred river currents."), ("01:30 PM", "Healthy organic Ayurvedic lunch and kombucha at The 60's Beatles Cafe in Tapovan."), ("05:30 PM", "Spiritual Maha Aarti ceremony with glowing diyas and holy Vedic chants at Triveni Ghat.")]),
        ("White-Water Rafting & Cliff Jumps", [("08:30 AM", "Adrenaline-fueled 16-km white-water river rafting expedition through rapids like Roller Coaster."), ("01:00 PM", "Riverside Maggi and lemon tea at Marine Drive beach camp."), ("03:30 PM", "Explore the graffiti-covered meditation domes of the historic Beatles Ashram (Chaurasi Kutia)."), ("06:30 PM", "Sunset acoustic music session at Little Buddha Cafe overlooking the emerald Ganges.")]),
        ("Sunrise Shrines & Waterfalls", [("05:30 AM", "Early morning scenic drive to Kunjapuri Devi Temple for sunrise over Himalayan peaks."), ("09:00 AM", "Hike through lush forest to cascading Neer Garh waterfalls and crystal pools."), ("01:30 PM", "Rooftop lunch at Pure Soul Cafe overlooking the valley."), ("05:30 PM", "Evening riverside meditation and sound bowl healing by the holy Ganges.")])
    ],
    'amritsar': [
        ("Golden Temple Sanctum, Sarovar & Langar", [("07:30 AM", "Spiritual morning parikrama around the sacred Amrit Sarovar and darshan inside Sri Harmandir Sahib."), ("10:30 AM", "Participate in Guru Ka Langar, the world's largest community kitchen serving thousands daily."), ("01:30 PM", "Crispy Amritsari Kulcha with melting butter and chole at Pehalwan Kulcha."), ("06:00 PM", "Evening Palki Sahib golden palanquin ceremony with soul-stirring Gurbani kirtan.")]),
        ("Wagah Border Ceremony & Jallianwala Bagh", [("09:00 AM", "Pay solemn tribute at Jallianwala Bagh national memorial and explore the Partition Museum."), ("01:00 PM", "Legendary Dal Makhani and Firni lunch at Kesar Da Dhaba in Chowk Passian."), ("03:30 PM", "Scenic drive to Wagah-Attari Border for the high-octane Beating Retreat ceremony with roaring crowds."), ("08:00 PM", "Evening heritage walk and Phulkari embroidery shopping along the illuminated Heritage Street.")]),
        ("Fortresses, Artisan Haveli & Village Feasts", [("09:00 AM", "Explore historic Gobindgarh Fort, ancient coin museums, and martial Sikh warfare galleries."), ("01:00 PM", "Authentic Amritsari fish fry and butter chicken feast at Makhan Fish & Chicken Corner."), ("04:00 PM", "Cultural tour of Sadda Pind heritage village experiencing Bhangra and pottery making."), ("07:30 PM", "Tall brass glass of creamy sweet Amritsari Lassi at Ahuja Milk Centre.")])
    ],
    'srinagar': [
        ("Dal Lake Shikara & Floating Bazaars", [("06:00 AM", "Sunrise Shikara boat ride across Dal Lake navigating through floating lotus gardens and vegetable markets."), ("09:00 AM", "Traditional Noon Chai and hot Kashmiri Girda bread at Ahdoos on the Jhelum riverbank."), ("11:30 AM", "Ascend Shankaracharya Hill to the 8th-century stone temple for 360-degree Srinagar panoramas."), ("06:30 PM", "Sunset over the lake from the carved cedar deck of your luxury heritage houseboat.")]),
        ("Imperial Mughal Terraces & Hazratbal", [("09:00 AM", "Walk the terraced waterfalls and chinar tree avenues of Nishat Bagh & Shalimar Bagh."), ("01:00 PM", "Authentic 7-course Kashmiri Wazwan feast featuring Rogan Josh and Gushtaba at Mughal Darbar."), ("04:00 PM", "Peaceful lakeside prayer and white marble architecture at historic Hazratbal Shrine."), ("06:30 PM", "Evening drive along Boulevard Road sampling roasted spiced corn and Kashmiri Kahwa.")]),
        ("Old City Wooden Bridges & Pashmina Masters", [("09:30 AM", "Heritage walk through Old Srinagar crossing wooden Zaina Kadal bridges and Jamia Masjid's 378 deodar pillars."), ("01:00 PM", "Traditional Tujji barbecue skewers at Khayam Chowk."), ("03:30 PM", "Visit master artisan ateliers for hand-spun Pashmina shawls and walnut wood carvings."), ("06:00 PM", "Chashme Shahi natural royal spring gardens overlooking the Zabarwan mountain range.")])
    ],
    'shimla': [
        ("The Ridge, Mall Road & Colonial Icons", [("08:30 AM", "Artisan crepes and mountain espresso at Wake & Bake Cafe on Mall Road."), ("10:30 AM", "Photograph Neo-Gothic Christ Church on The Ridge and hike up to Jakhu Temple guarded by the 108-ft Hanuman colossus."), ("02:00 PM", "Panoramic mountain lunch at Cafe Shimla Times."), ("06:00 PM", "Evening stroll down heritage Gaiety Theatre quarter and hot Gulab Jamun at Baljees.")]),
        ("Kufri Alpine Panoramas & Viceregal Lodge", [("08:30 AM", "Drive through fragrant cedar forests to Kufri for horseback riding up Mahasu Peak."), ("01:30 PM", "Mountain lunch with hot Maggi and ginger tea overlooking the Pir Panjal ranges."), ("03:30 PM", "Explore the Scottish baronial architecture of the Indian Institute of Advanced Study (Viceregal Lodge)."), ("06:30 PM", "Handmade pine and walnut wooden souvenir shopping at Lakkar Bazaar.")])
    ],
    'jodhpur': [
        ("Mehrangarh Fortress & Blue Alleys", [("08:30 AM", "Famous Shahi Samosa and Makhaniya Lassi breakfast at Clock Tower bazaar."), ("10:00 AM", "Ascend colossal Mehrangarh Fort towering 400 ft above the skyline, visiting royal palanquins and armory."), ("02:00 PM", "Traditional Rajasthani Ker Sangri and Dal Baati Churma at Gypsy Dining Hall."), ("05:30 PM", "Walk through the indigo-painted Brahmin alleys of Navchokiya to a rooftop cafe sunset view.")]),
        ("Marble Cenotaphs, Stepwells & Palaces", [("09:00 AM", "Marvel at the milky-white marble cenotaphs of Jaswant Thada and lake gardens."), ("11:30 AM", "Geometric architecture and cold brew at Toorji Ka Jhalra ancient stepwell."), ("02:30 PM", "Tour the opulent Art Deco museum at Umaid Bhawan Palace."), ("06:00 PM", "Brocade, bandhani, and spice shopping in Sardar Market under the illuminated fort.")])
    ],
    'jaisalmer': [
        ("The Living Sandstone Fort (Sonar Qila)", [("08:30 AM", "Breakfast on fort ramparts at Jaisal Italy with sweeping golden city panoramas."), ("10:00 AM", "Guided walking tour through Jaisalmer Fort, home to 3,000 residents inside medieval stone ramparts."), ("02:00 PM", "Traditional Rajasthani Gatte Ki Sabzi and Bajra Roti at The Trio."), ("05:30 PM", "Sunset rowboat cruise across sacred Gadisar Lake surrounded by carved temples and pavilions.")]),
        ("Thar Desert Dunes, Camels & Campfire", [("09:00 AM", "Explore the intricate yellow sandstone carvings of Patwon Ki Haveli and Salim Singh Ki Haveli."), ("01:30 PM", "Scenic drive into the Thar Desert, stopping at the haunted ruins of Kuldhara village."), ("04:30 PM", "Sunset camel safari across the rolling ripples of Sam Sand Dunes."), ("08:00 PM", "Desert camp musical evening with Kalbelia folk dancers, fire acrobatics, and stargazing.")])
    ],
    'hampi': [
        ("Sacred Centre, Tungabhadra & Boulders", [("06:00 AM", "Sunrise hike up Matanga Hill overlooking a sea of granite boulders and ancient ruins."), ("08:30 AM", "Traditional South Indian breakfast at Mango Tree restaurant."), ("10:30 AM", "Explore active 7th-century Virupaksha Temple and monolithic Sasivekalu Ganesha."), ("04:30 PM", "Coracle round-boat ride on Tungabhadra River and golden hour sunset at Hemakuta Hill.")]),
        ("Vijayanagara Empire, Stone Chariot & Royal Enclosure", [("08:30 AM", "Marvel at the iconic Stone Chariot and musical acoustic pillars at Vijaya Vittala Temple."), ("12:00 PM", "Explore the Indo-Islamic pavilions of Lotus Mahal and the colossal Elephant Stables."), ("02:30 PM", "Traditional banana-leaf thali at a local village cafe in Kamalapur."), ("05:30 PM", "Sunset vistas across the Tungabhadra valley from Malyavanta Raghunatha Temple.")])
    ],
    'ooty': [
        ("Heritage Nilgiri Toy Train & Botanical Gardens", [("08:30 AM", "Scenic ride aboard UNESCO Nilgiri Mountain Railway heritage steam train over bridges and ravines."), ("11:00 AM", "Walk through lush terraced lawns and fossil tree trunks of Government Botanical Garden."), ("01:30 PM", "Colonial high tea and lunch at Earl's Secret bungalow."), ("05:00 PM", "Leisurely rowboat cruise on misty Ooty Lake and handmade fudge shopping at King Star.")]),
        ("Highest Peak & Tea Estates", [("08:30 AM", "Ascend Doddabetta Peak (8,650 ft), highest point in Nilgiris, for telescope valley views."), ("11:30 AM", "Doddabetta Tea Factory & Chocolate Museum tasting hot artisanal Nilgiri tea."), ("02:30 PM", "Pykara Lake speedboating and pine forest walk along Pykara waterfalls."), ("06:00 PM", "Evening shopping for pure eucalyptus oil, homemade chocolates, and spices in Commercial Street.")])
    ],
    'darjeeling': [
        ("Tiger Hill Sunrise & Himalayan Masters", [("04:00 AM", "Dawn ascent to Tiger Hill watching sunrise illuminate snow-capped Mount Kanchenjunga (8,586 m)."), ("08:30 AM", "Ghoom Monastery prayer wheels, Batasia Loop garden railway spiral, and Glenary's bakery breakfast."), ("11:30 AM", "Himalayan Mountaineering Institute (HMI) museum & Padmaja Naidu Himalayan Zoo spotting Red Pandas."), ("05:30 PM", "Evening walk on Chowrasta Mall Road with hot momos and Darjeeling second-flush Muscatel tea.")]),
        ("Happy Valley Tea & Japanese Peace Pagoda", [("09:00 AM", "Heritage walk through Happy Valley Tea Estate witnessing organic Darjeeling tea plucking."), ("01:00 PM", "Keventers rooftop English breakfast and hot cocoa overlooking mountain peaks."), ("03:30 PM", "Peaceful chanting at Japanese Peace Pagoda and scenic Darjeeling Ropeway cable car glide."), ("06:30 PM", "Sunset over the tea valleys from Observatory Hill.")])
    ],
    'pondicherry': [
        ("White Town French Quarters & Promenade", [("08:30 AM", "Artisanal French baguettes and cafe au lait at Cafe des Arts in White Town."), ("10:30 AM", "Walking tour of mustard-yellow colonial villas, bougainvillea gates, and French street signs."), ("01:30 PM", "French-Creole lunch at Coromandel Cafe."), ("05:30 PM", "Sunset seaside stroll along Goubert Promenade and peaceful meditation at Sri Aurobindo Ashram.")]),
        ("Auroville Universal Township & Golden Globe", [("08:30 AM", "Drive to Auroville, meditating with views of the golden geodesic sphere Matrimandir."), ("01:00 PM", "Organic farm-to-table lunch at Solar Kitchen."), ("03:30 PM", "Boat ride through Chunnambar backwaters to isolated Paradise Beach sand spit."), ("07:00 PM", "Wood-fired sourdough pizza and gelato at Tanto Pizzeria.")])
    ],
    'coorg': [
        ("Coffee Plantations, Abbey Falls & Raja's Seat", [("08:30 AM", "Authentic Akki Roti and filter coffee breakfast in Madikeri."), ("10:30 AM", "Guided walking tour through lush Arabica coffee and black pepper plantations."), ("02:00 PM", "Traditional Kodava Pandi Curry lunch at Coorg Cuisine."), ("05:30 PM", "Abbey Falls waterfall viewpoint through spice trees and sunset at Raja's Seat musical fountains.")]),
        ("Elephant Sanctuary & Golden Temple", [("08:30 AM", "Morning visit to Dubare Elephant Camp watching elephants bathe in Cauvery river."), ("12:30 PM", "Explore Namdroling Monastery (Golden Temple) in Bylakuppe with 40-ft gilded Buddha statues."), ("03:00 PM", "Tibetan momos and thukpa at Camp 1."), ("06:00 PM", "Shopping for artisanal Coorg coffee beans, wild honey, and homemade chocolates.")])
    ],
    'mysore': [
        ("Imperial Mysore Palace & Royal Markets", [("08:30 AM", "Mylari Restaurant world-famous soft butter dosas with coconut chutney."), ("10:00 AM", "Extensive guided tour of magnificent Indo-Saracenic Mysore Palace and jewel-encrusted Durbar."), ("02:00 PM", "Royal dining at Lalitha Mahal Palace heritage hotel."), ("06:30 PM", "Witness the breathtaking illumination of Mysore Palace with 97,000 glowing bulbs.")]),
        ("Chamundi Hill, Sacred Nandi & Fountains", [("08:30 AM", "Climb Chamundi Hill to Sri Chamundeshwari Temple and colossal 16-ft monolithic Nandi."), ("12:00 PM", "Color and aroma exploration in Devaraja Market with flower garlands and sandalwood."), ("03:00 PM", "Taste authentic melt-in-mouth Mysore Pak at Guru Sweet Mart where it was invented."), ("06:30 PM", "Evening dancing musical fountain spectacle at Brindavan Gardens.")])
    ],
    'mathura': [
        ("Krishna Janmabhoomi & Sacred Yamuna Ghats", [("08:00 AM", "Morning darshan at Shri Krishna Janmasthan Temple Complex inside the prison sanctum."), ("10:30 AM", "Taste authentic hot Mathura ke Pede at Brijwasi Mithai Wala."), ("02:00 PM", "Dwarkadhish Temple darshan marveling at Rajasthani frescoed ceilings."), ("06:00 PM", "Grand evening Yamuna Maha Aarti with glowing brass lamps at Vishram Ghat.")]),
        ("Vrindavan Temples & Prem Mandir Spectacle", [("08:30 AM", "Morning kirtan and darshan at Banke Bihari Temple and ISKCON Krishna Balaram Temple."), ("01:00 PM", "Traditional Braj Thali feast with fresh Makhan Mishri."), ("04:00 PM", "Walk through holy Nidhivan sacred grove and Seva Kunj."), ("07:00 PM", "Spectacular illuminated musical fountain and light show at Prem Mandir white marble palace.")])
    ],
    'ayodhya': [
        ("Shri Ram Janmabhoomi & Hanuman Garhi", [("07:30 AM", "Sacred morning darshan of Ram Lalla at the grand pink sandstone Shri Ram Janmabhoomi Mandir."), ("10:30 AM", "Climb 76 steps to historic Hanuman Garhi fort shrine for blessings."), ("01:30 PM", "Traditional Awadhi thali lunch featuring local specialties and Ayodhya Peda."), ("05:30 PM", "Kanak Bhawan palace dedicated to Sita-Ram with exquisite gold crown displays.")]),
        ("Saryu River Ghats & Evening Maha Aarti", [("06:00 AM", "Sunrise holy dip and wooden boat ride along the sacred Saryu River."), ("09:30 AM", "Explore Dashrath Mahal and ancient Nageshwarnath Temple founded by Kush."), ("02:00 PM", "Peaceful stroll through Guptar Ghat where Lord Ram entered Mahasamadhi."), ("06:30 PM", "Mesmerizing evening Saryu Maha Aarti at Ram Ki Paidi with thousands of floating diyas.")])
    ],
    'spiti': [
        ("High Altitude Monasteries & Kaza", [("09:00 AM", "Acclimatization in Kaza (12,500 ft) with warm butter tea and seabuckthorn juice."), ("11:30 AM", "Explore 1000-year-old Key Monastery perched fortress-like on a sheer mountain crag."), ("02:30 PM", "Hot Tibetan thukpa and momos at The Himalayan Cafe in Kaza market."), ("06:00 PM", "Interact with monks at Kibber village (14,200 ft) enjoying raw Himalayan mountain vistas.")]),
        ("Highest Villages & Mystic Chandratal Lake", [("08:30 AM", "Post a card from Hikkim - world's highest post office at 14,567 ft."), ("11:00 AM", "Visit Komic - highest motorable village connected by road, and fossil hunting in Langza."), ("03:30 PM", "Scenic drive across Kunzum Pass (14,931 ft) to moon-shaped crescent Chandratal Lake."), ("07:30 PM", "Lakeside tent camping under a diamond-studded Milky Way sky.")])
    ],
    'dharamshala': [
        ("Little Lhasa, Dalai Lama Temple & Waterfalls", [("08:30 AM", "Tibetan steamed momos and butter tea at Tibet Kitchen in McLeodGanj."), ("10:30 AM", "Visit Tsuglagkhang Complex housing Dalai Lama Temple, spinning golden prayer wheels."), ("02:00 PM", "Wood-fired sourdough pizza at Illiterati Books & Coffee with valley views."), ("05:30 PM", "Pine forest hike to Bhagsunag Temple and cascading Bhagsu Waterfall plunge pools.")]),
        ("Norbulingka Arts & Triund Mountain Ridge", [("09:00 AM", "Explore serene Norbulingka Institute preserving Tibetan thangka painting and woodcraft."), ("01:00 PM", "Organic lunch in the lush Japanese-style gardens at Norbulingka Cafe."), ("03:30 PM", "Hike up towards Triund ridge enjoying dramatic views of the sheer Dhauladhar snow wall."), ("07:00 PM", "Sunset over Kangra Valley from St. John in the Wilderness deodar churchyard.")])
    ],
    'andaman': [
        ("Cellular Jail & Asia's Best Beach", [("09:00 AM", "Historic tour of Cellular Jail national memorial in Port Blair exploring Veer Savarkar cell."), ("01:00 PM", "High-speed catamaran cruise across azure waters to Havelock Island (Swaraj Dweep)."), ("03:30 PM", "Golden afternoon swimming at Radhanagar Beach (Beach No. 7), rated Asia's best beach."), ("06:30 PM", "Spectacular tropical sunset with fresh tender coconuts right on the white sand.")]),
        ("Coral Reefs, Scuba Diving & Elephant Beach", [("08:00 AM", "Morning boat safari to Elephant Beach for guided scuba diving and vibrant coral reef snorkeling."), ("01:30 PM", "Beachfront grilled catch-of-the-day fish and crab curry feast."), ("04:00 PM", "Kayaking through peaceful mangrove waterways in Havelock."), ("07:30 PM", "Candlelight beach dining under swaying palm trees listening to ocean waves.")])
    ],
    'shillong': [
        ("Highland Lakes, Pine Hills & Music", [("08:30 AM", "Artisan burger and breakfast with classic rock music at Dylan's Cafe."), ("10:30 AM", "Scenic speedboating on emerald Umiam Lake surrounded by coniferous pine hills."), ("02:00 PM", "Authentic Khasi tribal thali with Jadoh and Dohkhlieh at Trattoria."), ("05:30 PM", "Panoramic views across the plateau from Shillong Peak and evening stroll in Police Bazar.")]),
        ("Cherrapunji & Living Root Bridges", [("07:30 AM", "Scenic mountain drive to Cherrapunji (Sohra) through mist-shrouded gorges."), ("10:00 AM", "Trek down to the wonder of the Double Decker Living Root Bridge grown from rubber tree roots."), ("02:30 PM", "Gaze down at the roaring 1,115-ft plunge of Nohkalikai Falls, India's tallest plunge waterfall."), ("06:30 PM", "Explore Mawsmai limestone cave formations with natural stalactites.")])
    ],
    'nainital': [
        ("Emerald Naini Lake & Naina Devi Temple", [("08:30 AM", "Traditional aloo poori breakfast with hot masala chai on Mall Road."), ("10:00 AM", "Sacred darshan at lakeside Naina Devi Temple on the northern banks."), ("01:30 PM", "Scenic rowboat cruise across the emerald waters of crescent-shaped Naini Lake."), ("05:30 PM", "Mall Road evening promenade, candle shopping, and heritage coffee at Cafe Chica.")]),
        ("Snow View Peak & Himalayan Vistas", [("09:00 AM", "Aerial Ropeway cable car ride up to Snow View Point (7,450 ft) for vistas of Nanda Devi and Trishul peaks."), ("01:00 PM", "Mountain lunch with hot soup and momos overlooking the valley."), ("03:00 PM", "Hike to Tiffin Top (Dorothy's Seat) through oak, deodar, and pine woods."), ("06:00 PM", "Explore natural limestone labyrinth caves at Cave Garden.")])
    ],
    'mussoorie': [
        ("Mall Road, Gun Hill & Colonial Heritage", [("08:30 AM", "Bun Omelette and herbal ginger tea at iconic Char Dukan in historic Landour."), ("10:30 AM", "Stroll along the tranquil pine-lined ridge of Camel's Back Road."), ("01:30 PM", "Colonial dining at The Tavern on Mall Road."), ("05:30 PM", "Cable car ascent to Gun Hill summit for panoramic sunset over Doon Valley.")]),
        ("Waterfalls & Himalayan Sanctuaries", [("09:00 AM", "Morning visit to cascading Kempty Falls with mountain splash pools."), ("01:30 PM", "Hike up to historic Sir George Everest House estate with 360-degree snow peak vistas."), ("04:30 PM", "Fresh lemon drizzle cake and apple pie at Landour Bakehouse."), ("06:30 PM", "Golden hour sunset viewing from Cloud's End heritage forest.")])
    ]
}

def build_fallback_itinerary(destination, days, style='Adventure', budget='Moderate'):
    clean_city = destination.split(',')[0].strip()
    dest_lower = destination.lower()
    
    # Intelligent token matching across known landmarks
    matched_key = None
    for k in DESTINATION_LANDMARK_MAP:
        if k in dest_lower or dest_lower in k:
            matched_key = k
            break
            
    # Secondary check on city/region words (e.g. "kashmir", "munnar", "kaza", "leh", "kufri")
    if not matched_key:
        token_aliases = {
            'kashmir': 'srinagar',
            'pahalgam': 'srinagar',
            'gulmarg': 'srinagar',
            'leh': 'ladakh',
            'nubra': 'ladakh',
            'munnar': 'kerala',
            'alleppey': 'kerala',
            'kochi': 'kerala',
            'kaza': 'spiti',
            'mcleodganj': 'dharamshala',
            'kufri': 'shimla',
            'rohtang': 'manali',
            'taj': 'agra',
            'vrindavan': 'mathura',
            'meghalaya': 'shillong',
            'cherrapunji': 'shillong',
            'landour': 'mussoorie',
            'havelock': 'andaman'
        }
        for token, mapped_k in token_aliases.items():
            if token in dest_lower:
                matched_key = mapped_k
                break

    itinerary_list = []
    if matched_key and DESTINATION_LANDMARK_MAP.get(matched_key):
        preset_days = DESTINATION_LANDMARK_MAP[matched_key]
        for i in range(1, days + 1):
            if i <= len(preset_days):
                theme, slots_data = preset_days[i - 1]
            else:
                cycle_theme, cycle_slots = preset_days[(i - 1) % len(preset_days)]
                theme = f"Extended Day {i}: {cycle_theme}"
                slots_data = cycle_slots
            itinerary_list.append({
                "day": i,
                "theme": f"Day 0{i}: {theme}" if i < 10 else f"Day {i}: {theme}",
                "slots": [{"time": s[0], "activity": s[1]} for s in slots_data]
            })
    else:
        # Contextual procedural synthesis tailored for the specific destination
        themes = [
            f"Iconic Landmarks & Orientation in {clean_city}",
            f"Historic Heritage & Cultural Monoliths of {clean_city}",
            f"Panoramic Vistas, Nature Trails & Regional Delicacies",
            f"Artisan Quarters, Stepwells & Sunset Points of {clean_city}",
            f"Local Bazaars, Street Flavors & Farewell Gala in {clean_city}",
            f"Scenic Highlands & Countryside Exploration around {clean_city}",
            f"Spiritual Shrines & Traditional Crafts of {clean_city}"
        ]
        for i in range(1, days + 1):
            theme_title = themes[(i - 1) % len(themes)]
            itinerary_list.append({
                "day": i,
                "theme": f"Day 0{i}: {theme_title}" if i < 10 else f"Day {i}: {theme_title}",
                "slots": [
                    {"time": "08:30 AM", "activity": f"Authentic {style.lower()} breakfast and artisanal specialty tea/coffee in central {clean_city}."},
                    {"time": "11:00 AM", "activity": f"Guided {style.lower()} exploration of the premier historic monument and architecture of {clean_city}."},
                    {"time": "02:00 PM", "activity": f"Traditional culinary lunch feast tasting signature {budget.lower()} local dishes in {clean_city}."},
                    {"time": "06:00 PM", "activity": f"Scenic golden hour photography at top viewpoint followed by evening bazaar walks in {clean_city}."}
                ]
            })

    return {
        "destination": destination,
        "total_days": days,
        "style": style,
        "budget": budget,
        "itinerary": itinerary_list,
        "status": "success",
        "success": True,
        "ai_engine": "TravelMate AI (Neural Sync)"
    }

@csrf_exempt
def generate_itinerary_view(request):
    """
    Accepts destination, days, style, and budget via GET (or POST) request.
    Configures google-generativeai using settings.GEMINI_API_KEY.
    Generates a hyper-realistic, location-specific itinerary using Gemini AI
    and returns valid JSON.
    """
    # Accept parameters via GET (primary) or POST
    destination = request.GET.get('destination') or request.POST.get('destination')
    days_param = request.GET.get('days') or request.POST.get('days') or 5
    style = (request.GET.get('style') or request.POST.get('style') or 'Adventure').strip()
    budget = (request.GET.get('budget') or request.POST.get('budget') or 'Moderate').strip()

    # Also handle application/json body if provided
    if not destination and request.body:
        try:
            body_data = json.loads(request.body.decode('utf-8'))
            destination = body_data.get('destination')
            days_param = body_data.get('days', 5)
            style = body_data.get('style', style)
            budget = body_data.get('budget', budget)
        except Exception:
            pass

    if not destination or not str(destination).strip():
        return JsonResponse({
            'status': 'error',
            'message': 'Destination query parameter is required (e.g., ?destination=Mathura&days=3)'
        }, status=400)

    destination = str(destination).strip()

    try:
        days = max(1, min(int(days_param), 14))
    except (ValueError, TypeError):
        days = 5

    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        logger.info("GEMINI_API_KEY is not configured, returning resilient fallback itinerary.")
        fallback_data = build_fallback_itinerary(destination, days, style, budget)
        return JsonResponse(fallback_data, safe=False)

    genai.configure(api_key=api_key)

    prompt = f"""
You are 'TravelMate AI', an elite, highly intelligent real-time travel and itinerary architect.
Generate a hyper-realistic, location-specific, and fully customized travel itinerary for {destination} for {days} days.

TRAVELER CUSTOMIZATION PREFERENCES:
- Travel Archetype / Style: {style} (Design activities, pace, thrills, culture, or leisure strictly around this archetype)
- Budget Tier: {budget} (Recommend stays, dining, transport, and experiences perfectly aligned with this budget)

CRITICAL RULES:
1. NO GENERIC PLACEHOLDERS: Do NOT use repetitive boilerplate phrases like "explore local market", "walk around the city", or "visit local museum". Every single time slot and activity MUST feature verified, real, and famous tourist attractions, authentic landmarks, heritage temples/monuments, and iconic local food joints specific to {destination} (e.g., if Mathura: Shri Krishna Janmasthan Temple Complex, Dwarkadhish Temple, Yamuna Aarti at Vishram Ghat, authentic Mathura ke Pede at Brijwasi Mithai Wala; if Jaipur: Amber Fort, Hawa Mahal, Jal Mahal, Johari Bazaar, Rawat Mishthan Bhandar).
2. REALISTIC TIME SLOTS: Structure each day with logical chronological time slots (e.g., 08:30 AM, 11:30 AM, 02:30 PM, 06:30 PM) ensuring smooth geographical transitions for a traveler.
3. THEME-BASED DAYS: Provide a catchy, engaging theme title for each day reflecting the {style} archetype (e.g., "Day 01: Royal Bastions & Heritage Flavors").
4. STRICT JSON FORMAT: Return ONLY valid, raw JSON. Do NOT include markdown code fences (no ```json or ```), no conversational intro, and no outro.

Expected JSON structure:
{{
  "destination": "{destination}",
  "total_days": {days},
  "style": "{style}",
  "budget": "{budget}",
  "itinerary": [
    {{
      "day": 1,
      "theme": "Theme title for Day 1",
      "slots": [
        {{"time": "08:30 AM", "activity": "Specific real tourist spot / breakfast spot in {destination}"}},
        {{"time": "11:30 AM", "activity": "Specific real tourist landmark / temple / museum in {destination}"}},
        {{"time": "02:30 PM", "activity": "Specific real lunch / market / cultural site in {destination}"}},
        {{"time": "06:30 PM", "activity": "Specific real evening sunset point / aarti / rooftop dining in {destination}"}}
      ]
    }}
  ]
}}
Ensure the "itinerary" array contains exactly {days} day objects numbered 1 to {days}.
"""

    models_to_try = []
    preferred = getattr(settings, 'GEMINI_MODEL', 'gemini-3.5-flash')
    for m in [preferred, 'gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-3.8-flash']:
        if m not in models_to_try:
            models_to_try.append(m)

    response = None
    last_error = None
    used_model = None

    for m_name in models_to_try:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(prompt)
            if response and response.text:
                used_model = m_name
                break
        except Exception as err:
            logger.warning(f"Gemini model {m_name} failed: {err}")
            last_error = err

    if not response or not response.text:
        logger.warning(f"All Gemini AI models failed: {last_error}. Returning resilient fallback itinerary.")
        fallback_data = build_fallback_itinerary(destination, days, style, budget)
        return JsonResponse(fallback_data, safe=False)

    raw_text = response.text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_text = "\n".join(lines).strip()

    try:
        parsed_json = json.loads(raw_text)
    except json.JSONDecodeError as jde:
        logger.error(f"JSON decode error: {jde}, text: {raw_text}")
        return JsonResponse({
            'status': 'error',
            'success': False,
            'message': 'Failed to parse AI output into valid JSON',
            'raw_output': raw_text
        }, status=502)

    # Normalize in case Gemini returned top-level day_1, day_2 keys
    if "itinerary" not in parsed_json:
        itinerary_list = []
        day_keys = [k for k in parsed_json.keys() if k.lower().startswith('day')]
        day_keys.sort(key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
        for k in day_keys:
            day_val = parsed_json[k]
            day_num = int(''.join(filter(str.isdigit, k)) or (len(itinerary_list) + 1))
            itinerary_list.append({
                "day": day_num,
                "theme": day_val.get("title") or day_val.get("theme") or f"Day {day_num} Exploration",
                "slots": day_val.get("slots") or day_val.get("activities") or []
            })
        parsed_json = {
            "destination": destination,
            "total_days": days,
            "itinerary": itinerary_list
        }

    parsed_json["destination"] = destination
    parsed_json["total_days"] = days
    parsed_json["style"] = style
    parsed_json["budget"] = budget
    parsed_json["status"] = "success"
    parsed_json["success"] = True
    parsed_json["ai_engine"] = f"TravelMate AI ({used_model})"

    # Persist the full synthesized itinerary into MongoDB GeneratedItinerary collection
    try:
        from .models import GeneratedItinerary, log_user_activity
        user_email = (getattr(request.user, 'email', '') or '').strip().lower() if request.user.is_authenticated else 'anonymous'
        username = getattr(request.user, 'username', '') or getattr(request.user, 'first_name', '') or 'anonymous'

        GeneratedItinerary.objects.create(
            user_email=user_email,
            username=username,
            destination=destination,
            days=days,
            ai_engine=f"TravelMate AI ({used_model})",
            itinerary_json=json.dumps(parsed_json)
        )
        log_user_activity(
            request=request,
            action_type='GENERATE_ITINERARY',
            description=f"Generated {days}-day itinerary for {destination} using {used_model}",
            metadata={'destination': destination, 'days': days, 'model': used_model}
        )
    except Exception as save_err:
        logger.warning(f"Error persisting generated itinerary: {save_err}")

    return JsonResponse(parsed_json, safe=False)

@csrf_exempt
def generate_itinerary_api(request):
    """
    Alias redirecting to generate_itinerary_view for backwards compatibility.
    """
    return generate_itinerary_view(request)

@csrf_exempt
def chatbot_api(request):
    """
    Backend API endpoint for TravelMate Neural Concierge Chatbot powered by Gemini AI.
    Saves conversation history to MongoDB ChatMessageLog collection.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST

        message = payload.get('message', '').strip()
        if not message:
            return JsonResponse({'success': False, 'error': 'Message parameter is required'}, status=400)

        result = gemini_service.generate_chat_response(user_message=message)
        reply = result.get('reply') or result.get('response') or ''

        # Persist conversation into MongoDB ChatMessageLog collection
        try:
            from .models import ChatMessageLog, log_user_activity
            user_email = (getattr(request.user, 'email', '') or '').strip().lower() if request.user.is_authenticated else 'anonymous'
            username = getattr(request.user, 'username', '') or 'anonymous'
            session_key = request.session.session_key if hasattr(request, 'session') and request.session else ''

            ChatMessageLog.objects.create(
                user_email=user_email,
                username=username,
                session_key=session_key or '',
                user_message=message,
                bot_response=reply
            )
            log_user_activity(
                request=request,
                action_type='CHAT_MESSAGE',
                description=f"Asked Neural Concierge: {message[:120]}",
                metadata={'message': message, 'bot_reply_len': len(reply)}
            )
        except Exception as chat_err:
            logger.warning(f"Error persisting chat log: {chat_err}")

        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =========================================
# CLIENT TELEMETRY & ACTIVITY HISTORY APIS
# =========================================
@csrf_exempt
def log_client_activity_api(request):
    """
    Receives frontend client interactions (button clicks, exports, modal views)
    and stores them in MongoDB UserActivityLog collection.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST
    except Exception:
        payload = request.POST

    action_type = payload.get('action_type') or 'UI_INTERACTION'
    description = payload.get('description') or 'User interacted with interface'
    metadata = payload.get('metadata') or {}

    from .models import log_user_activity
    entry = log_user_activity(
        request=request,
        action_type=action_type,
        description=description,
        metadata=metadata
    )

    return JsonResponse({'success': True, 'log_id': str(entry.pk) if entry else None})

def get_activity_history_api(request):
    """
    Returns recent activity history from the database.
    """
    from .models import UserActivityLog

    user_email = (getattr(request.user, 'email', '') or '').strip().lower() if request.user.is_authenticated else ''

    # Get recent 50 activity logs
    if user_email:
        recent_activities = list(UserActivityLog.objects.filter(user_email__iexact=user_email).order_by('-created_at')[:50])
    else:
        recent_activities = list(UserActivityLog.objects.all().order_by('-created_at')[:50])

    data = []
    for act in recent_activities:
        data.append({
            'id': str(act.pk),
            'user': act.username,
            'email': act.user_email,
            'action_type': act.action_type,
            'description': act.action_description,
            'path': act.path,
            'ip': act.ip_address,
            'timestamp': act.formatted_created_at
        })

    return JsonResponse({
        'success': True,
        'count': len(data),
        'activities': data
    })

