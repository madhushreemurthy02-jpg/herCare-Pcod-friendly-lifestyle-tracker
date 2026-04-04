from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from models.user import create_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
bcrypt = Bcrypt()


# ──────────────────────────────────────────────
#  POST /api/auth/register
# ──────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    # --- validate required fields ---
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    phone = (data.get("phone") or "").strip()

    if not first_name or not last_name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Please fill in all required fields 🌸"
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Password must be at least 6 characters 🌷"
        }), 400

    # --- check if email already exists ---
    from app import mongo
    db = mongo

    if db.users.find_one({"email": email}):
        return jsonify({
            "success": False,
            "message": "An account with this email already exists"
        }), 409

    # --- hash password & save user ---
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user_doc = create_user(first_name, last_name, email, password_hash, phone)
    result = db.users.insert_one(user_doc)

    # --- create JWT token ---
    user_id = str(result.inserted_id)
    token = create_access_token(identity=user_id)

    return jsonify({
        "success": True,
        "message": f"Welcome to herCare, {first_name}! 🌸",
        "token": token,
        "user": {
            "id": user_id,
            "first_name": first_name
        }
    }), 201


# ──────────────────────────────────────────────
#  POST /api/auth/login
# ──────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Please enter your email and password 🌸"
        }), 400

    # --- find user ---
    from app import mongo
    db = mongo

    user = db.users.find_one({"email": email})

    if not user:
        return jsonify({
            "success": False,
            "message": "No account found with this email. Please sign up first 🌷"
        }), 404

    # --- check password ---
    if not bcrypt.check_password_hash(user["password"], password):
        return jsonify({
            "success": False,
            "message": "Incorrect password. Please try again."
        }), 401

    # --- create JWT token ---
    user_id = str(user["_id"])
    token = create_access_token(identity=user_id)

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['first_name']}! 🌸",
        "token": token,
        "user": {
            "id": user_id,
            "first_name": user["first_name"]
        }
    }), 200
