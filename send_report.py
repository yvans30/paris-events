#!/usr/bin/env python3
"""Reads events JSON from stdin and sends an HTML email via Gmail SMTP."""
import json
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


COLORS = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6"]
TYPE_EMOJIS = {
    "meetup": "🤝", "conference": "🎤", "hackathon": "💻",
    "workshop": "🛠️", "networking": "🤝", "afterwork": "🍻", "talk": "🎙️",
}


def load_config(path="config.json"):
    with open(path) as f:
        return json.load(f)


def fmt_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m")
    except Exception:
        return iso


def generate_html(events, date_from, date_to):
    df = fmt_date(date_from)
    dt = fmt_date(date_to)
    today = datetime.now().strftime("%d/%m/%Y")

    html = f"""<!DOCTYPE html><html lang="fr">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;color:#222;background:#f9f9f9;padding:20px;">
<div style="background:#1a1a2e;color:white;padding:24px 28px;border-radius:10px 10px 0 0;">
  <h1 style="margin:0;font-size:22px;">🗓️ Événements Tech &amp; Finance — Paris</h1>
  <p style="margin:6px 0 0;font-size:15px;color:#aac4ff;">Semaine du {df} au {dt}</p>
</div>
<div style="background:white;border-radius:0 0 10px 10px;padding:24px 28px;">
"""

    if not events:
        html += """<p style="color:#666;">Aucun événement tech/finance pertinent trouvé à Paris pour cette période.
Je réessaierai la semaine prochaine.</p>"""
    else:
        for i, ev in enumerate(events):
            color = COLORS[i % len(COLORS)]
            event_type = ev.get("type", "").lower()
            emoji = next((v for k, v in TYPE_EMOJIS.items() if k in event_type), "📅")
            url = ev.get("url", "#")
            venue_line = " — ".join(filter(None, [ev.get("venue"), ev.get("address")]))
            desc = ev.get("description", "").strip()

            html += f"""
<div style="border-left:4px solid {color};padding-left:16px;margin-bottom:28px;">
  <h2 style="margin:0 0 6px;font-size:17px;">
    {emoji} <a href="{url}" style="color:{color};text-decoration:none;">{ev['title']}</a>
  </h2>
  <table style="font-size:14px;border-collapse:collapse;width:100%;">
    <tr><td style="padding:3px 10px 3px 0;color:#666;white-space:nowrap;"><strong>📅 Date</strong></td>
        <td>{fmt_date(ev.get('date',''))} à {ev.get('time','?')}</td></tr>
    <tr><td style="padding:3px 10px 3px 0;color:#666;"><strong>📍 Lieu</strong></td>
        <td>{venue_line}</td></tr>
    <tr><td style="padding:3px 10px 3px 0;color:#666;"><strong>🏷️ Type</strong></td>
        <td>{ev.get('type','')}</td></tr>
    <tr><td style="padding:3px 10px 3px 0;color:#666;"><strong>💶 Prix</strong></td>
        <td>{ev.get('price','?')}</td></tr>
    <tr><td style="padding:3px 10px 3px 0;color:#666;"><strong>📝 Description</strong></td>
        <td>{desc}</td></tr>
  </table>
</div>
<hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
"""

    html += f"""
  <p style="font-size:12px;color:#999;text-align:center;">
    Rapport généré automatiquement le {today} — Paris Events Weekly
  </p>
</div>
</body>
</html>"""
    return html


def send_email(recipients, subject, html_body):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        print("[ERROR] GMAIL_USER ou GMAIL_APP_PASSWORD non défini.", file=sys.stderr)
        sys.exit(1)

    if not recipients:
        print("[ERROR] GMAIL_RECIPIENTS non défini ou vide.", file=sys.stderr)
        sys.exit(1)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, msg.as_string())

    print(f"[OK] Email envoyé à : {', '.join(recipients)}", file=sys.stderr)


def main():
    config = load_config()

    raw = sys.stdin.read().strip()
    events = json.loads(raw) if raw else []

    today = datetime.now()
    date_from = events[0]["date"] if events else today.strftime("%Y-%m-%d")
    date_to = events[-1]["date"] if events else (today + timedelta(days=14)).strftime("%Y-%m-%d")

    date_from_fmt = fmt_date(date_from)
    subject = f"Evenements Tech & Finance Paris - Semaine du {date_from_fmt}"
    html_body = generate_html(events, date_from, date_to)

    raw_recipients = os.environ.get("GMAIL_RECIPIENTS", "")
    recipients = [r.strip() for r in raw_recipients.split(",") if r.strip()]
    send_email(recipients, subject, html_body)


if __name__ == "__main__":
    main()
