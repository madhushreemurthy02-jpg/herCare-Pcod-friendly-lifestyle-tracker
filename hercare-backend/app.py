from datetime import timedelta
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from config import Config

# ──────────────────────────────────────────────
#  Create Flask App
# ──────────────────────────────────────────────
app = Flask(__name__)

# Load config
app.config["JWT_SECRET_KEY"] = Config.JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)

# Enable CORS so frontend (Live Server) can talk to backend
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Init extensions
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# ──────────────────────────────────────────────
#  Connect to MongoDB
# ──────────────────────────────────────────────
client = MongoClient(Config.MONGO_URI)
mongo = client["hercare"]  # explicit database name

print(f"[OK] Connected to MongoDB: {Config.MONGO_URI}")

# Create index on email for fast lookups & uniqueness
mongo.users.create_index("email", unique=True)

# ──────────────────────────────────────────────
#  Register Blueprints (Routes)
# ──────────────────────────────────────────────
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.daily_log import daily_log_bp
from routes.cycle import cycle_bp
from routes.insights import insights_bp

app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(daily_log_bp)
app.register_blueprint(cycle_bp)
app.register_blueprint(insights_bp, url_prefix="/api/insights")

# ──────────────────────────────────────────────
#  Health Check Route
# ──────────────────────────────────────────────
@app.route("/")
def health_check():
    return {"status": "ok", "message": "herCare API is running 🌸"}

@app.route("/api")
def api_info():
    return {
        "app": "herCare API",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "register": "POST /api/auth/register",
                "login": "POST /api/auth/login"
            }
        }
    }

# ──────────────────────────────────────────────
#  Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
