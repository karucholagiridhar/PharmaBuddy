import re
from datetime import datetime

class Validator:
    @staticmethod
    def validate_medication_input(data):
        errors = []
        
        if not data.get('name') or len(data['name'].strip()) < 2:
            errors.append("Medicine name is required and must be at least 2 characters.")
            
        if not data.get('times') or len(data['times']) == 0:
            errors.append("At least one timing is required.")
            
        if data.get('times'):
            for t in data['times']:
                try:
                    datetime.strptime(t, "%H:%M")
                except ValueError:
                    errors.append(f"Invalid time format: {t}. Use HH:MM.")
        
        if data.get('email_notification') and not data.get('notification_email'):
             errors.append("Email is required if notifications are enabled.")
             
        if data.get('notification_email') and not re.match(r"[^@]+@[^@]+\.[^@]+", data['notification_email']):
            errors.append("Invalid email format.")

        return errors

    @staticmethod
    def validate_login(username, password):
        if not username or not password:
            return "Username and password are required."
        return None
