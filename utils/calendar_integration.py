from datetime import datetime, timedelta
from typing import Optional, Dict
from utils.utils import setup_logger

logger = setup_logger(__name__)

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle
    import os
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    logger.warning("Google Calendar libraries not available")

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


class CalendarIntegration:
    def __init__(self):
        self.service = None
        self.available = CALENDAR_AVAILABLE
        
    def authenticate(self) -> bool:
        if not self.available:
            return False
        try:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            creds_path = os.path.join(BASE_DIR, 'credentials.json')
            token_path = os.path.join(BASE_DIR, 'token.pickle')
            
            creds = None
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(creds_path):
                        logger.error(f"credentials.json not found at {creds_path}. Download from Google Cloud Console")
                        return False
                    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar authenticated successfully")
            return True
        except Exception as e:
            logger.error(f"Calendar authentication failed: {str(e)}")
            return False
    
    def create_reminder_event(
        self,
        medicine_name: str,
        dosage: str,
        reminder_time: str,
        start_date: str,
        duration_days: int,
        instructions: Optional[str] = None
    ) -> Dict:
        if not self.service:
            if not self.authenticate():
                return {"success": False, "error": "Authentication failed"}
        
        try:
            start_datetime = datetime.strptime(f"{start_date} {reminder_time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=15)
            end_date = datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=duration_days)
            
            description = f"Take {dosage}"
            if instructions:
                description += f"\n\nInstructions: {instructions}"
            
            event = {
                'summary': f'💊 {medicine_name}',
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'recurrence': [
                    f'RRULE:FREQ=DAILY;UNTIL={end_date.strftime("%Y%m%d")}T235959Z'
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10},
                        {'method': 'popup', 'minutes': 0},
                        {'method': 'email', 'minutes': 15},
                    ],
                },
            }
            
            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f"Calendar event created: {created_event.get('htmlLink')}")
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "event_link": created_event.get('htmlLink')
            }
        
        except Exception as e:
            logger.error(f"Failed to create calendar event: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_multiple_reminder_events(
        self,
        medicine_name: str,
        dosage: str,
        times: list,
        start_date: str,
        duration_days: int,
        instructions: Optional[str] = None
    ) -> Dict:
        results = []
        for time in times:
            result = self.create_reminder_event(
                medicine_name, dosage, time, start_date, duration_days, instructions
            )
            results.append(result)
        
        success_count = sum(1 for r in results if r.get('success'))
        
        return {
            "success": success_count > 0,
            "total": len(results),
            "created": success_count,
            "details": results
        }
