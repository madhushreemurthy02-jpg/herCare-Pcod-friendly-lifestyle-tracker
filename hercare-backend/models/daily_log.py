from datetime import datetime

def create_daily_log(user_id, date, sleep=None, hydration=None, mood=None, nutrition=None, activities=None, notes=None):
    return {
        "user_id": user_id,
        "date": date, # Format: YYYY-MM-DD
        "sleep": sleep or {}, # bedtime, waketime, quality, duration_mins
        "hydration": hydration or {}, # glasses, ml
        "mood": mood or {}, # mood, note, tags
        "nutrition": nutrition or [], # list of checked items
        "activities": activities or [], # list of {name, duration, intensity, notes, cal}
        "notes": notes,
        "created_at": datetime.utcnow()
    }
