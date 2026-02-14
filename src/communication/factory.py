import os

from .ports import CleanerNotifier


def create_cleaner_notifier(channel: str | None = None) -> CleanerNotifier:
    """
    Factory: create the right adapter based on config.

    The channel can be passed explicitly or read from the
    CLEANING_STAFF_CHANNEL env var. Defaults to "console".
    """
    channel = channel or os.environ.get("CLEANING_STAFF_CHANNEL", "console")

    if channel == "email":
        from .email_notifier import EmailCleanerNotifier

        return EmailCleanerNotifier(
            smtp_host=os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.environ.get("EMAIL_SMTP_PORT", "587")),
            smtp_user=os.environ["EMAIL_USER"],
            smtp_password=os.environ["EMAIL_PASSWORD"],
            imap_host=os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com"),
            imap_port=int(os.environ.get("EMAIL_IMAP_PORT", "993")),
            cleaner_email=os.environ["CLEANER_EMAIL"],
        )

    if channel == "console":
        from .console_notifier import ConsoleCleanerNotifier

        return ConsoleCleanerNotifier()

    raise ValueError(f"Unknown cleaner channel: {channel!r}")
