import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.constants.messages import OtpPurpose

import logging
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_name = settings.EMAILS_FROM_NAME
        self.from_email = settings.EMAILS_FROM_ADDRESS

    def send_otp_email(self, email: str, otp: str, purpose: OtpPurpose) -> bool:

        if settings.APP_ENV == "development":
            logger.info(f"DEV MODE: OTP for {email} is {otp}")
            return True
        
        subject = "Your OTP — Dentist AI"

        if purpose == OtpPurpose.PASSWORD_RESET:
            body = f"""
            <p>You requested a password reset.</p>
            <p>Your OTP is: <strong>{otp}</strong></p>
            <p>Expires in 10 minutes.</p>
            """
        else:
            body = f"""
            <p>Your verification OTP is: <strong>{otp}</strong></p>
            <p>Expires in 10 minutes.</p>
            """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = email
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, email, msg.as_string())
            return True

        except Exception as e:
            logger.error(f"Email send failed to {email}: {e}")
            return False