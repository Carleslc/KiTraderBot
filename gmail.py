import os
import email
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

try:
    with open("tokens/gmail", 'rb') as gmail_token:
        GMAIL_TOKEN = decrypt(gmail_token.read().strip()).strip()

    with open("tokens/gmail_at", 'r') as gmail:
        GMAIL_MAIL = gmail.read().strip()
except FileNotFoundError:
    print("Alerts from Gmail are disabled")
    ENABLED = False

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
        print(datetime.now(TIMEZONE))
        print(f"Logging to mail ({INBOX})...")
        mail = IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(GMAIL_MAIL, GMAIL_TOKEN)
        mail.select(INBOX)

def __read_alert(id):
    _, data = mail.uid('fetch', id, 'BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)]')
    msg = email.message_from_string(data[0][1].decode('utf-8'))
    subject = msg['subject'].replace(PREFIX, '', 1).replace('\r\n', '')
    date = datetime.strptime(msg['date'], DATE_TIME_FORMAT)
    return subject, date

def last_alert(maxHours=8):
    if not ENABLED:
        return None
    
    minTime = datetime.now(TIMEZONE) - timedelta(hours=maxHours)

    if os.path.isfile('lastAlert'):
        with open('lastAlert', 'r') as lastAlertFile:
            lastAlert = lastAlertFile.read()
            lastAlertDate = datetime.strptime(lastAlert.split(' -> ', 1)[0], DATE_TIME_FORMAT).astimezone(TIMEZONE)
    else:
        lastAlertDate = minTime

    lastAlertDate = max(lastAlertDate, minTime)
    print(f"Fetching new alerts since {lastAlertDate}")

    since = lastAlertDate.strftime(DATE_FORMAT)
    _, data = mail.search(None, r'(SENTSINCE {date}) (FROM "noreply@tradingview.com") (X-GM-RAW "subject:\"{prefix}\"")'.format(date=since, prefix=PREFIX))
    mail_ids = data[0].split()

    alerts = len(mail_ids)

    if alerts > 0:
        subject, newLastAlertDate = __read_alert(mail_ids[-1])
        if newLastAlertDate != lastAlertDate and newLastAlertDate > lastAlertDate:
            alertParts = subject.split()
            alertText = f'{alertParts[0].upper()} {' '.join(alertParts[1:]}'
            alert = f'{newLastAlertDate.astimezone(TIMEZONE).strftime(DATE_TIME_FORMAT)} -> {alertText}'
            with open('lastAlert', 'w') as lastAlertFile:
                lastAlertFile.write(alert)
            return alertText

    print('Alerts are up to date')
    return None

def logout():
    if mail is not None:
        mail.close()

if __name__ == '__main__':
    login()
    last_alert()
    logout()