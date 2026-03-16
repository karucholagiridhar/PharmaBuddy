import bcrypt
from pymongo import MongoClient
from datetime import datetime
from utils.config import Config
from utils.utils import setup_logger

logger = setup_logger(__name__)

class AuthManager:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI, **Config.get_tls_kwargs())
        self.db = self.client.get_database("prescription_db")
        self.users = self.db.users
        self.users.create_index([("username", 1)], unique=True, background=True)

    def register_user(self, username, password, email=""):
        if self.users.find_one({"username": username}):
            return False, "Username already exists."
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.users.insert_one({
            "username": username,
            "password_hash": hashed,
            "email": email,
            "created_at": datetime.utcnow(),
            "display_name": "",
            "language": "en",
            "theme": "dark",
            "avatar": ""
        })
        logger.info(f"Registered user: {username}")
        return True, "User registered successfully."

    def login_user(self, username, password):
        user = self.users.find_one({"username": username})
        if not user:
            return False, "Invalid username or password."
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            logger.info(f"User logged in: {username}")
            return True, "Login successful."
        else:
            return False, "Invalid username or password."

    def get_user_profile(self, username: str) -> dict:
        user = self.users.find_one({"username": username}, {"password_hash": 0, "_id": 0})
        return user or {}

    def update_user_profile(self, username: str, updates: dict) -> bool:
        allowed = {"display_name", "language", "theme", "avatar"}
        safe = {k: v for k, v in updates.items() if k in allowed}
        if not safe:
            return False
        self.users.update_one({"username": username}, {"$set": safe})
        return True
