"""
ServicePulse - Email Notification Provider Abstraction
Author: Muhammadyusuf Usmonov
"""
import abc
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from backend.app.core.config import settings

logger = logging.getLogger("servicepulse.email")


class EmailProvider(abc.ABC):
    """Abstract interface for transactional email delivery."""

    @abc.abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email to a single recipient."""
        pass


class SMTPEmailProvider(EmailProvider):
    """Production-grade SMTP email delivery provider."""

    def __init__(
        self,
        host: str,
        port: int = 587,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        from_email: str = "noreply@servicepulse.uz",
        from_name: str = "ServicePulse Platform"
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email
        self.from_name = from_name

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            # Synchronous SMTP in thread or standard call
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)
            logger.info("Successfully delivered email to %s (subject: %s)", to_email, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send SMTP email to %s: %s", to_email, exc)
            return False


class NullEmailProvider(EmailProvider):
    """
    Fallback provider when no SMTP server is configured.
    Explicitly logs that email delivery is disabled/in null mode.
    Never pretends that an email was delivered to an external server.
    """

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        logger.info(
            "[EmailProvider:Null] Outbound email skipped (no SMTP configured). Recipient: %s | Subject: %s",
            to_email,
            subject
        )
        return False


def get_email_provider() -> EmailProvider:
    """Factory creating the appropriate EmailProvider according to configuration."""
    if settings.SMTP_HOST:
        return SMTPEmailProvider(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            user=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_TLS,
            from_email=settings.EMAILS_FROM_EMAIL,
            from_name=settings.EMAILS_FROM_NAME
        )
    return NullEmailProvider()


class EmailNotificationService:
    """High-level transactional email operations for authentication & onboarding."""

    def __init__(self, provider: Optional[EmailProvider] = None):
        self.provider = provider or get_email_provider()

    async def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        org_name: str,
        invite_code: str,
        role_name: str
    ) -> bool:
        subject = f"Invitation to join {org_name} on ServicePulse"
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #0f172a;">You've been invited to ServicePulse</h2>
            <p><strong>{inviter_name}</strong> has invited you to join <strong>{org_name}</strong> as <strong>{role_name}</strong>.</p>
            <div style="margin: 24px 0; padding: 16px; background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; text-align: center;">
                <p style="margin: 0 0 8px 0; font-size: 14px; color: #64748b;">Your Invitation Code:</p>
                <code style="font-size: 20px; font-weight: bold; color: #0284c7; letter-spacing: 1px;">{invite_code}</code>
            </div>
            <p style="font-size: 14px; color: #64748b;">Enter this invitation code on the ServicePulse registration page to activate your account.</p>
        </div>
        """
        text = f"You have been invited by {inviter_name} to join {org_name} as {role_name}. Invitation code: {invite_code}"
        return await self.provider.send_email(to_email, subject, html, text)

    async def send_org_request_received(self, to_email: str, org_name: str) -> bool:
        subject = f"ServicePulse: Organization Registration Received ({org_name})"
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #0f172a;">Registration Under Review</h2>
            <p>Thank you for registering <strong>{org_name}</strong> on ServicePulse.</p>
            <p>Your request has been submitted to the platform administration for verification. You will receive an email once your organization has been approved.</p>
        </div>
        """
        text = f"Registration request for {org_name} received and is currently under review by platform administration."
        return await self.provider.send_email(to_email, subject, html, text)

    async def send_org_request_approved(self, to_email: str, org_name: str) -> bool:
        subject = f"Welcome to ServicePulse: {org_name} Approved"
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #16a34a;">Organization Approved!</h2>
            <p>Your organization <strong>{org_name}</strong> has been approved by the platform administration.</p>
            <p>You may now log in to ServicePulse using the email and password you provided during registration.</p>
        </div>
        """
        text = f"Organization {org_name} approved! You can now log in using your registered credentials."
        return await self.provider.send_email(to_email, subject, html, text)

    async def send_org_request_rejected(self, to_email: str, org_name: str, reason: Optional[str] = None) -> bool:
        subject = f"ServicePulse: Update on your registration for {org_name}"
        reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #dc2626;">Registration Update</h2>
            <p>Your registration request for <strong>{org_name}</strong> could not be approved at this time.</p>
            {reason_text}
            <p>Please contact support@servicepulse.uz if you believe this was an error.</p>
        </div>
        """
        text = f"Your registration request for {org_name} was not approved. Reason: {reason or 'Not specified'}"
        return await self.provider.send_email(to_email, subject, html, text)


email_notification_service = EmailNotificationService()
