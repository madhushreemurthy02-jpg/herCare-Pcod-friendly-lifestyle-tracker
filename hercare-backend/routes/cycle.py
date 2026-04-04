from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from middleware.auth_middleware import token_required
from models.cycle_log import create_cycle_log

cycle_bp = Blueprint("cycle", __name__, url_prefix="/api/cycle")

# --- POST /api/cycle (Log your cycle stats) ---
@cycle_bp.route("", methods=["POST"])
@token_required
def save_cycle_log():
    from app import mongo
    user_id = get_jwt_identity()
    data = request.get_json()
    
    start_date = data.get("start_date")
    if not start_date:
        return jsonify({"success": False, "message": "Start date is required 🩸"}), 400
        
    end_date = data.get("end_date")
    status = data.get("status")
    symptoms = data.get("symptoms")
    flow = data.get("flow")
    pain = data.get("pain")
    
    log_doc = create_cycle_log(
        user_id, start_date, 
        end_date=end_date, status=status, 
        symptoms=symptoms, flow=flow, pain=pain
    )
    
    # We log cycle data by start_date to maintain a historical record
    mongo.cycle_logs.update_one(
        {"user_id": user_id, "start_date": start_date}, 
        {"$set": log_doc}, 
        upsert=True
    )
    
    return jsonify({"success": True, "message": "Cycle data logged successfully! 🌷"}), 200

# --- GET /api/cycle/history (Retrieve all your cycle data) ---
@cycle_bp.route("/history", methods=["GET"])
@token_required
def get_cycle_history():
    from app import mongo
    user_id = get_jwt_identity()
    
    # Get all logs, sorted by start_date descending
    history = list(mongo.cycle_logs.find({"user_id": user_id}, {"_id": 0}).sort("start_date", -1))
    
    return jsonify({"success": True, "data": history}), 200
