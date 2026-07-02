import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, verify_jwt_in_request, jwt_required
from dotenv import load_dotenv
import urllib.request
import urllib.error
import json

# ─────────────────────────────────────────────────────────────────────────────
# 1. SETUP & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///hercare.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "hercare-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours in seconds

app = Flask(__name__)
app.config.from_object(Config)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# ─────────────────────────────────────────────────────────────────────────────
# 2. DATABASE MODELS
# ─────────────────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    health_profile = db.relationship('HealthProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    daily_logs = db.relationship('DailyLog', backref='user', lazy=True, cascade="all, delete-orphan")
    cycle_logs = db.relationship('CycleLog', backref='user', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "created_at": self.created_at.isoformat()
        }

class HealthProfile(db.Model):
    __tablename__ = 'health_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    age = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    cycle_length = db.Column(db.Integer, nullable=False)
    last_period = db.Column(db.String(20), nullable=True) # YYYY-MM-DD
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "cycle_length": self.cycle_length,
            "last_period": self.last_period,
            "updated_at": self.updated_at.isoformat()
        }

class DailyLog(db.Model):
    __tablename__ = 'daily_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False) # Format: YYYY-MM-DD
    sleep = db.Column(db.JSON, default={})
    hydration = db.Column(db.JSON, default={})
    mood = db.Column(db.JSON, default={})
    nutrition = db.Column(db.JSON, default=[])
    activities = db.Column(db.JSON, default=[])
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "sleep": self.sleep,
            "hydration": self.hydration,
            "mood": self.mood,
            "nutrition": self.nutrition,
            "activities": self.activities,
            "notes": self.notes,
            "created_at": self.created_at.isoformat()
        }

class CycleLog(db.Model):
    __tablename__ = 'cycle_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.String(20), nullable=False) # YYYY-MM-DD
    end_date = db.Column(db.String(20), nullable=True)    # YYYY-MM-DD
    status = db.Column(db.String(50), nullable=True)      # 'On Period', 'Ended', 'Late'
    symptoms = db.Column(db.JSON, default={})             # {symptom_name: severity_level}
    flow = db.Column(db.JSON, default={})                # intensity, flow_days
    pain = db.Column(db.Integer, nullable=True)           # 1-10
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "symptoms": self.symptoms,
            "flow": self.flow,
            "pain": self.pain,
            "created_at": self.created_at.isoformat()
        }

# ─────────────────────────────────────────────────────────────────────────────
# 3. MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"success": False, "message": "Invalid or missing token."}), 401
    return decorated

# ─────────────────────────────────────────────────────────────────────────────
# 4. ROUTES (Auth, Profile, Daily Log, Cycle, Insights)
# ─────────────────────────────────────────────────────────────────────────────

# --- AUTH ROUTES ---
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    phone = (data.get("phone") or "").strip()

    if not first_name or not last_name or not email or not password:
        return jsonify({"success": False, "message": "Please fill in all required fields 🌸"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "An account with this email already exists"}), 409

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    new_user = User(first_name=first_name, last_name=last_name, email=email, password=password_hash, phone=phone)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        token = create_access_token(identity=str(new_user.id))
        return jsonify({"success": True, "token": token, "user": {"id": new_user.id, "first_name": first_name}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"success": True, "token": token, "user": {"id": user.id, "first_name": user.first_name}}), 200

# --- PROFILE ROUTES ---
@app.route("/api/profile", methods=["GET", "PUT"])
@token_required
def profile_api():
    user_id = get_jwt_identity()
    if request.method == "GET":
        profile = HealthProfile.query.filter_by(user_id=user_id).first()
        if not profile: return jsonify({"success": False, "message": "Profile not found"}), 404
        return jsonify({"success": True, "data": profile.to_dict()}), 200
    
    data = request.get_json()
    age = data.get("age")
    height = data.get("height")
    weight = data.get("weight")
    cycle_length = data.get("cycle_length")
    last_period = data.get("last_period")

    profile = HealthProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = HealthProfile(
            user_id=user_id, age=age, height=height, 
            weight=weight, cycle_length=cycle_length, last_period=last_period
        )
        db.session.add(profile)
    else:
        profile.age = age
        profile.height = height
        profile.weight = weight
        profile.cycle_length = cycle_length
        profile.last_period = last_period
    
    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated!"}), 200

# --- DAILY LOG ROUTES ---
@app.route("/api/daily-log", methods=["GET", "POST"])
@token_required
def daily_log_api():
    user_id = get_jwt_identity()
    if request.method == "GET":
        date_str = request.args.get("date")
        log = DailyLog.query.filter_by(user_id=user_id, date=date_str).first()
        if not log: return jsonify({"success": False}), 404
        return jsonify({"success": True, "data": log.to_dict()}), 200
    
    data = request.get_json()
    date_str = data.get("date")
    log = DailyLog.query.filter_by(user_id=user_id, date=date_str).first()
    
    fields = ["sleep", "hydration", "mood", "nutrition", "activities", "notes"]
    log_data = {f: data.get(f) for f in fields if f in data}

    if not log:
        log = DailyLog(user_id=user_id, date=date_str, **log_data)
        db.session.add(log)
    else:
        for key, val in log_data.items(): setattr(log, key, val)
    
    db.session.commit()
    return jsonify({"success": True, "message": "Daily log saved!"}), 200

# --- CYCLE ROUTES ---
@app.route("/api/cycle", methods=["POST"])
@token_required
def cycle_api():
    user_id = get_jwt_identity()
    data = request.get_json()
    start_date = data.get("start_date")
    log_id = data.get("id")
    
    fields = ["start_date", "end_date", "status", "symptoms", "flow", "pain"]
    cycle_data = {f: data.get(f) for f in fields if f in data}

    if log_id:
        log = CycleLog.query.filter_by(id=log_id, user_id=user_id).first()
    else:
        log = CycleLog.query.filter_by(user_id=user_id, start_date=start_date).first()

    if not log:
        log = CycleLog(user_id=user_id, **cycle_data)
        db.session.add(log)
    else:
        for key, val in cycle_data.items(): setattr(log, key, val)

    db.session.commit()
    return jsonify({"success": True, "message": "Cycle data logged!"}), 200

@app.route("/api/cycle/history", methods=["GET"])
@token_required
def cycle_history():
    user_id = get_jwt_identity()
    history = CycleLog.query.filter_by(user_id=user_id).order_by(CycleLog.start_date.desc()).all()
    return jsonify({"success": True, "data": [h.to_dict() for h in history]}), 200

@app.route("/api/cycle/<int:log_id>", methods=["DELETE"])
@token_required
def delete_cycle(log_id):
    user_id = get_jwt_identity()
    log = CycleLog.query.filter_by(id=log_id, user_id=user_id).first()
    if not log:
        return jsonify({"success": False, "message": "Log not found."}), 404
    db.session.delete(log)
    db.session.commit()
    return jsonify({"success": True, "message": "Cycle log deleted successfully."}), 200

def get_gemini_insights(profile_dict, daily_logs_list, cycle_log_dict):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment. Falling back to local insights.")
        return None

    data_summary = {
        "health_profile": profile_dict,
        "recent_daily_logs_7_days": daily_logs_list,
        "latest_cycle_log": cycle_log_dict
    }

    prompt = f"""
You are an empathetic health AI assistant specializing in PCOD/PCOS (Polycystic Ovary Syndrome) and menstrual health.
Below is the user's PCOD-friendly lifestyle tracker data, including their health profile, recent daily logs (past 7 days), and latest cycle log details.

Data:
{json.dumps(data_summary, indent=2)}

Task:
Analyze this data carefully. Synthesize their habits (sleep, hydration, nutrition, activities, mood) and cycle phase/symptoms to create 4-5 personalized, highly actionable, and empathetic health insights. Focus on how these habits specifically affect their PCOD management (e.g. insulin resistance, inflammation, cortisol levels, hormonal balance).

Respond strictly in the following JSON format:
{{
  "insights": [
    {{
      "type": "positive" | "tip" | "warning" | "reminder",
      "icon": "emoji string",
      "title": "Short title",
      "text": "Empathetic, clear, and actionable feedback or advice."
    }}
  ]
}}
Do not include any markdown backticks or explanations outside the JSON structure.
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            text_response = res_data['candidates'][0]['content']['parts'][0]['text']
            parsed = json.loads(text_response.strip())
            if isinstance(parsed, dict) and "insights" in parsed and isinstance(parsed["insights"], list):
                return parsed["insights"]
            elif isinstance(parsed, list):
                return parsed
    except Exception as e:
        print(f"Gemini API call failed: {e}. Falling back.")
        return None


def generate_local_insights(profile, daily_logs, cycle_log):
    insights = []
    log = daily_logs[0] if daily_logs else None
    
    # ── SLEEP ──
    if log and isinstance(log.sleep, dict):
        sleep = log.sleep
        bedtime = sleep.get('bedtime')
        waketime = sleep.get('waketime')
        if bedtime and waketime:
            try:
                bh, bm = map(int, bedtime.split(':'))
                wh, wm = map(int, waketime.split(':'))
                mins = (wh * 60 + wm) - (bh * 60 + bm)
                if mins < 0:
                    mins += 1440
                label = f"{mins // 60}h {mins % 60}m"
                if mins < 360:
                    insights.append({
                        "type": "warning",
                        "icon": "😴",
                        "title": "Low Sleep Detected",
                        "text": f"You slept {label}. For PCOD management, 7–9 hours helps regulate cortisol and insulin levels. Try setting a consistent bedtime — even 30 minutes earlier makes a difference."
                    })
                elif mins < 420:
                    insights.append({
                        "type": "tip",
                        "icon": "🌙",
                        "title": "Sleep Could Be Better",
                        "text": f"You got {label} — not bad, but aiming for 7+ hours can noticeably improve your energy, mood, and hormone balance throughout the day."
                    })
                else:
                    insights.append({
                        "type": "positive",
                        "icon": "✨",
                        "title": "Great Sleep!",
                        "text": f"You slept {label} — excellent! Good sleep supports healthy cortisol rhythm, which is especially important for managing PCOD symptoms."
                    })
            except Exception:
                pass
            
            q = sleep.get('quality', '')
            if 'Restless' in q:
                insights.append({
                    "type": "tip",
                    "icon": "🌿",
                    "title": "Restless Sleep",
                    "text": "Restless sleep raises cortisol and worsens hormonal imbalance. Try limiting screens 30 minutes before bed, and consider light stretching or chamomile tea."
                })
            elif 'Refreshed' in q or 'Deep' in q:
                insights.append({
                    "type": "positive",
                    "icon": "💫",
                    "title": "Quality Sleep",
                    "text": "Waking up refreshed is a great sign! Quality sleep helps your body regulate estrogen and progesterone levels more effectively — keep this up."
                })

    # ── HYDRATION ──
    if log and isinstance(log.hydration, dict):
        hydration = log.hydration
        ml = hydration.get('ml') or (hydration.get('glasses', 0) * 250)
        if ml >= 2000:
            insights.append({
                "type": "positive",
                "icon": "💧",
                "title": "Well Hydrated!",
                "text": f"You hit {ml}ml today — fantastic! Staying hydrated reduces bloating, supports kidney function, and eases PCOD-related water retention."
            })
        elif ml >= 1200:
            insights.append({
                "type": "tip",
                "icon": "🥛",
                "title": "Drink a Little More Water",
                "text": f"You had about {ml}ml today. Try to reach 2000ml — carry a water bottle and sip regularly. Proper hydration supports hormonal detoxification throughout the day."
            })
        elif ml > 0:
            insights.append({
                "type": "warning",
                "icon": "⚠️",
                "title": "Low Hydration Today",
                "text": f"Only {ml}ml logged today — below the recommended 2000ml. Dehydration can worsen PCOD symptoms like fatigue, bloating, and mood swings."
            })

    # ── MOOD ──
    if log and isinstance(log.mood, dict):
        mood_data = log.mood
        mood = mood_data.get('mood')
        if mood in ['Great', 'Good']:
            insights.append({
                "type": "positive",
                "icon": "🌸",
                "title": f"Positive Mood — {mood}!",
                "text": "A good mood is a real health indicator. Whatever you did today is clearly working for your body and mind — take note of it and try to repeat it."
            })
        elif mood == 'Okay':
            insights.append({
                "type": "tip",
                "icon": "🌷",
                "title": "Neutral Mood Today",
                "text": "Feeling 'okay' is perfectly valid. A short 10-minute walk, some journaling, or a warm drink can gently shift your mood and support hormone balance."
            })
        elif mood in ['Bad', 'Awful']:
            insights.append({
                "type": "reminder",
                "icon": "💗",
                "title": "Low Mood Noticed",
                "text": "PCOD can affect mental health through hormonal fluctuations — you are not alone in feeling this. Be gentle with yourself today."
            })
        tags = mood_data.get('tags', [])
        if any(t in ['Anxious', 'Stressed', 'Overwhelmed', 'Irritable'] for t in tags):
            insights.append({
                "type": "tip",
                "icon": "🧘",
                "title": "Stress Management",
                "text": "High stress raises cortisol, which can disrupt your cycle and worsen PCOD symptoms. Even 5 minutes of deep breathing or a short walk creates a meaningful shift."
            })

    # ── NUTRITION ──
    if log and hasattr(log, 'nutrition') and log.nutrition is not None:
        n = log.nutrition if isinstance(log.nutrition, list) else []
        if len(n) == 0:
            insights.append({
                "type": "warning",
                "icon": "🥗",
                "title": "No Nutrition Logged",
                "text": "You didn't log any nutrition today. Diet plays a major role in PCOD management — try to include leafy greens, a protein source, and whole grains in your meals tomorrow."
            })
        elif len(n) >= 4:
            insights.append({
                "type": "positive",
                "icon": "🥗",
                "title": "Excellent Nutrition!",
                "text": f"You checked off {len(n)} nutrition goals today — that's fantastic! A PCOD-friendly diet helps regulate insulin and reduce chronic inflammation."
            })
        else:
            insights.append({
                "type": "tip",
                "icon": "🌾",
                "title": "Good Start on Nutrition",
                "text": f"You logged {len(n)} nutrition goals today. Aim to add more variety — leafy greens, protein, and whole grains provide the best hormonal support for PCOD."
            })
        if 'Low Sugar' in n:
            insights.append({
                "type": "positive",
                "icon": "🚫🍬",
                "title": "Low Sugar — Great for PCOD!",
                "text": "Avoiding processed sugar is one of the most impactful things you can do. It reduces insulin spikes and helps regulate androgen levels. This is a great habit to maintain!"
            })
        if 'Protein Source' not in n and len(n) > 0:
            insights.append({
                "type": "tip",
                "icon": "🥚",
                "title": "Add More Protein",
                "text": "Protein stabilises blood sugar and keeps you fuller longer — both critical for PCOD. Try adding eggs, lentils, tofu, or chicken to your next meal."
            })

    # ── ACTIVITY ──
    if log and hasattr(log, 'activities') and log.activities is not None:
        acts = log.activities if isinstance(log.activities, list) else []
        total_mins = sum([int(a.get('duration', 0)) for a in acts if isinstance(a, dict)])
        if len(acts) == 0:
            insights.append({
                "type": "tip",
                "icon": "🚶",
                "title": "No Activity Today",
                "text": "Even a 20-minute walk significantly improves insulin sensitivity in PCOD. Try building gentle movement into your day — it doesn't need to be intense to be effective."
            })
        elif total_mins >= 30:
            insights.append({
                "type": "positive",
                "icon": "💪",
                "title": f"Active Day — {total_mins} Minutes!",
                "text": "Great job staying active! Regular exercise is one of the most effective tools for PCOD — it improves insulin resistance, supports a regular cycle, and boosts mood."
            })
        else:
            insights.append({
                "type": "tip",
                "icon": "🏃",
                "title": "Keep Building Activity",
                "text": f"You moved for {total_mins} minutes today — a good start. Try to gradually reach 30+ minutes. Light activity like stretching, yoga, or a brisk walk all count."
            })

    # ── CYCLE PHASE & PERIOD INSIGHTS ──
    cycle_start = None
    if cycle_log and cycle_log.start_date:
        cycle_start = cycle_log.start_date
    elif profile and profile.last_period:
        cycle_start = profile.last_period

    if cycle_start and cycle_start not in ["", "null", "None"]:
        try:
            start_date_obj = datetime.strptime(cycle_start, "%Y-%m-%d")
            today = datetime.now()
            diff_days = (today - start_date_obj).days + 1
            cycle_len = int(profile.cycle_length) if profile and profile.cycle_length else 28
            
            if 1 <= diff_days <= 5:
                insights.append({
                    "type": "tip",
                    "icon": "🩸",
                    "title": "Menstrual Phase",
                    "text": f"You are in your Menstrual phase (Day {diff_days}). It's normal to feel lower energy. Focus on iron-rich foods, stay warm, and prioritise gentle stretches or rest."
                })
            elif 5 < diff_days <= 13:
                insights.append({
                    "type": "positive",
                    "icon": "🌱",
                    "title": "Follicular Phase",
                    "text": f"You are in your Follicular phase (Day {diff_days}). Your energy should be rising! This is a great time to incorporate more active workouts and fresh, nutrient-dense foods."
                })
            elif diff_days == 14:
                insights.append({
                    "type": "tip",
                    "icon": "🌕",
                    "title": "Ovulation Phase",
                    "text": f"You are around your Ovulation phase (Day {diff_days}). You might feel more social and energetic. With PCOD, ovulation can sometimes be delayed, so keep tracking."
                })
            elif 14 < diff_days <= cycle_len:
                insights.append({
                    "type": "warning",
                    "icon": "🍂",
                    "title": "Luteal Phase",
                    "text": f"You are in your Luteal phase (Day {diff_days}). You might experience cravings or mood changes. Focus on complex carbs, magnesium-rich foods, and stress management."
                })
            elif diff_days > cycle_len:
                insights.append({
                    "type": "reminder",
                    "icon": "📅",
                    "title": "Late Period",
                    "text": f"Your period is currently late by {diff_days - cycle_len} days. Irregular cycles are common with PCOD, but managing stress and maintaining a balanced diet helps."
                })
        except Exception:
            pass

    if cycle_log:
        pain = cycle_log.pain or 0
        flow = cycle_log.flow.get('intensity', '') if isinstance(cycle_log.flow, dict) else ''
        if pain >= 7:
            insights.append({
                "type": "reminder",
                "icon": "💗",
                "title": "High Period Pain",
                "text": f"You reported pain level {pain}/10. Severe pain with PCOD can indicate elevated prostaglandins. Please discuss this with your doctor — relief is possible."
            })
        elif pain >= 4:
            insights.append({
                "type": "warning",
                "icon": "🌡️",
                "title": "Moderate Period Pain",
                "text": f"Pain level {pain}/10 noted. A warm compress, anti-inflammatory foods like turmeric/ginger, and gentle stretching can help."
            })
        elif pain > 0:
            insights.append({
                "type": "tip",
                "icon": "🌸",
                "title": "Mild Discomfort",
                "text": f"Low pain level {pain}/10 — manageable! Staying hydrated and keeping active on low-pain days helps maintain cycle regularity."
            })
        if 'heavy' in flow.lower():
            insights.append({
                "type": "reminder",
                "icon": "🩸",
                "title": "Heavy Flow Noted",
                "text": "Heavy periods can cause iron deficiency. Eat iron-rich foods like leafy greens and lentils, and speak to your doctor if this persists."
            })
        active_symptoms = [k for k, v in (cycle_log.symptoms or {}).items() if isinstance(v, dict) and v.get('active')]
        if len(active_symptoms) >= 3:
            insights.append({
                "type": "tip",
                "icon": "🌿",
                "title": "Multiple Symptoms Active",
                "text": f"You logged {len(active_symptoms)} active symptoms today. Tracking these reveals PCOD triggers. Consider sharing this log with your gynaecologist."
            })

    # ── PROFILE / BMI ──
    if profile and profile.weight and profile.height:
        try:
            hM = float(profile.height) / 100
            bmi = float(profile.weight) / (hM * hM)
            if bmi > 27:
                insights.append({
                    "type": "tip",
                    "icon": "💛",
                    "title": "Weight & PCOD",
                    "text": f"Even a 5–10% reduction in weight significantly improves PCOD symptoms, restores cycle regularity, and improves insulin sensitivity."
                })
            elif 18.5 <= bmi <= 24.9:
                insights.append({
                    "type": "positive",
                    "icon": "⚖️",
                    "title": "Healthy Weight Range",
                    "text": f"Your BMI ({bmi:.1f}) is in the healthy range. Maintaining this via balanced nutrition and activity is excellent for PCOD management."
                })
        except Exception:
            pass

    return insights


# --- INSIGHTS ROUTES ---
@app.route("/api/insights/", methods=["GET"])
@token_required
def get_insights():
    user_id = get_jwt_identity()
    profile = HealthProfile.query.filter_by(user_id=user_id).first()
    daily_logs = DailyLog.query.filter_by(user_id=user_id).order_by(DailyLog.date.desc()).limit(7).all()
    cycle_log = CycleLog.query.filter_by(user_id=user_id).order_by(CycleLog.start_date.desc()).first()

    # Prepare dictionary payloads
    profile_dict = profile.to_dict() if profile else {}
    daily_logs_list = [log.to_dict() for log in daily_logs]
    cycle_log_dict = cycle_log.to_dict() if cycle_log else {}

    # Try to fetch from Gemini
    gemini_insights = get_gemini_insights(profile_dict, daily_logs_list, cycle_log_dict)
    
    if gemini_insights is not None:
        return jsonify({
            "success": True,
            "insights": gemini_insights,
            "ai_powered": True
        }), 200
    
    # Fallback to local rule-based insights
    local_insights = generate_local_insights(profile, daily_logs, cycle_log)
    return jsonify({
        "success": True,
        "insights": local_insights,
        "ai_powered": False
    }), 200

# ─────────────────────────────────────────────────────────────────────────────
# 5. INITIALIZATION & RUN
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def health_check():
    return {"status": "ok", "message": "herCare All-in-One API ready! 🌸"}

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
