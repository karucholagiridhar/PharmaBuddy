import smtplib
import os
import pandas as pd
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Dict, Optional, Union
from utils.config import Config

logger = logging.getLogger(__name__)

class EmailManager:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.sender_email = os.getenv("MAIL_USERNAME")
        self.sender_password = os.getenv("MAIL_PASSWORD")
        self.enabled = bool(self.sender_email and self.sender_password)
        
        if not self.enabled:
            logger.warning("EmailManager disabled: MAIL_USERNAME or MAIL_PASSWORD not set in .env")

    def send_email(
        self, 
        recipient_email: str, 
        subject: str, 
        body: str, 
        attachment_path: Optional[str] = None,
        is_html: bool = True
    ) -> Dict[str, Union[bool, str]]:
        """
        Send a generic email with optional attachment.
        """
        if not self.enabled:
            return {"success": False, "error": "Email configuration missing"}

        try:
            message = MIMEMultipart()
            message['From'] = self.sender_email
            message['To'] = recipient_email
            message['Subject'] = subject

            msg_type = 'html' if is_html else 'plain'
            message.attach(MIMEText(body, msg_type))

            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                filename = os.path.basename(attachment_path)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={filename}'
                )
                message.attach(part)

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())
            
            logger.info(f"Email sent to {recipient_email}")
            return {"success": True, "message": "Email sent successfully"}

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_adherence_report(
        self, 
        recipient_email: str, 
        stats_data: Dict, 
        user_name: Optional[str] = "User"
    ) -> Dict[str, Union[bool, str]]:
        """
        Generate a CSV report from stats and send it.
        """
        if not self.enabled:
            return {"success": False, "error": "Email configuration missing"}
            
        try:
            # Create a DataFrame for detailed stats
            details = stats_data.get('reminder_details', [])
            if not details:
                return {"success": False, "error": "No data to report"}
                
            df = pd.DataFrame(details)
            
            # Format filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"medimate_adherence_report_{timestamp}.csv"
            
            # Use a temporary directory or media root
            # Assuming src/../data exists or similar
            report_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'reports')
            os.makedirs(report_dir, exist_ok=True)
            file_path = os.path.join(report_dir, filename)
            
            df.to_csv(file_path, index=False)
            
            # Create Email Body
            body = f"""
            <html>
            <body>
                <h2>💊 PharmaBuddy Adherence Report</h2>
                <p>Hello {user_name},</p>
                <p>Here is your medication adherence summary for the last {stats_data.get('period_days', 7)} days.</p>
                
                <table style="border-collapse: collapse; width: 100%; max_width: 600px;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 10px; border: 1px solid #ddd;">Metric</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Value</th>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Total Doses</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{stats_data.get('total_doses')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Taken</td>
                        <td style="padding: 10px; border: 1px solid #ddd; color: green;">{stats_data.get('taken_count')}</td>
                    </tr>
                     <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Missed</td>
                        <td style="padding: 10px; border: 1px solid #ddd; color: red;">{stats_data.get('missed_count')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Adherence Rate</td>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>{stats_data.get('adherence_rate')}%</strong></td>
                    </tr>
                </table>
                
                <p>A detailed CSV report is attached.</p>
                <p>Stay healthy,<br>PharmaBuddy Team</p>
            </body>
            </html>
            """
            
            result = self.send_email(
                recipient_email, 
                "Your PharmaBuddy Adherence Report",
                body, 
                file_path
            )
            
            # Clean up (optional, maybe keep for debug?)
            # os.remove(file_path) 
            
            return result

        except Exception as e:
            logger.error(f"Failed to generate/send report: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_dose_reminder(
        self,
        recipient_email: str,
        medicine_name: str,
        dosage: str,
        instructions: str,
        time: str
    ):
        """Send a quick email reminder for a dose"""
        subject = f"🔔 Time to take {medicine_name}"
        body = f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                <h2 style="color: #2c3e50;">Time for your Medication</h2>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="margin: 0; color: #16a085;">💊 {medicine_name}</h3>
                    <p style="margin: 5px 0 0 0; font-size: 16px;"><strong>Dose:</strong> {dosage}</p>
                </div>
                
                <p><strong>Scheduled Time:</strong> {time}</p>
                {f'<p><strong>Instructions:</strong> {instructions}</p>' if instructions else ''}
                
                <p style="margin-top: 20px; font-size: 12px; color: #7f8c8d;">
                    Stay consistent! Log this dose in your PharmaBuddy app.
                </p>
            </div>
        </body>
        </html>
        """
        return self.send_email(recipient_email, subject, body)
