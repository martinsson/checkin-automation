import email as email_lib
import email.utils
import re
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

from imapclient import IMAPClient

from .ports import CleanerNotifier, CleanerQuery, CleanerResponse

REQUEST_ID_PATTERN = re.compile(r"\[REQ-([^\]]+)\]")


class EmailCleanerNotifier(CleanerNotifier):
    """Adapter: communicate with cleaners via email (SMTP send, IMAP receive)."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        imap_host: str,
        imap_port: int,
        cleaner_email: str,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.cleaner_email = cleaner_email

    async def send_query(self, query: CleanerQuery) -> str:
        subject = f"[REQ-{query.request_id}] {query.property_name} — {query.date}"

        msg = MIMEText(query.message, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = self.cleaner_email
        msg["Message-ID"] = email.utils.make_msgid(domain="checkin-automation")
        msg["X-Request-ID"] = query.request_id

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

        return msg["Message-ID"]

    async def poll_responses(self) -> list[CleanerResponse]:
        responses = []

        with IMAPClient(self.imap_host, port=self.imap_port, ssl=True) as client:
            client.login(self.smtp_user, self.smtp_password)
            client.select_folder("INBOX")

            uids = client.search(["UNSEEN", "FROM", self.cleaner_email])
            if not uids:
                return responses

            fetched = client.fetch(uids, ["RFC822"])
            for uid, data in fetched.items():
                raw_bytes = data[b"RFC822"]
                msg = email_lib.message_from_bytes(raw_bytes)

                subject = msg["Subject"] or ""
                request_id = self._extract_request_id(subject)

                if request_id:
                    body = self._get_body(msg)
                    responses.append(
                        CleanerResponse(
                            request_id=request_id,
                            raw_text=body,
                            received_at=datetime.now(timezone.utc),
                        )
                    )
                    client.set_flags([uid], [b"\\Seen"])

        return responses

    @staticmethod
    def _extract_request_id(subject: str) -> str | None:
        match = REQUEST_ID_PATTERN.search(subject)
        return match.group(1) if match else None

    @staticmethod
    def _get_body(msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode("utf-8", errors="replace")
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="replace")
        return ""
