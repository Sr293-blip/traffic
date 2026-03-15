from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# AI Modules
from vehicle_detection import detect_congestion
from accident_detection import detect_accident
from congestion_prediction import predict_congestion
from rl_agent import route_decision

app = Flask(__name__)
app.secret_key = "traffic_secret"

DATABASE = "users.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:

        conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            phone TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS traffic_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            congestion TEXT,
            vehicle_count INTEGER
        )
        """)

init_db()


# ---------------- EMAIL ALERT ----------------

def send_email_alert(to_email, subject, message):

    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'plain'))

    try:

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        server.send_message(msg)
        server.quit()

        print("Email sent successfully")

    except Exception as e:

        print("Email Error:", e)


# ---------------- FREE SMS ALERT ----------------

def send_sms_alert(phone, message):

    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password"

    sms_gateway = phone + "@airtelmail.com"

    msg = MIMEText(message)

    msg["From"] = sender_email
    msg["To"] = sms_gateway

    try:

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        server.sendmail(sender_email, sms_gateway, msg.as_string())

        server.quit()

        print("SMS sent to:", phone)

    except Exception as e:

        print("SMS Error:", e)


# ---------------- AUTH ROUTES ----------------

@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/signup-page")
def signup_page():
    return render_template("signup.html")


@app.route("/signup", methods=["POST"])
def signup():

    username = request.form.get("username")
    password = request.form.get("password")
    email = request.form.get("email")
    phone = request.form.get("phone")

    try:

        with get_db() as conn:

            conn.execute(
                "INSERT INTO users(username,password,email,phone) VALUES(?,?,?,?)",
                (username, password, email, phone)
            )

        return redirect("/?signup=success")

    except:
        return redirect("/signup-page")


@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username")
    password = request.form.get("password")

    with get_db() as conn:

        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

    if user:

        session["user"] = username
        return redirect("/index")

    return "Invalid Login"


@app.route("/index")
def index():

    if "user" not in session:
        return redirect("/")

    return render_template("index.html")


@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    return render_template("dashboard.html")


@app.route("/analysis-result")
def analysis_result():

    if "user" not in session:
        return redirect("/")

    return render_template("analysis_result.html")


@app.route("/traffic-analytics")
def traffic_analytics():

    if "user" not in session:
        return redirect("/")

    return render_template("analytics.html")


@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/")


# ---------------- TEST SMS ----------------

@app.route("/test-user-sms")
def test_user_sms():

    with get_db() as conn:

        row = conn.execute(
            "SELECT phone FROM users WHERE username=?",
            (session["user"],)
        ).fetchone()

    if row:

        send_sms_alert(row["phone"], "Test SMS from Smart Traffic System")

    return "SMS sent to logged-in user"


# ---------------- TRAFFIC ANALYSIS ----------------

traffic_history = []

@app.route("/analyze", methods=["POST"])
def analyze():

    video = "traffic.mp4"

    congestion = detect_congestion(video)

    vehicle_count = 10 if congestion == "LOW" else 25 if congestion == "MEDIUM" else 50

    accident = detect_accident(vehicle_count)

    route = route_decision(congestion)

    suggestion = "Normal Route Recommended"

    traffic_history.append(vehicle_count)

    if len(traffic_history) > 10:
        traffic_history.pop(0)

    prediction_word = "NONE"

    if len(traffic_history) == 10:

        prediction_value = predict_congestion(traffic_history)

        if prediction_value < 20:

            prediction_word = "LOW"

        elif prediction_value < 40:

            prediction_word = "MEDIUM"

        else:

            prediction_word = "HIGH"
            suggestion = "Alternate Route Recommended"


    # Save traffic log and get user info

    user_email = None
    user_phone = None

    with get_db() as conn:

        conn.execute(
            "INSERT INTO traffic_logs(time, congestion, vehicle_count) VALUES(?,?,?)",
            (str(datetime.datetime.now()), congestion, vehicle_count)
        )

        row = conn.execute(
            "SELECT email,phone FROM users WHERE username=?",
            (session["user"],)
        ).fetchone()

        if row:

            user_email = row["email"]
            user_phone = row["phone"]


    alert_message = f"""
Traffic Alert

Traffic Level : {congestion}
Vehicle Count : {vehicle_count}
Prediction : {prediction_word}
Route : {suggestion}
"""


    # Send email alert every time

    if user_email:

        send_email_alert(
            user_email,
            f"🚦 Traffic Alert - {congestion}",
            alert_message
        )


    # Send SMS alert every time

    if user_phone:

        send_sms_alert(
            user_phone,
            alert_message
        )


    return jsonify({
        "congestion": congestion,
        "vehicle_count": vehicle_count,
        "prediction": prediction_word,
        "suggestion": suggestion
    })


# ---------------- ANALYTICS GRAPH ----------------

@app.route("/analytics")
def analytics():

    with get_db() as conn:

        data = conn.execute(
            "SELECT time,vehicle_count FROM traffic_logs ORDER BY id DESC LIMIT 20"
        ).fetchall()

    times = [row["time"][-8:] for row in reversed(data)]
    counts = [row["vehicle_count"] for row in reversed(data)]

    return jsonify({
        "times": times,
        "counts": counts
    })


# ---------------- RUN ----------------

if __name__ == "__main__":

    app.run(debug=True)