import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/hercare")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "hercare-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours in seconds
