import email as email_lib
import email.utils
import logging
import os
import re
import smtplib
from email.header import decode_header as _decode_header
from datetime import datetime, timezone
from email.mime.text import MIMEText

import anthropic
from imapclient import IMAPClient

from src.ports.cleaner import CleanerNotifier, CleanerQuery, CleanerResponse

log = logging.getLogger(__name__)

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
        anthropic_api_key: str | None = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.cleaner_email = cleaner_email
        self._anthropic = anthropic.Anthropic(
            api_key=anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
        )

    def _translate_to_french(self, text: str) -> str:
        """Translate text to French using Claude. Returns original on failure."""
        try:
            response = self._anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": (
                    "Translate the following guest message into French. "
                    "If it is already in French, return it as-is. "
                    "Return ONLY the translated text, nothing else.\n\n"
                    f"{text}"
                )}],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            log.warning("Translation failed, using original message: %s", exc)
            return text

    async def send_query(self, query: CleanerQuery) -> str:
        subject = f"{query.property_name} — {query.date}"

        translated = self._translate_to_french(query.message)
        body = (
            f"Bonjour {query.cleaner_name},\n\n"
            f"Voici une nouvelle demande, dites moi ce qui est possible, "
            f"raisonnablement bien entendu.\n\n"
            f"{translated}\n\n"
            f"[REQ-{query.request_id}]"
        )
        msg = MIMEText(body, _charset="utf-8")
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

                # Try X-Request-ID header first, then body [REQ-...], then subject
                body = self._get_body(msg)
                request_id = msg["X-Request-ID"] or None
                if not request_id:
                    request_id = self._extract_request_id(body)
                if not request_id:
                    subject = self._decode_subject(msg["Subject"] or "")
                    request_id = self._extract_request_id(subject)

                if request_id:
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
    def _decode_subject(subject: str) -> str:
        parts = _decode_header(subject)
        return "".join(
            t.decode(enc or "utf-8") if isinstance(t, bytes) else t
            for t, enc in parts
        )

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
