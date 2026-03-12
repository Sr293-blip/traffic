from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import datetime

# AI Modules
from vehicle_detection import detect_congestion
from accident_detection import detect_accident
from congestion_prediction import predict_congestion
from email_alert import send_email
from rl_agent import route_decision

app = Flask(__name__)
app.secret_key = "traffic_secret"

DATABASE = "users.db"

# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
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

    conn.commit()
    conn.close()

init_db()

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

    conn = get_db()

    try:
        conn.execute(
            "INSERT INTO users(username,password) VALUES(?,?)",
            (username, password)
        )
        conn.commit()

        return redirect("/?signup=success")

    except:
        return redirect("/signup-page")

    finally:
        conn.close()


@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username")
    password = request.form.get("password")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()

    conn.close()

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

    if accident:
        send_email(
            "authority@email.com",
            "🚨 Accident Alert",
            f"""
Possible accident detected!

Traffic Status : {congestion}
Vehicle Count  : {vehicle_count}

Location: Smart Traffic Junction
Immediate attention required.
"""
        )

    # Save traffic history
    traffic_history.append(vehicle_count)

    if len(traffic_history) > 10:
        traffic_history.pop(0)

    # LSTM congestion prediction
    prediction = None

    if len(traffic_history) == 10:
        prediction = predict_congestion(traffic_history)

    # RL route decision
    route = route_decision(congestion)

    suggestion = "Normal Route Recommended"

    if route == "ALTERNATE_ROUTE":
        suggestion = "Heavy Traffic Detected. Take Alternate Route"

    # Save to database
    conn = get_db()

    conn.execute(
        "INSERT INTO traffic_logs(time, congestion, vehicle_count) VALUES(?,?,?)",
        (
            str(datetime.datetime.now()),
            congestion,
            vehicle_count
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "congestion": congestion,
        "vehicle_count": vehicle_count,
        "prediction": str(prediction),
        "accident": accident,
        "route": route,
        "suggestion": suggestion
    })


# ---------------- GRAPH DATA API ----------------

@app.route("/analytics")
def analytics():

    conn = get_db()

    data = conn.execute(
        "SELECT time, vehicle_count FROM traffic_logs ORDER BY id DESC LIMIT 20"
    ).fetchall()

    conn.close()

    times = []
    counts = []

    for row in reversed(data):
        times.append(row["time"][-8:])
        counts.append(row["vehicle_count"])

    return jsonify({
        "times": times,
        "counts": counts
    })


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)