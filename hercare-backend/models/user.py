from datetime import datetime


def create_user(first_name, last_name, email, password_hash, phone=""):
    """
    Returns a user document ready to insert into MongoDB.
    """
    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": email.lower().strip(),
        "password": password_hash,
        "phone": phone,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
