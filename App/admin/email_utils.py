from flask import Flask
from flask_mail import Mail, Message
import os

mail = Mail()

def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config.from_pyfile(os.path.join(basedir, 'config.py'))
    mail.init_app(app)
    return app

def send_reset_email(to_email, token):
    app = create_app()
    with app.app_context():
        reset_link = f"http://localhost:2002/admin/reset-password/{token}"
        msg = Message(
            subject="Password Reset Request",
            recipients=[to_email],
            html=f"""
            <h2>Password Reset Request</h2>
            <p>You requested to reset your password. Click the link below to proceed:</p>
            <p><a href="{reset_link}">{reset_link}</a></p>
            <p>If you didn't request this, please ignore this email.</p>
            <p>This link will expire in 1 hour.</p>
            """
        )
        mail.send(msg)