import os
import email
import logging

from pytz import timezone
from imaplib import IMAP4_SSL
from datetime import datetime, timedelta
from Crypto.Cipher import AES

def decrypt(ciphertext):
    iv = ciphertext[:AES.block_size]
    cipher = AES.new(b'038,6gb(dHhjf-0L', AES.MODE_CBC, iv)
    plaintext = cipher.decrypt(ciphertext[AES.block_size:])
    return plaintext.rstrip(b"\0").decode('utf8')

ENABLED = True
DEBUG = False

try:
    with open("tokens/gmail", 'rb') as gmail_token:
        GMAIL_TOKEN = decrypt(gmail_token.read().strip()).strip()

    with open("tokens/gmail_at", 'r') as gmail:
        GMAIL_MAIL = gmail.read().strip()
except FileNotFoundError:
    ENABLED = False
    logging.warn("Alerts from Gmail are disabled")

TIMEZONE = timezone('Europe/Madrid')
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
INBOX = "Trading"
PREFIX = "Alerta: "

DATE_FORMAT = "%d-%b-%Y"
DATE_TIME_FORMAT = "%a, %d %b %Y %H:%M:%S %z"

def login():
    global mail
    if ENABLED:
        logging.info(f"Logging to mail ({INBOX})...")
        try:
            mail = IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(GMAIL_MAIL, GMAIL_TOKEN)
            mail.select(INBOX)
        except Exception as e:
            logging.warn("Cannot login")
            logout()
            raise e

def logout():
    global mail
    if mail is not None:
        mail.close()
        mail.logout()
        mail = None

def __read_alert(mail_id):
    global mail
    _, data = mail.uid('fetch', mail_id, 'BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)]')
    msg = email.message_from_string(data[0][1].decode('utf-8'))
    subject = msg['subject'].replace(PREFIX, '', 1).replace('\r\n', '')
    date = datetime.strptime(msg['date'], DATE_TIME_FORMAT)
    return subject, date

def get_last_alert_date():
    if os.path.isfile('lastAlert'):
        with open('lastAlert', 'r') as lastAlertFile:
            lastAlert = lastAlertFile.read()
            lastAlertDate = datetime.strptime(lastAlert.split(' -> ', 1)[0], DATE_TIME_FORMAT).astimezone(TIMEZONE)
            return lastAlertDate
    return None

def update_alerts(maxHours=24):
    global mail

    if not ENABLED:
        return None

    print(f"{datetime.now(TIMEZONE).strftime(DATE_TIME_FORMAT)} - Update last alert")

    lastAlertDate = get_last_alert_date()

    if not lastAlertDate:
        lastAlertDate = datetime.now(TIMEZONE) - timedelta(hours=maxHours)
    
    login()

    since = lastAlertDate.strftime(DATE_FORMAT)
    _, data = mail.search(None, r'(SENTSINCE {date}) (FROM "noreply@tradingview.com") (X-GM-RAW "subject:\"{prefix}\"")'.format(date=since, prefix=PREFIX))
    mail_ids = data[0].split()

    alerts = []

    for mail_id in mail_ids:
        subject, alertDate = __read_alert(mail_id)
        if alertDate > lastAlertDate:
            alertParts = subject.split()
            alertText = f"{alertParts[0].upper()} {' '.join(alertParts[1:])}"
            alerts.append((alertDate, alertText))
            newAlert = f'{alertDate.astimezone(TIMEZONE).strftime(DATE_TIME_FORMAT)} -> {alertText}'
            print(newAlert)
    
    logout()
    
    if alerts:
        with open('lastAlert', 'w') as lastAlertFile:
            lastAlertFile.write(newAlert)
    
    return alerts

if __name__ == '__main__':
    update_alerts()
