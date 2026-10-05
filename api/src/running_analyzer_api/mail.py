"""Transactional emails (SMTP: Mailpit in development, Brevo in production; docs/SPEC.md §11).

Configured from the environment only, so the worker can use it without the API's settings:
SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD, SMTP_FROM, WEB_URL. Without SMTP_HOST nothing is
sent (and nothing fails): a missing email must never fail an Analysis or a deletion.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)

FAILURE_TEXT = {
    "fps_too_low": "The video has fewer than 60 frames per second. Record at 60 fps or more, or use slow motion for the whole clip.",
    "too_short": "The video is shorter than 20 seconds of running.",
    "runner_not_found": "No runner could be found in the video. Make sure the whole body is in frame.",
    "body_not_fully_visible": "The head or the feet are out of the frame. Move the phone back.",
    "no_steady_running": "No stretch of steady running was found. Start recording once you are at speed and keep running for 20–30 seconds.",
    "not_side_view": "The running direction could not be recognized: film from the side, with the phone perpendicular to the belt.",
    "same_side": "Both side videos show the same side of the runner.",
    "internal_error": "Something went wrong on our side. The team has been notified.",
}


def web_url(path: str = "") -> str:
    return os.environ.get("WEB_URL", "http://localhost:3000").rstrip("/") + path


def send(to: str, subject: str, text: str) -> bool:
    host = os.environ.get("SMTP_HOST")
    if not host:
        log.info("SMTP_HOST not set: email to %s not sent (%s)", to, subject)
        return False
    msg = EmailMessage()
    msg["From"] = os.environ.get("SMTP_FROM", "Running Analyzer <noreply@localhost>")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if port == 587:
                smtp.starttls()
            user = os.environ.get("SMTP_USER")
            if user:
                smtp.login(user, os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException):
        log.exception("could not send email to %s (%s)", to, subject)
        return False


def analysis_ready(to: str, session_id: str, recorded_on: str, speed_kmh: float) -> bool:
    return send(to, "Your running analysis is ready", (
        f"The analysis of your run of {recorded_on} at {speed_kmh:g} km/h is ready:\n\n"
        f"{web_url(f'/sessions/{session_id}')}\n\n"
        "You can turn these emails off in your profile.\n"
    ))


def analysis_failed(to: str, session_id: str, recorded_on: str, reason: str | None, ask_to_send: bool = False) -> bool:
    """`ask_to_send`: the failure may be our mistake, so the Session page offers to send the Videos to
    the team (a Failure Report); without an answer they are deleted after 7 days."""
    why = FAILURE_TEXT.get(reason or "", reason or "unknown reason")
    session_url = web_url(f"/sessions/{session_id}")
    if ask_to_send:
        ask = ("Something went wrong on our side. Send your videos to our team so we can fix it" if reason == "internal_error"
               else "Think your video was fine? Send it to our team and we'll take a look")
        ask = f"{ask}: {session_url} (within 7 days; after that the videos are deleted).\n\n"
    else:
        ask = ""
    return send(to, "We could not analyze your run", (
        f"We could not analyze the videos of your run of {recorded_on}.\n\n{why}\n\n{ask}"
        f"Details: {session_url}\n"
        f"Record again: {web_url('/sessions/new')}\n"
    ))


def failure_report_opened(to: str, session_id: str, reason: str | None) -> bool:
    """To each Admin when a Runner sends the Videos of a failed Analysis to the team."""
    return send(to, f"Failure Report: {reason or 'unknown reason'}", (
        f"A failed Analysis was sent to the team ({reason}).\n\n"
        f"Session {session_id}: {web_url('/admin?tab=failed')}\n\n"
        "Re-analyze it once fixed, or mark it resolved. Its videos are deleted after 90 days in any case.\n"
    ))


def account_deleted(to: str) -> bool:
    return send(to, "Your Running Analyzer account was deleted", (
        "Your account, your profile, your sessions, videos and analyses have been deleted.\n\n"
        "Encrypted backups are overwritten within 30 days. If you did not ask for this, reply to this email.\n"
    ))
