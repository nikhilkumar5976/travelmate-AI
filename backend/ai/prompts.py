def build_itinerary_prompt(trip, travelers, currency):
    interests = ', '.join(str(i) for i in (trip.interests or [])) or 'general exploration'
    return f"""You are the itinerary planner for TravelMate AI, a travel planning app.

Create a realistic day-by-day itinerary from the trip details below.

Trip details:
- Destination: {trip.destination}
- Number of days: {trip.num_days}
- Total budget for the whole group: {trip.budget} {currency}
- Number of travelers: {travelers}
- Interests: {interests}

Rules:
1. Plan exactly {trip.num_days} days, with 3 to 5 stops per day in a sensible geographic order.
2. Match the stops to the interests and spread them across the days.
3. For every stop, give an estimated cost per person in {currency}. Use 0 for free stops. These are estimates, never exact prices.
4. The total cost for the whole group (cost per person times {travelers}) should stay within the total budget. If the budget is too low for this destination and number of days, still build the best plan you can and write a short, honest explanation in "budget_warning".
5. Only suggest places and activities you are confident really exist at this destination. Do not invent names. If unsure, suggest a general activity instead.
6. Include accommodation, local transport, and food costs in the estimates.

Respond with valid JSON only, with no extra text, in exactly this shape:
{{
  "summary": "one or two sentences about the trip",
  "days": [
    {{
      "day_number": 1,
      "title": "",
      "stops": [
        {{
          "name": "",
          "description": "",
          "time_of_day": "morning, afternoon or evening",
          "category": "food, sightseeing, stay, transport or activity",
          "estimated_cost_per_person": 0
        }}
      ]
    }}
  ],
  "budget_warning": ""
}}"""