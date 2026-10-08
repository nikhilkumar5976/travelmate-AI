import json
import logging
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

# Configure Gemini API
_gemini_configured = False

def configure_gemini():
    global _gemini_configured
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if api_key and not _gemini_configured:
        try:
            genai.configure(api_key=api_key)
            _gemini_configured = True
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}")
    return _gemini_configured

def get_gemini_model(model_name=None):
    configure_gemini()
    chosen_model = model_name or getattr(settings, 'GEMINI_MODEL', 'gemini-3.8-flash')
    return genai.GenerativeModel(chosen_model)

def generate_itinerary(destination: str, days: int = 5, style: str = "Adventure", budget: str = "Moderate") -> dict:
    """
    Generates a rich, day-by-day travel itinerary using Gemini AI.
    Returns structured JSON with days, timings, activities, budget estimates, and insider tips.
    """
    configure_gemini()
    days = max(1, min(int(days), 14))

    prompt = f"""
You are 'TravelMate AI', an elite, highly intelligent real-time travel and itinerary architect. 
Your task is to generate a hyper-realistic, location-specific, and fully customized travel itinerary for {destination} for {days} days.

CRITICAL RULES:
1. NO GENERIC PLACEHOLDERS: Do not use repetitive boilerplate sentences. Every single time slot and activity must feature real, verified, and famous tourist attractions, local landmarks, authentic food spots, or cultural experiences specific to {destination}.
2. REALISTIC TIME SLOTS: Structure each day with logical time slots (e.g., 08:30 AM, 11:00 AM, 02:00 PM, 06:30 PM) ensuring smooth geographical transitions for a traveler.
3. THEME-BASED DAYS: Give a catchy, engaging theme title for each day (e.g., "Day 01: Spiritual Awakening & Heritage Trails").
4. STRICT JSON FORMAT: Return ONLY valid JSON data matching this exact structure, with no extra markdown text outside the JSON:

{{
  "day_1": {{
    "title": "Theme name here",
    "slots": [
      {{"time": "09:00 AM", "activity": "Specific real activity description for {destination}"}},
      {{"time": "11:30 AM", "activity": "Specific real activity description for {destination}"}},
      {{"time": "02:00 PM", "activity": "Specific real activity description for {destination}"}},
      {{"time": "06:30 PM", "activity": "Specific real activity description for {destination}"}}
    ]
  }}
}}
Generate entries up to "day_{days}".
"""

    try:
        model = get_gemini_model()
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Clean markdown codeblocks if model wrapped it
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()
            
        data = json.loads(raw_text)
        return {
            "success": True,
            "data": data,
            "source": "gemini"
        }
    except Exception as e:
        logger.error(f"Gemini Itinerary Generation Error: {e}", exc_info=True)
        # Graceful fallback response so UI never breaks
        return {
            "success": False,
            "error": str(e),
            "source": "fallback"
        }

def generate_chat_response(user_message: str, conversation_history=None) -> dict:
    """
    Answers user inquiries via the TravelMate Neural Concierge powered by Gemini.
    """
    configure_gemini()
    system_instruction = (
        "You are the TravelMate Neural Concierge, an ultra-smart, helpful, and friendly AI travel assistant. "
        "You assist users with travel planning across India and international destinations. "
        "You know about hidden gems, local street food, heritage forts, beaches, mountain treks, "
        "budget planning in Indian Rupees (₹), packing essentials, offline travel, and best seasons to visit. "
        "Keep your responses engaging, concise, easy to read, and formatted with bullet points or emojis where helpful. "
        "Always maintain an enthusiastic, polite, and sophisticated tone."
    )

    try:
        model = get_gemini_model()
        chat_prompt = f"{system_instruction}\n\nUser Question: {user_message}\n\nConcierge Response:"
        response = model.generate_content(chat_prompt)
        reply_text = response.text.strip()
        
        return {
            "success": True,
            "reply": reply_text,
            "source": "gemini"
        }
    except Exception as e:
        logger.error(f"Gemini Chatbot Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "reply": "I'm experiencing a momentary neural synchronization hiccup. Please ask again in a moment or explore destinations in our catalog!",
            "source": "fallback"
        }
