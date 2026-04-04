from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from middleware.auth_middleware import token_required
from models.daily_log import create_daily_log

daily_log_bp = Blueprint("daily_log", __name__, url_prefix="/api/daily-log")

# --- POST /api/daily-log (Log your daily wellness) ---
@daily_log_bp.route("", methods=["POST"])
@token_required
def save_daily_log():
    from app import mongo
    user_id = get_jwt_identity()
    data = request.get_json()
    
    date_str = data.get("date")
    if not date_str:
        return jsonify({"success": False, "message": "Date is required"}), 400
        
    sleep = data.get("sleep")
    hydration = data.get("hydration")
    mood = data.get("mood")
    nutrition = data.get("nutrition")
    activities = data.get("activities")
    notes = data.get("notes")
    
    log_doc = create_daily_log(
        user_id, date_str, 
        sleep=sleep, 
        hydration=hydration, 
        mood=mood, 
        nutrition=nutrition, 
        activities=activities, 
        notes=notes
    )
    
    # Update if exists for this date, else insert
    mongo.daily_logs.update_one(
        {"user_id": user_id, "date": date_str}, 
        {"$set": log_doc}, 
        upsert=True
    )
    
    return jsonify({"success": True, "message": "🌸 Daily log saved successfully!"}), 200

# --- GET /api/daily-log (Retrieve daily log for a date) ---
@daily_log_bp.route("", methods=["GET"])
@token_required
def get_daily_log():
    from app import mongo
    user_id = get_jwt_identity()
    date_str = request.args.get("date")
    
    if not date_str:
        return jsonify({"success": False, "message": "Date parameter is required"}), 400
        
    log = mongo.daily_logs.find_one({"user_id": user_id, "date": date_str}, {"_id": 0})
    
    if not log:
        return jsonify({"success": False, "message": "No log found for this date"}), 404
        
    return jsonify({"success": True, "data": log}), 200
