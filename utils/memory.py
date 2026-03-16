from pymongo import MongoClient
from datetime import datetime
import uuid
from utils.config import Config
from utils.utils import setup_logger

logger = setup_logger(__name__)

class MemoryManager:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI, **Config.get_tls_kwargs())
        self.db = self.client.get_database("prescription_db")
        self.sessions = self.db.sessions
        self.messages = self.db.messages
        self._ensure_indexes()
        logger.info("Connected to MongoDB")

    def _ensure_indexes(self):
        self.sessions.create_index([("user_id", 1), ("prescription_id", 1)], background=True)
        self.sessions.create_index([("session_id", 1)], unique=True, background=True)
        self.sessions.create_index([("user_id", 1), ("last_active", -1)], background=True)
        self.messages.create_index([("session_id", 1), ("timestamp", 1)], background=True)

    def get_or_create_session(self, user_id, prescription_id, title=None, filename=None, details=None):
        existing_session = self.sessions.find_one({
            "user_id": user_id,
            "prescription_id": prescription_id
        })
        if existing_session:
            updates = {}
            if title and not existing_session.get("title"):
                updates["title"] = title
            if filename and not existing_session.get("filename"):
                updates["filename"] = filename
            if details and not existing_session.get("details"):
                updates["details"] = details
            if updates:
                self.sessions.update_one(
                    {"_id": existing_session["_id"]},
                    {"$set": updates}
                )
            return existing_session["session_id"], existing_session.get("details", "")
        session_id = str(uuid.uuid4())
        doc = {
            "session_id": session_id,
            "user_id": user_id,
            "prescription_id": prescription_id,
            "summary": "",
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        if title:
            doc["title"] = title
        if filename:
            doc["filename"] = filename
        if details:
            doc["details"] = details
        self.sessions.insert_one(doc)
        logger.info(f"Created new session {session_id} for user {user_id} on prescription {prescription_id}")
        return session_id, details or ""

    def get_session_details(self, session_id):
        session = self.sessions.find_one({"session_id": session_id})
        return session.get("details", "") if session else ""

    def get_prescription_by_filename(self, user_id, filename):
        session = self.sessions.find_one({
            "user_id": user_id,
            "filename": filename
        })
        if session:
            return session["prescription_id"]
        return None

    def add_message(self, session_id, role, content):
        self.messages.insert_one({
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        })
        self.update_last_active(session_id)

    def get_history(self, session_id, limit=10):
        cursor = self.messages.find({"session_id": session_id}).sort("timestamp", 1).limit(limit)
        return list(cursor)

    def get_summary(self, session_id):
        session = self.sessions.find_one({"session_id": session_id})
        return session.get("summary", "") if session else ""

    def update_summary(self, session_id, new_summary):
        self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"summary": new_summary, "last_active": datetime.utcnow()}}
        )

    def update_last_active(self, session_id):
        self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"last_active": datetime.utcnow()}}
        )
    
    def get_user_prescriptions(self, user_id):
        cursor = self.sessions.find(
            {"user_id": user_id, "prescription_id": {"$ne": "GLOBAL"}},
            {"prescription_id": 1, "title": 1, "last_active": 1}
        ).sort("last_active", -1)
        results = []
        seen_ids = set()
        for doc in cursor:
            p_id = doc["prescription_id"]
            if p_id not in seen_ids:
                results.append({
                    "id": p_id,
                    "title": doc.get("title", f"Prescription {p_id[:8]}...")
                })
                seen_ids.add(p_id)
        return results

    def get_all_sessions(self):
        return list(self.sessions.find().sort("last_active", -1))

    def save_otc_result(self, session_id, otc_result):
        self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"otc_result": otc_result}}
        )

    def get_otc_result(self, session_id):
        session = self.sessions.find_one({"session_id": session_id})
        return session.get("otc_result") if session else None

    def delete_session(self, user_id, prescription_id):
        session = self.sessions.find_one({
            "user_id": user_id,
            "prescription_id": prescription_id
        })
        if session:
            session_id = session.get("session_id")
            # Delete messages
            self.messages.delete_many({"session_id": session_id})
            # Delete session
            self.sessions.delete_one({"_id": session["_id"]})
            logger.info(f"Deleted session {session_id} for user {user_id}")
            return True
        return False

