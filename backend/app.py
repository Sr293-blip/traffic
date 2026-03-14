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
            email TEXT
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
    sender_email = "your_email@gmail.com"          # Replace with your email
    sender_password = "your_app_password"          # Use Gmail App Password

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
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# ---------------- AUTH ----------------

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
    email = request.form.get("email")  # Add email field in signup form

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users(username,password,email) VALUES(?,?,?)",
                (username, password, email)
            )
        return redirect("/?signup=success")
    except sqlite3.IntegrityError:
        return redirect("/signup-page")  # username already exists
    except Exception as e:
        print(f"Signup Error: {e}")
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
    return "Invalid login"

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

@app.route("/traffic-analytics")
def traffic_analytics():
    if "user" not in session:
        return redirect("/")
    return render_template("analytics.html")

@app.route("/analysis-result")
def analysis_result():
    if "user" not in session:
        return redirect("/")
    return render_template("analysis_result.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# ---------------- TRAFFIC ANALYSIS ----------------

traffic_history = []

@app.route("/analyze", methods=["POST"])
def analyze():
    video = "traffic.mp4"

    # YOLO vehicle detection
    congestion = detect_congestion(video)

    # Convert congestion → vehicle count
    if congestion == "LOW":
        vehicle_count = 10
    elif congestion == "MEDIUM":
        vehicle_count = 25
    else:
        vehicle_count = 50

    # Accident detection
    accident = detect_accident(vehicle_count)

    # RL route decision
    route = route_decision(congestion)
    suggestion = "Normal Route Recommended"
    if route == "ALTERNATE_ROUTE":
        suggestion = "Heavy Traffic Detected. Take Alternate Route"

    # Save traffic history
    traffic_history.append(vehicle_count)
    if len(traffic_history) > 10:
        traffic_history.pop(0)

    # LSTM congestion prediction (convert numeric to words)
    prediction_word = "Not enough data"
    if len(traffic_history) == 10:
        prediction_value = predict_congestion(traffic_history)
        if prediction_value < 20:
            prediction_word = "LOW"
        elif prediction_value < 40:
            prediction_word = "MEDIUM"
        else:
            prediction_word = "HIGH"

    # Save to database and fetch user email
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO traffic_logs(time, congestion, vehicle_count) VALUES(?,?,?)",
                (str(datetime.datetime.now()), congestion, vehicle_count)
            )
            row = conn.execute(
                "SELECT email FROM users WHERE username=?", (session["user"],)
            ).fetchone()
            user_email = row["email"] if row and "email" in row.keys() else None
    except Exception as e:
        print(f"DB Error: {e}")
        user_email = None

    # Send alert email if accident occurs or congestion is high
    if user_email and (accident or congestion == "HIGH"):
        send_email_alert(
            to_email=user_email,
            subject="🚨 Smart Traffic Alert",
            message=f"""
Traffic Alert!

Traffic Status : {congestion}
Vehicle Count  : {vehicle_count}
Accident Detected : {'Yes' if accident else 'No'}
Route Suggestion : {suggestion}

Stay safe!
"""
        )

    return jsonify({
        "congestion": congestion,
        "vehicle_count": vehicle_count,
        "prediction": prediction_word,
        "accident": accident,
        "route": route,
        "suggestion": suggestion
    })

# ---------------- GRAPH DATA API ----------------

@app.route("/analytics")
def analytics():
    with get_db() as conn:
        data = conn.execute(
            "SELECT time, vehicle_count FROM traffic_logs ORDER BY id DESC LIMIT 20"
        ).fetchall()

    times = [row["time"][-8:] for row in reversed(data)]
    counts = [row["vehicle_count"] for row in reversed(data)]

    return jsonify({"times": times, "counts": counts})

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)