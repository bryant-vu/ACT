"""Outgoing email for "Request Login Info".

Sends through SMTP (for example Gmail with an App Password) using the config
vars SMTP_USER, SMTP_PASSWORD, and optionally SMTP_HOST / SMTP_PORT / MAIL_FROM.
Without SMTP_PASSWORD it is a dry run: the message is printed to the server
console and nothing is sent.
"""
import html
import os
import re
import smtplib
import ssl
from email.message import EmailMessage

import certifi

import auth


def _one_line(text, limit=200):
    return re.sub(r'[\r\n\x00-\x1f]+', ' ', text or '').strip()[:limit]


LOGO_PATH = os.path.join(auth.BASE, 'static', 'img', 'bvuedulogo_email.png')


def send(to, subject, body, reply_to=None, html_body=None):
    """True if the message was handed to the mail server (or dry-run printed).

    html_body, if given, is sent as the HTML version (plain `body` stays as the
    fallback) and may show the logo with <img src="cid:logo">."""
    cfg = auth.CONFIG
    sender = cfg.get('MAIL_FROM') or cfg.get('SMTP_USER') or 'login@localhost'
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = _one_line(to)
    msg['Subject'] = _one_line(subject, 120)
    if reply_to:
        msg['Reply-To'] = _one_line(reply_to)
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')
        try:
            with open(LOGO_PATH, 'rb') as f:
                msg.get_payload()[1].add_related(f.read(), 'image', 'png', cid='<logo>', filename='bvuedu-logo.png')
        except OSError as e:
            print('logo not attached:', e, flush=True)
    if not cfg.get('SMTP_PASSWORD'):
        print(f'--- DRY RUN email (nothing sent) ---\nTo: {msg["To"]}\nSubject: {msg["Subject"]}'
              f'\nReply-To: {msg.get("Reply-To", "")}\n\n{body}\n--- end ---', flush=True)
        return True
    try:
        host, port = cfg.get('SMTP_HOST', 'smtp.gmail.com'), int(cfg.get('SMTP_PORT', '587'))
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context(cafile=certifi.where()))
            smtp.login(cfg.get('SMTP_USER', sender), re.sub(r'\s+', '', cfg['SMTP_PASSWORD']))  # Google shows it in groups with spaces
            smtp.send_message(msg)
        return True
    except Exception as e:   # noqa: BLE001
        print('email failed:', e, flush=True)
        return False


SIGNATURE = """All the best,
Bryant

C: (714) 507-5912
W: www.bvuedu.com
A: 5151 California Ave Irvine, CA, 92617"""


def _signature_html():
    # "All the best, Bryant" lines up with the email body; the logo sits left of the C / W / A lines
    return (
        '<p style="margin:18px 0 0">All the best,<br>Bryant</p>'
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:14px"><tr>'
        '<td style="padding-right:12px;vertical-align:middle">'
        '<img src="cid:logo" width="66" height="66" alt="BVU EDU" style="display:block;border:0"></td>'
        '<td style="vertical-align:middle;font:14px/1.5 Arial,Helvetica,sans-serif;color:#333">'
        'C: (714) 507-5912<br>'
        'W: <a href="https://www.bvuedu.com" style="color:#2f5597">www.bvuedu.com</a><br>'
        'A: 5151 California Ave Irvine, CA, 92617</td></tr></table>')


def send_login_info(to, logins, password):
    """logins: [(TutorBird name, login ID), ...]. More than one when a parent's
    address is on file for several students."""
    if len(logins) == 1:
        name, login = logins[0]
        first = name.split()[0].strip('(“”") ') if name.split() else 'there'
        who = f"ID: {login}\n"
        hi = f"Hi {first},"
    else:
        who = ''.join(f"{name}: ID {login}\n" for name, login in logins)
        hi = 'Hi,'
    body = (f"{hi}\n\nHere is the login for the ACT math practice site.\n\n"
            f"{who}Password: {password}\n\n"
            "Type the ID exactly as shown (the full name with no spaces; capitals don't matter). "
            "You'll stay logged in on that device for months.\n\n"
            "If you didn't ask for this, you can ignore this email.\n\n" + SIGNATURE)
    esc = html.escape
    rows = ''.join(f'<li><b>{esc(n)}</b>: ID <b>{esc(l)}</b></li>' for n, l in logins) if len(logins) > 1 else \
        f'<p style="margin:0">ID: <b>{esc(logins[0][1])}</b></p>'
    if len(logins) > 1:
        rows = f'<ul style="margin:0 0 0 18px;padding:0">{rows}</ul>'
    html_body = (
        '<div style="font:15px/1.5 Arial,Helvetica,sans-serif;color:#222;max-width:520px">'
        f'<p>{esc(hi)}</p><p>Here is the login for the ACT math practice site.</p>'
        f'<div style="background:#f4f6fa;border-radius:8px;padding:12px 16px;margin:12px 0">{rows}'
        f'<p style="margin:6px 0 0">Password: <b>{esc(password)}</b></p></div>'
        "<p>Type the ID exactly as shown (the full name with no spaces; capitals don't matter). "
        "You'll stay logged in on that device for months.</p>"
        "<p style=\"color:#666\">If you didn't ask for this, you can ignore this email.</p>"
        + _signature_html() + '</div>')
    return send(to, 'Your ACT practice site login', body, html_body=html_body)


def notify_owner(typed_name, typed_email, match, reason):
    typed_name, typed_email = typed_name or '(blank)', typed_email or '(blank)'
    to = auth.CONFIG.get('NOTIFY_TO')
    if not to:
        print('NOTIFY_TO is not set; login request not forwarded', flush=True)
        return False
    closest = (f"{match['name']} ({match['role']}, {int(match['score'] * 100)}% match)"
               if match else 'no close match in the roster')
    body = (f"Someone asked for login info on the ACT site and it could not be sent automatically.\n\n"
            f"They typed: {_one_line(typed_name)}\nTheir email: {_one_line(typed_email)}\n"
            f"Closest roster name: {closest}\nWhy it wasn't sent: {reason}\n\n"
            "Reply to this email to answer them directly.")
    return send(to, f'Login request: {_one_line(typed_name, 60)}', body, reply_to=typed_email if '@' in typed_email else None)
