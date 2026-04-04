from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def token_required(f):
    """
    Decorator that protects a route — checks for a valid JWT token
    in the Authorization header before allowing access.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Invalid or missing token. Please sign in again."
            }), 401

    return decorated
