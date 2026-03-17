from apscheduler.schedulers.background import BackgroundScheduler
from services.mail_service import MailService
from utils.reminder import ReminderManager
from utils.utils import setup_logger
import atexit

logger = setup_logger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.reminder_mgr = ReminderManager()
        self.mail_svc = MailService()
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown())
        self._add_jobs()

    def _add_jobs(self):
        # Check for medication reminders every minute
        self.scheduler.add_job(
            func=self._check_reminders,
            trigger="interval",
            minutes=1,
            id="medication_reminders",
            replace_existing=True
        )
        logger.info("Scheduler started: Medication reminder job added.")

    def _check_reminders(self):
        try:
            if not self.mail_svc.enabled:
                return

            due_reminders = self.reminder_mgr.check_due_reminders()

            if due_reminders:
                logger.info(f"Found {len(due_reminders)} due reminders.")

            for reminder in due_reminders:
                recipient = reminder.get('notification_email')
                matched_time = reminder.get('current_match_time', '')
                if recipient and matched_time:
                    self.mail_svc.send_dose_reminder(
                        recipient,
                        reminder['medicine_name'],
                        reminder['dosage'],
                        reminder.get('instructions', ''),
                        matched_time
                    )
                    self.reminder_mgr.mark_notification_sent(reminder['_id'], matched_time)
        except Exception as e:
            logger.error(f"Scheduler Job Error: {e}")
