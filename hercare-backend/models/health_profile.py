from datetime import datetime

def create_health_profile(user_id, age, height, weight, cycle_length, last_period=None):
    return {
        "user_id": user_id,
        "age": age,
        "height": height,
        "weight": weight,
        "cycle_length": cycle_length,
        "last_period": last_period,
        "updated_at": datetime.utcnow()
    }
