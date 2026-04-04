from datetime import datetime

def create_cycle_log(user_id, start_date, end_date=None, status=None, symptoms=None, flow=None, pain=None):
    return {
        "user_id": user_id,
        "start_date": start_date, # YYYY-MM-DD
        "end_date": end_date,     # YYYY-MM-DD
        "status": status,         # 'On Period', 'Ended', 'Late'
        "symptoms": symptoms or {}, # {symptom_name: severity_level}
        "flow": flow or {},         # intensity, flow_days
        "pain": pain,               # 1-10
        "created_at": datetime.utcnow()
    }
