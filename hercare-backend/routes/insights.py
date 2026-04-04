from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import google.generativeai as genai
from models.user import db

insights_bp = Blueprint('insights', __name__)

@insights_bp.route('/', methods=['GET'])
@jwt_required()
def get_insights():
    try:
        user_id = get_jwt_identity()

        # Configure API Key (done inside the route to ensure .env is fully loaded if lazy-loaded)
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"success": False, "message": "Gemini API key not configured."}), 500
        
        genai.configure(api_key=api_key)

        # Fetch user's profile
        profile = db.health_profiles.find_one({"user_id": user_id})
        
        # Fetch user's most recent daily logs
        daily_logs = list(db.daily_logs.find({"user_id": user_id}).sort("date", -1).limit(7))
        
        # Fetch user's cycle logs
        cycle_logs = list(db.cycle_logs.find({"user_id": user_id}).sort("start_date", -1).limit(1))
        
        # Format the data for Gemini
        profile_data = ""
        if profile:
            profile_data = f"Age: {profile.get('age')}, Weight: {profile.get('weight')}kg, Height: {profile.get('height')}cm, Avg Cycle Length: {profile.get('cycle_length')} days."
        
        logs_data = ""
        for log in daily_logs:
            mood = log.get('mood', {}).get('mood', 'Not logged')
            sleep_quality = log.get('sleep', {}).get('quality', 'Not logged')
            glasses = log.get('hydration', {}).get('glasses', 0)
            logs_data += f"- Date: {log.get('date')}, Mood: {mood}, Sleep Quality: {sleep_quality}/10, Water: {glasses} glasses.\n"

        cycle_data = ""
        if cycle_logs:
            cl = cycle_logs[0]
            cycle_data = f"Last Period Start: {cl.get('start_date')}, Flow: {cl.get('flow', {}).get('intensity', 'Not logged')}, Pain Level: {cl.get('pain', 'Not logged')}/10"

        prompt = f"""
        You are an empathetic, knowledgeable wellness assistant specializing in PCOS/PCOD context.
        The user has provided the following health profile: {profile_data}
        
        Here are their recent daily logs:
        {logs_data}
        
        And their latest cycle information:
        {cycle_data}
        
        Based on this data, provide 3 short, personalized, actionable insights or tips for their daily routine to manage their PCOD lifestyle. 
        Format your response nicely in clear HTML (using only <b>, <i>, <br>, <ul>, <li> tags as appropriate, do NOT use markdown or generic text). Make it supportive and uplifting.
        """

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        return jsonify({"success": True, "insights": response.text}), 200

    except Exception as e:
        print(f"Insight Generation Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@insights_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat_with_ai():
    try:
        user_id = get_jwt_identity()
        data = db.users.find_one({"_id": user_id})
        user_name = data.get('first_name', 'User') if data else 'User'
        
        user_msg = request.json.get('message')
        if not user_msg:
            return jsonify({"success": False, "message": "No message provided"}), 400

        # Configure Gemini
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)

        # Context (Profile + Logs)
        profile = db.health_profiles.find_one({"user_id": user_id})
        daily_logs = list(db.daily_logs.find({"user_id": user_id}).sort("date", -1).limit(3))
        
        context = f"User Name: {user_name}. "
        if profile:
            context += f"Profile: Age {profile.get('age')}, Cycle {profile.get('cycle_length')} days. "
        
        prompt = f"""
        You are 'herCare AI', a supportive, expert wellness coach for women with PCOD/PCOS. 
        Your tone is gentle, uplifting, and medically informed but conversational.
        User Context: {context}
        User's question: {user_msg}
        
        Keep your response concise (max 2-3 short paragraphs). Use only standard HTML tags if needed (<b>, <i>, <br>). 
        Always be encouraging. If asked medical questions, provide wellness advice but remind the user to consult their doctor.
        """

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        return jsonify({"success": True, "response": response.text}), 200

    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
