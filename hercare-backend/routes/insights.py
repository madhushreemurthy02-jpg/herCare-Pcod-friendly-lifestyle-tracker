from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import os

insights_bp = Blueprint('insights', __name__)

@insights_bp.route('/', methods=['GET'])
@jwt_required()
def get_insights():
    try:
        user_id = get_jwt_identity()
        from app import mongo

        # Fetch user's profile
        profile = mongo.profiles.find_one({"user_id": user_id})
        
        # Fetch user's most recent daily logs
        daily_logs = list(mongo.daily_logs.find({"user_id": user_id}).sort("date", -1).limit(7))
        
        # Fetch user's cycle logs
        cycle_logs = list(mongo.cycle_logs.find({"user_id": user_id}).sort("start_date", -1).limit(1))

        # --- RULE-BASED INSIGHTS LOGIC ---
        insights = []

        # 1. Sleep Rule
        avg_sleep = 0
        if daily_logs:
            sleep_vals = [log.get('sleep', {}).get('quality', 0) for log in daily_logs if isinstance(log.get('sleep', {}).get('quality'), (int, float))]
            if sleep_vals:
                avg_sleep = sum(sleep_vals) / len(sleep_vals)
        
        if avg_sleep < 6:
            insights.append("<b>Improve Sleep Hygiene:</b> Your recent sleep quality has been lower than ideal. Try creating a fixed bedtime routine with no screens 30 minutes before bed to help regulate your hormones.")
        else:
            insights.append("<b>Steady Rest:</b> Your sleep quality looks consistent! Keep prioritizing rest, as it's vital for managing PCOD-related fatigue.")

        # 2. Hydration Rule
        avg_water = 0
        if daily_logs:
            water_vals = [log.get('hydration', {}).get('glasses', 0) for log in daily_logs if isinstance(log.get('hydration', {}).get('glasses', 0), (int, float))]
            if water_vals:
                avg_water = sum(water_vals) / len(water_vals)
        
        if avg_water < 6:
            insights.append("<b>Hydration Boost:</b> Staying hydrated helps reduce bloating and skin issues. Aim for at least 8-10 glasses of water daily.")
        else:
            insights.append("<b>Great Hydration:</b> You're doing a fantastic job with your water intake! This helps flush out toxins and keeps your energy levels stable.")

        # 3. Cycle & Pain Rule
        if cycle_logs:
            last_pain = cycle_logs[0].get('pain', 0)
            if last_pain > 6:
                insights.append("<b>Managing Discomfort:</b> Your last period pain was reported as high. Consider gentle anti-inflammatory foods like ginger or turmeric tea during your next cycle.")
            else:
                insights.append("<b>Monitor Cycle Phase:</b> Keep tracking your symptoms. Regular movement like walking or light yoga can help maintain cycle regularity.")
        else:
            insights.append("<b>Start Cycle Tracking:</b> Logging your period dates and symptoms will help us provide more specific hormone-balancing tips.")

        # Format as HTML list
        html_response = "<ul>"
        for item in insights:
            html_response += f"<li>{item}</li><br>"
        html_response += "</ul>"

        return jsonify({"success": True, "insights": html_response}), 200

    except Exception as e:
        print(f"Insight Generation Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

