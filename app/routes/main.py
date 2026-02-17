from flask import Flask
from app.routes.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = "CHANGE_ME_SECRET_KEY"

    app.register_blueprint(auth_bp)

    return app
