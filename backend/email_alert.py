import smtplib
from email.mime.text import MIMEText

SENDER = "yourprojectmail@gmail.com"
PASSWORD = "your_app_password"

def send_email(to, subject, message):
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = to

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(SENDER, PASSWORD)
    server.send_message(msg)
    server.quit()