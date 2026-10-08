from datetime import datetime
import json
import logging
import pytz
from djongo import models

logger = logging.getLogger(__name__)

class Destination(models.Model):
    _id = models.ObjectIdField()
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.DecimalField(max_digits=3, decimal_places=2)
    image_url = models.URLField()
    description = models.TextField()

    @property
    def id(self):
        return str(self.pk)

    @property
    def formatted_price(self):
        try:
            if hasattr(self.price, 'to_decimal'):
                val = float(self.price.to_decimal())
            else:
                val = float(self.price)
            if val.is_integer():
                return f"{int(val):,}"
            return f"{val:,.2f}"
        except Exception:
            return str(self.price)

    def __str__(self):
        return self.title

class Review(models.Model):
    _id = models.ObjectIdField()
    destination=models.ForeignKey(Destination,on_delete=models.CASCADE,related_name='reviews')
    username = models.CharField(max_length=100)
    rating = models.IntegerField()
    comment=models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def id(self):
        return str(self.pk)

    def __str__(self):
        return f"{self.username} - {self.destination.title}★"

def get_ist_now():
    """
    Returns current date and time in Indian Standard Time (IST - Asia/Kolkata).
    """
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)

class UserLoginLog(models.Model):
    _id = models.ObjectIdField()
    email = models.EmailField()
    name = models.CharField(max_length=200)
    login_time = models.DateTimeField(default=get_ist_now)

    @property
    def ist_time(self):
        """Returns the login time in Indian Standard Time (IST)."""
        if not self.login_time:
            return None
        if getattr(self.login_time, 'tzinfo', None):
            ist = pytz.timezone('Asia/Kolkata')
            return self.login_time.astimezone(ist)
        return self.login_time

    @property
    def formatted_login_time(self):
        """Returns a human-readable IST formatted timestamp."""
        t = self.ist_time
        if t:
            return t.strftime("%d %b %Y, %I:%M:%S %p IST")
        return ""

    def __str__(self):
        time_display = self.formatted_login_time or str(self.login_time)
        return f"{self.email} ({time_display})"


class UserActivityLog(models.Model):
    _id = models.ObjectIdField()
    user_email = models.CharField(max_length=255, blank=True, default='anonymous')
    username = models.CharField(max_length=150, blank=True, default='anonymous')
    session_key = models.CharField(max_length=100, blank=True, default='')
    action_type = models.CharField(max_length=100)
    action_description = models.CharField(max_length=400, blank=True, default='')
    path = models.CharField(max_length=500, blank=True, default='')
    method = models.CharField(max_length=10, blank=True, default='GET')
    ip_address = models.CharField(max_length=64, blank=True, default='')
    user_agent = models.TextField(blank=True, default='')
    metadata_json = models.TextField(blank=True, default='{}')
    created_at = models.DateTimeField(default=get_ist_now)

    @property
    def id(self):
        return str(self.pk)

    @property
    def formatted_created_at(self):
        if self.created_at:
            return self.created_at.strftime("%d %b %Y, %I:%M:%S %p IST")
        return ""

    def __str__(self):
        return f"[{self.formatted_created_at}] @{self.username} ({self.action_type}): {self.action_description}"


class GeneratedItinerary(models.Model):
    _id = models.ObjectIdField()
    user_email = models.CharField(max_length=255, blank=True, default='anonymous')
    username = models.CharField(max_length=150, blank=True, default='anonymous')
    destination = models.CharField(max_length=200)
    days = models.IntegerField(default=3)
    ai_engine = models.CharField(max_length=100, default='TravelMate AI')
    itinerary_json = models.TextField()
    created_at = models.DateTimeField(default=get_ist_now)

    @property
    def id(self):
        return str(self.pk)

    @property
    def formatted_created_at(self):
        if self.created_at:
            return self.created_at.strftime("%d %b %Y, %I:%M:%S %p IST")
        return ""

    def __str__(self):
        return f"{self.destination} ({self.days} Days) by @{self.username}"


class ChatMessageLog(models.Model):
    _id = models.ObjectIdField()
    user_email = models.CharField(max_length=255, blank=True, default='anonymous')
    username = models.CharField(max_length=150, blank=True, default='anonymous')
    session_key = models.CharField(max_length=100, blank=True, default='')
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(default=get_ist_now)

    @property
    def id(self):
        return str(self.pk)

    @property
    def formatted_created_at(self):
        if self.created_at:
            return self.created_at.strftime("%d %b %Y, %I:%M:%S %p IST")
        return ""

    def __str__(self):
        return f"[@{self.username}] {self.user_message[:40]}"


class SearchQueryLog(models.Model):
    _id = models.ObjectIdField()
    user_email = models.CharField(max_length=255, blank=True, default='anonymous')
    username = models.CharField(max_length=150, blank=True, default='anonymous')
    query = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, default='all')
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=get_ist_now)

    @property
    def id(self):
        return str(self.pk)

    @property
    def formatted_created_at(self):
        if self.created_at:
            return self.created_at.strftime("%d %b %Y, %I:%M:%S %p IST")
        return ""

    def __str__(self):
        return f"'{self.query}' by @{self.username} ({self.results_count} results)"


def log_user_activity(request=None, action_type='GENERAL', description='', metadata=None, user=None, user_email=None, username=None):
    """
    Universally logs any user activity or event into MongoDB UserActivityLog collection.
    Captures user identity, IP address, user agent, URL path, HTTP method, and metadata.
    """
    try:
        ip = ''
        user_agent = ''
        path = ''
        method = 'GET'
        session_key = ''

        if request:
            path = request.path or ''
            method = request.method or 'GET'
            if hasattr(request, 'session') and request.session:
                session_key = request.session.session_key or ''

            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', '')
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            if not user and hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user

        if user and getattr(user, 'is_authenticated', False):
            user_email = user_email or getattr(user, 'email', '') or f"{getattr(user, 'username', 'user')}@travelmate.ai"
            username = username or getattr(user, 'username', '') or getattr(user, 'first_name', '') or user_email.split('@')[0]
        else:
            user_email = user_email or 'anonymous'
            username = username or 'anonymous'

        metadata_str = '{}'
        if metadata:
            try:
                metadata_str = json.dumps(metadata)
            except Exception:
                metadata_str = str(metadata)

        return UserActivityLog.objects.create(
            user_email=user_email,
            username=username,
            session_key=session_key,
            action_type=action_type,
            action_description=str(description)[:400],
            path=str(path)[:500],
            method=str(method)[:10],
            ip_address=str(ip)[:64],
            user_agent=str(user_agent)[:1000],
            metadata_json=metadata_str,
            created_at=get_ist_now()
        )
    except Exception as e:
        logger.warning(f"Error in log_user_activity: {e}")
        return None



