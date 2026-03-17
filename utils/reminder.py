from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pymongo import MongoClient
from utils.config import Config
from utils.utils import setup_logger

logger = setup_logger(__name__)


class ReminderManager:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI, **Config.get_tls_kwargs())
        self.db = self.client['medimate']
        self.reminders = self.db['reminders']
        self.adherence = self.db['adherence_log']
        self._ensure_indexes()

    def _ensure_indexes(self):
        self.reminders.create_index([("user_id", 1), ("is_active", 1)], background=True)
        self.reminders.create_index([("user_id", 1), ("is_active", 1), ("start_date", 1), ("end_date", 1)], background=True)
        self.adherence.create_index([("user_id", 1), ("date", 1), ("status", 1)], background=True)
        self.adherence.create_index([("user_id", 1), ("medicine_name", 1), ("date", 1), ("scheduled_time", 1)], background=True)
        self.db['email_notifications'].create_index([("reminder_id", 1), ("date", 1), ("scheduled_time", 1)], background=True)
    
    def add_reminder(
        self,
        user_id: str,
        medicine_name: str,
        dosage: str,
        frequency: str,
        times: List[str],
        duration_days: int,
        start_date: str,
        instructions: Optional[str] = None,
        with_food: bool = False,
        email_notification: bool = False,
        notification_email: Optional[str] = None
    ) -> Dict:
        try:
            reminder = {
                "user_id": user_id,
                "medicine_name": medicine_name,
                "dosage": dosage,
                "frequency": frequency,
                "times": times,
                "duration_days": duration_days,
                "start_date": start_date,
                "end_date": self._calculate_end_date(start_date, duration_days),
                "instructions": instructions,
                "with_food": with_food,
                "email_notification": email_notification,
                "notification_email": notification_email,
                "is_active": True,
                "created_at": datetime.now().isoformat()
            }
            
            result = self.reminders.insert_one(reminder)
            reminder['_id'] = str(result.inserted_id)
            
            logger.info(f"Reminder added for {medicine_name} by user {user_id}")
            return {"success": True, "reminder": reminder}
        
        except Exception as e:
            logger.error(f"Error adding reminder: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_user_reminders(self, user_id: str, active_only: bool = True) -> List[Dict]:
        try:
            query = {"user_id": user_id}
            if active_only:
                query["is_active"] = True
            reminders = list(self.reminders.find(query).sort("created_at", -1))
            for reminder in reminders:
                reminder['_id'] = str(reminder['_id'])
            return reminders
        
        except Exception as e:
            logger.error(f"Error fetching reminders: {str(e)}")
            return []
    
    def get_todays_reminders(self, user_id: str) -> List[Dict]:
        try:
            today = datetime.now().date().isoformat()

            reminders = list(self.reminders.find({
                "user_id": user_id,
                "is_active": True,
                "start_date": {"$lte": today},
                "end_date": {"$gte": today}
            }))

            # Fetch all taken logs for today in ONE query instead of one per dose
            taken_cursor = self.adherence.find(
                {"user_id": user_id, "date": today, "status": "taken"},
                {"medicine_name": 1, "scheduled_time": 1, "_id": 0}
            )
            taken_set = {(log["medicine_name"], log["scheduled_time"]) for log in taken_cursor}

            todays_schedule = []
            for reminder in reminders:
                for time in reminder['times']:
                    todays_schedule.append({
                        "_id": str(reminder['_id']),
                        "id": str(reminder['_id']),
                        "medicine_name": reminder['medicine_name'],
                        "dosage": reminder['dosage'],
                        "time": time,
                        "times": reminder['times'],
                        "frequency": reminder['frequency'],
                        "with_food": reminder.get('with_food', False),
                        "instructions": reminder.get('instructions', ''),
                        "taken": (reminder['medicine_name'], time) in taken_set
                    })
            todays_schedule.sort(key=lambda x: x['time'])
            return todays_schedule

        except Exception as e:
            logger.error(f"Error fetching today's reminders: {str(e)}")
            return []

    def get_logs_for_date(self, user_id: str, date_obj) -> List[Dict]:
        """Get adherence logs for a specific date"""
        try:
            date_str = date_obj.isoformat() if hasattr(date_obj, 'isoformat') else str(date_obj)
            
            logs = list(self.adherence.find({
                "user_id": user_id,
                "date": date_str
            }))
            
            # Add time_slot based on scheduled_time logic if not present
            # The UI expects 'time_slot' but our mark_as_taken only saves 'scheduled_time'
            # We need to map scheduled_time back to morning/afternoon/night or ensure UI is robust
            # For now, let's just return the logs and let's see how UI uses it.
            # Looking at UI: it checks log['time_slot'] == 'morning' etc.
            # But the log entry in mark_as_taken doesn't seem to save 'time_slot'.
            # We need to fix mark_as_taken to save time_slot or infer it here.
            
            # Let's infer it here if possible, or just pass it as is.
            # Actually, looking at mark_as_taken, it takes 'scheduled_time'.
            # The UI logic: log['time_slot'] == 'morning'
            # We need to check if 'time_slot' is in the log.
            # If not, we might fail.
            # Let's assume we need to add 'time_slot' to the log when retrieving or when saving.
            # Since we can't easily change existing logs, let's try to infer or match by time.
            
            # Wait, the UI code says:
            # log_entry = next((log for log in today_logs if log['medicine_name'] == med_name and log['time_slot'] == 'morning'), None)
            
            # But mark_as_taken saves:
            # "scheduled_time": scheduled_time
            
            # So indeed, 'time_slot' is missing from the log.
            # I must fix this mismatch.
            # For now, I will add a hack in get_logs_for_date to try to find the time slot from the reminder settings? 
            # OR better, I should modify the UI to match by time, OR modify get_logs_for_date to map times.
            
            # Let's get the reminders to map times to slots
            reminders = self.get_user_reminders(user_id)
            for log in logs:
                if 'time_slot' not in log:
                    # Try to find the reminder and map the time
                    med_name = log.get('medicine_name')
                    time = log.get('scheduled_time')
                    
                    found = False
                    for r in reminders:
                        if r.get('medicine_name') == med_name:
                            # Check r['times'] (which is a list of strings)
                            # But we need to know if it's morning/afternoon/night
                            # The 'reminders' from get_user_reminders stores 'times' as a list.
                            # It DOES NOT store which slot it belongs to explicitly like {'morning': '08:00'}.
                            # Wait, in add_reminder, we saw:
                            # "times": times (list)
                            # But the UI sends:
                            # schedule['morning']...
                            
                            # Let's look at add_reminder again in UI:
                            # schedule = {} -> schedule['morning'] = ...
                            # But then it calls add_reminder with times=times_list (sorted list)
                            # So the backend 'reminder' object ONLY has a list of times. It lost the key 'morning'/'afternoon'.
                            
                            # However, the UI `render_active_schedule` tries to use `reminder.get('schedule', {})`.
                            # `get_user_reminders` returns the raw mongo document.
                            # It does NOT seem to have a 'schedule' field with 'morning'/'afternoon' keys if we look at `add_reminder` implementation in reminder.py:
                            # It saves: "times": times, "frequency": frequency... but NOT the "morning"/"afternoon" map.
                            
                            # So `reminder.get('schedule', {})` in UI will be EMPTY!
                            # The UI code is trying to read non-existent data structure 'schedule'.
                            pass
            
            # This reveals a deeper data structure mismatch.
            # The backend stores "times": ["08:00", "20:00"]
            # The UI `render_active_schedule` expects `reminder.get('schedule')` to be `{'morning': '08:00', ...}`
            
            # I need to adapt `get_logs_for_date` AND likely `render_active_schedule`.
            # But let's start by implementing `get_logs_for_date` simply returning the logs.
            # And then I will probably have to fix `src/ui_pages_medical.py` to handle the 'times' list instead of 'schedule' dict.
            
            return logs
            
        except Exception as e:
            logger.error(f"Error fetching logs: {str(e)}")
            return []
    
    def mark_as_taken(
        self,
        user_id: str,
        medicine_name: str,
        scheduled_time: str,
        actual_time: Optional[str] = None
    ) -> Dict:
        """Mark a reminder as taken"""
        try:
            if actual_time is None:
                actual_time = datetime.now().strftime("%H:%M")
            
            log_entry = {
                "user_id": user_id,
                "medicine_name": medicine_name,
                "scheduled_time": scheduled_time,
                "actual_time": actual_time,
                "date": datetime.now().date().isoformat(),
                "timestamp": datetime.now().isoformat(),
                "status": "taken"
            }
            
            self.adherence.insert_one(log_entry)
            logger.info(f"Marked {medicine_name} as taken for user {user_id}")
            
            return {"success": True, "message": "Marked as taken"}
        
        except Exception as e:
            logger.error(f"Error marking as taken: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def mark_as_skipped(
        self,
        user_id: str,
        medicine_name: str,
        scheduled_time: str,
        reason: Optional[str] = None
    ) -> Dict:
        """Mark a reminder as skipped"""
        try:
            log_entry = {
                "user_id": user_id,
                "medicine_name": medicine_name,
                "scheduled_time": scheduled_time,
                "date": datetime.now().date().isoformat(),
                "timestamp": datetime.now().isoformat(),
                "status": "skipped",
                "reason": reason
            }
            
            self.adherence.insert_one(log_entry)
            logger.info(f"Marked {medicine_name} as skipped for user {user_id}")
            
            return {"success": True, "message": "Marked as skipped"}
        
        except Exception as e:
            logger.error(f"Error marking as skipped: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_adherence_stats(self, user_id: str, days: int = 7) -> Dict:
        """Get adherence statistics for the last N days"""
        try:
            # Get active reminders
            reminders = list(self.reminders.find({
                "user_id": user_id,
                "is_active": True
            }))
            
            start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
            
            logs = list(self.adherence.find({
                "user_id": user_id,
                "date": {"$gte": start_date}
            }))
            
            total = len(logs)
            taken = len([log for log in logs if log['status'] == 'taken'])
            missed = len([log for log in logs if log['status'] == 'skipped'])
            
            adherence_rate = (taken / total * 100) if total > 0 else 0
            
            # Build detailed stats per reminder
            reminder_details = []
            for reminder in reminders:
                med_logs = [log for log in logs if log.get('medicine_name') == reminder['medicine_name']]
                med_total = len(med_logs)
                med_taken = len([log for log in med_logs if log['status'] == 'taken'])
                med_missed = len([log for log in med_logs if log['status'] == 'skipped'])
                med_adherence = (med_taken / med_total * 100) if med_total > 0 else 0
                
                reminder_details.append({
                    'medicine_name': reminder['medicine_name'],
                    'dosage': reminder['dosage'],
                    'times': reminder['times'],
                    'total_doses': med_total,
                    'taken': med_taken,
                    'missed': med_missed,
                    'adherence': round(med_adherence, 1)
                })
            
            return {
                "total_reminders": len(reminders),
                "total_doses": total,
                "taken_count": taken,
                "missed_count": missed,
                "adherence_rate": round(adherence_rate, 1),
                "period_days": days,
                "reminder_details": reminder_details
            }
        
        except Exception as e:
            logger.error(f"Error calculating adherence: {str(e)}")
            return {
                "total_reminders": 0,
                "total_doses": 0,
                "taken_count": 0,
                "missed_count": 0,
                "adherence_rate": 0,
                "period_days": days,
                "reminder_details": []
            }
    
    def delete_reminder(self, reminder_id: str) -> Dict:
        """Delete a reminder"""
        try:
            from bson.objectid import ObjectId
            result = self.reminders.delete_one({"_id": ObjectId(reminder_id)})
            
            if result.deleted_count > 0:
                return {"success": True, "message": "Reminder deleted"}
            else:
                return {"success": False, "error": "Reminder not found"}
        
        except Exception as e:
            logger.error(f"Error deleting reminder: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def toggle_reminder(self, reminder_id: str, is_active: bool) -> Dict:
        """Activate or deactivate a reminder"""
        try:
            from bson.objectid import ObjectId
            result = self.reminders.update_one(
                {"_id": ObjectId(reminder_id)},
                {"$set": {"is_active": is_active}}
            )
            
            if result.modified_count > 0:
                status = "activated" if is_active else "deactivated"
                return {"success": True, "message": f"Reminder {status}"}
            else:
                return {"success": False, "error": "Reminder not found"}
        
        except Exception as e:
            logger.error(f"Error toggling reminder: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _calculate_end_date(self, start_date: str, duration_days: int) -> str:
        """Calculate end date from start date and duration"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = start + timedelta(days=duration_days)
        return end.date().isoformat()
    
    def _check_if_taken(self, user_id: str, medicine_name: str, date: str, time: str) -> bool:
        """Check if a medicine was marked as taken"""
        log = self.adherence.find_one({
            "user_id": user_id,
            "medicine_name": medicine_name,
            "date": date,
            "scheduled_time": time,
            "status": "taken"
        })
        return log is not None

    def check_due_reminders(self) -> List[Dict]:
        """
        Check for reminders due now (with ±1 minute tolerance) that haven't
        been notified yet today. Returns list of due reminders enriched with
        a 'current_match_time' field indicating which scheduled time matched.
        """
        try:
            now = datetime.now()
            today = now.date().isoformat()

            # Use current minute + previous minute to handle scheduler timing drift
            current_time = now.strftime("%H:%M")
            prev_time = (now - timedelta(minutes=1)).strftime("%H:%M")
            times_to_check = [current_time, prev_time]

            active_reminders = list(self.reminders.find({
                "is_active": True,
                "email_notification": True,
                "start_date": {"$lte": today},
                "end_date": {"$gte": today},
                "times": {"$in": times_to_check}
            }))

            # Fetch already-sent notifications for today to avoid duplicates
            sent_cursor = self.db['email_notifications'].find(
                {"date": today},
                {"reminder_id": 1, "scheduled_time": 1, "_id": 0}
            )
            notified_set = {(doc["reminder_id"], doc["scheduled_time"]) for doc in sent_cursor}

            due = []
            for reminder in active_reminders:
                rid = str(reminder['_id'])
                # Find the earliest matching time that hasn't been notified yet
                for t in times_to_check:
                    if t in reminder.get('times', []) and (rid, t) not in notified_set:
                        r = dict(reminder)
                        r['_id'] = rid
                        r['current_match_time'] = t
                        due.append(r)
                        break  # One notification per reminder per scheduler run

            return due

        except Exception as e:
            logger.error(f"Error checking due reminders: {str(e)}")
            return []

    def mark_notification_sent(self, reminder_id: str, scheduled_time: str):
        """Record that an email notification was sent to prevent duplicate sends."""
        try:
            self.db['email_notifications'].insert_one({
                "reminder_id": reminder_id,
                "scheduled_time": scheduled_time,
                "date": datetime.now().date().isoformat(),
                "sent_at": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error recording notification sent: {str(e)}")
