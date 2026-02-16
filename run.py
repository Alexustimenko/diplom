from flask import Flask, render_template, session
from dotenv import load_dotenv
from app.routes.auth import auth_bp

load_dotenv()

app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
app.secret_key = "supersecretkey"

app.register_blueprint(auth_bp)

@app.route("/")
def home():
    return render_template(
        "home.html",
        is_logged_in=("user_id" in session),
        is_admin=(session.get("is_admin") == 1),
        email=session.get("email"),
    )

if __name__ == "__main__":
    app.run(debug=True)
