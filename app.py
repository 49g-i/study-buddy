from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app)

# ----------------- DB INIT -----------------
def init_db():
    conn = sqlite3.connect("studybuddy.db")
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            subjects TEXT NOT NULL
        )
    """)

    # Messages table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ----------------- DB HELPERS -----------------
def save_user(name, email, subjects):
    conn = sqlite3.connect("studybuddy.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (name, email, subjects) VALUES (?, ?, ?)",
                (name, email, subjects))
    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = sqlite3.connect("studybuddy.db")
    cur = conn.cursor()
    cur.execute("SELECT name, email, subjects FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    return row


def get_all_users():
    conn = sqlite3.connect("studybuddy.db")
    cur = conn.cursor()
    cur.execute("SELECT name, email, subjects FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows


def save_message(sender, receiver, content):
    conn = sqlite3.connect("studybuddy.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO messages (sender, receiver, content) VALUES (?, ?, ?)",
                (sender, receiver, content))
    conn.commit()
    conn.close()


def load_messages_between(user1, user2):
    conn = sqlite3.connect("studybuddy.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT sender, receiver, content, timestamp
        FROM messages
        WHERE (sender = ? AND receiver = ?)
           OR (sender = ? AND receiver = ?)
        ORDER BY timestamp ASC
    """, (user1, user2, user2, user1))
    rows = cur.fetchall()
    conn.close()
    return rows


# ----------------- ROUTES -----------------
@app.route("/")
def index():
    if "email" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        subjects = ",".join(request.form.getlist("subjects"))
        save_user(name, email, subjects)
        session["email"] = email
        return redirect(url_for("dashboard"))
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        user = get_user_by_email(email)
        if user:
            session["email"] = email
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("email", None)
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        return redirect(url_for("login"))
    users = get_all_users()
    return render_template("dashboard.html", users=users, me=session["email"])


@app.route("/chat/<other_email>")
def chat(other_email):
    if "email" not in session:
        return redirect(url_for("login"))
    me = session["email"]
    msgs = load_messages_between(me, other_email)
    return render_template("chat.html", messages=msgs, me=me, other=other_email)


# ----------------- SOCKET EVENTS -----------------
@socketio.on("send_message")
def handle_message(data):
    sender = data["sender"]
    receiver = data["receiver"]
    content = data["content"]

    save_message(sender, receiver, content)

    room = "_".join(sorted([sender, receiver]))
    emit("receive_message", {"sender": sender, "content": content}, room=room)


@socketio.on("join")
def on_join(data):
    user = data["user"]
    other = data["other"]
    room = "_".join(sorted([user, other]))
    join_room(room)


@socketio.on("leave")
def on_leave(data):
    user = data["user"]
    other = data["other"]
    room = "_".join(sorted([user, other]))
    leave_room(room)


# ----------------- MAIN -----------------
if __name__ == "__main__":
    init_db()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
