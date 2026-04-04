from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from middleware.auth_middleware import token_required
from models.health_profile import create_health_profile

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")

# --- GET /api/profile (Retrieve your profile) ---
@profile_bp.route("", methods=["GET"])
@token_required
def get_profile():
    from app import mongo
    user_id = get_jwt_identity()
    profile = mongo.profiles.find_one({"user_id": user_id}, {"_id": 0})
    
    if not profile:
        return jsonify({"success": False, "message": "Profile not found"}), 404
        
    return jsonify({"success": True, "data": profile}), 200

# --- PUT /api/profile (Save or Update your profile) ---
@profile_bp.route("", methods=["PUT"])
@token_required
def save_profile():
    from app import mongo
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Extract data from frontend fields
    age = data.get("age")
    height = data.get("height")
    weight = data.get("weight")
    cycle_length = data.get("cycle_length")
    last_period = data.get("last_period")
    
    if not all([age, height, weight, cycle_length]):
        return jsonify({"success": False, "message": "Please fill in all basic fields 🌸"}), 400
        
    profile_data = create_health_profile(user_id, age, height, weight, cycle_length, last_period)
    
    # Update if exists, else insert (upsert=True)
    mongo.profiles.update_one(
        {"user_id": user_id}, 
        {"$set": profile_data}, 
        upsert=True
    )
    
    return jsonify({"success": True, "message": "Profile saved successfully! 🌸"}), 200
