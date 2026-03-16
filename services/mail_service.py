import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.config import Config
from utils.utils import setup_logger

logger = setup_logger(__name__)

class MailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587  # Check port 587 again
        self.sender_email = Config.EMAIL_SENDER
        self.password = Config.EMAIL_PASSWORD
        self.enabled = bool(self.sender_email and self.password)

    def send_dose_reminder(self, to_email, medicine_name, dosage, instructions, time_str):
        if not self.enabled:
            logger.warning("Email service disabled: Credentials missing.")
            return False, "Email service disabled in server config."

        def _send():
            try:
                subject = f"💊 Reminder: Time for {medicine_name}"
                
                html_content = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                            <h2 style="color: #008080;">Time to take your medication</h2>
                            <p>Hello,</p>
                            <p>This is a reminder to take the following medication scheduled for <strong>{time_str}</strong>:</p>
                            
                            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #008080; margin: 20px 0;">
                                <h3 style="margin: 0; color: #008080;">{medicine_name}</h3>
                                <p style="margin: 5px 0 0;"><strong>Dosage:</strong> {dosage}</p>
                                {f'<p style="margin: 5px 0 0;"><strong>Instructions:</strong> {instructions}</p>' if instructions else ''}
                            </div>
                            
                            <p>Please log this in your <a href="#" style="color: #008080;">PharmaBuddy Dashboard</a>.</p>
                            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                            <small style="color: #666;">PharmaBuddy Health Assistant</small>
                        </div>
                    </body>
                </html>
                """
                
                msg = MIMEMultipart()
                msg['From'] = self.sender_email
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(html_content, 'html'))

                # Use standard SMTP with STARTTLS and timeout
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(self.sender_email, self.password)
                    server.send_message(msg)
                
                logger.info(f"Email sent to {to_email} for {medicine_name}")
            except Exception as e:
                logger.error(f"Failed to send email to {to_email}: {e}")

        # Run in background thread
        import threading
        threading.Thread(target=_send).start()
        return True, "Email queued for sending"

    def send_performance_report(self, to_email, stats):
        if not self.enabled:
            logger.warning("Email service disabled: Credentials missing.")
            return False, "Email service disabled in server config."

        def _send():
            try:
                subject = f"📊 Your Medication Performance Report"
                
                # Format the details list
                details_html = ""
                for item in stats.get('reminder_details', []):
                    details_html += f"""
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px;">{item['medicine_name']}</td>
                        <td style="padding: 10px;">{item['total_doses']}</td>
                        <td style="padding: 10px; color: green;">{item['taken']}</td>
                        <td style="padding: 10px; color: red;">{item['missed']}</td>
                        <td style="padding: 10px;">{item['adherence']}%</td>
                    </tr>
                    """

                html_content = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                            <h2 style="color: #008080;">Weekly Performance Report</h2>
                            <p>Hello,</p>
                            <p>Here is your medication adherence report for the last {stats.get('period_days', 7)} days.</p>
                            
                            <div style="display: flex; justify-content: space-around; background-color: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px;">
                                <div style="text-align: center;">
                                    <h3 style="margin: 0; color: #008080;">{stats.get('adherence_rate', 0)}%</h3>
                                    <small>Adherence</small>
                                </div>
                                <div style="text-align: center;">
                                    <h3 style="margin: 0; color: green;">{stats.get('taken_count', 0)}</h3>
                                    <small>Taken</small>
                                </div>
                                <div style="text-align: center;">
                                    <h3 style="margin: 0; color: red;">{stats.get('missed_count', 0)}</h3>
                                    <small>Missed</small>
                                </div>
                            </div>
                            
                            <h4 style="margin-top: 30px;">Detailed Breakdown</h4>
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                                <thead>
                                    <tr style="background-color: #eee;">
                                        <th style="padding: 10px;">Medicine</th>
                                        <th style="padding: 10px;">Total</th>
                                        <th style="padding: 10px;">Taken</th>
                                        <th style="padding: 10px;">Missed</th>
                                        <th style="padding: 10px;">Rate</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {details_html}
                                </tbody>
                            </table>
                            
                            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                            <small style="color: #666;">PharmaBuddy Health Assistant</small>
                        </div>
                    </body>
                </html>
                """
                
                msg = MIMEMultipart()
                msg['From'] = self.sender_email
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(html_content, 'html'))

                # Use standard SMTP with STARTTLS and timeout
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(self.sender_email, self.password)
                    server.send_message(msg)
                
                logger.info(f"Performance report sent to {to_email}")
            except Exception as e:
                logger.error(f"Failed to send report to {to_email}: {e}")

        # Run in background thread
        import threading
        threading.Thread(target=_send).start()
        return True, "Report queued for sending"
