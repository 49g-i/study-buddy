from flask import Flask, render_template, request, redirect, url_for, session, g
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import sys
import os

online_users = set()

# ----------------- CONFIG -----------------
DB_NAME = "studybuddy.db"

app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app)


# ----------------- DB UTILITIES -----------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            subjects TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()


# ----------------- DB HELPERS -----------------
def save_user(name, email, subjects):
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO users (name, email, subjects) VALUES (?, ?, ?)",
        (name, email, subjects),
    )
    db.commit()


def get_user_by_email(email):
    cur = get_db().execute(
        "SELECT name, email, subjects FROM users WHERE email = ?", (email,)
    )
    return cur.fetchone()


def get_all_users():
    cur = get_db().execute("SELECT name, email, subjects FROM users")
    return cur.fetchall()


def save_message(sender, receiver, content):
    db = get_db()
    db.execute(
        "INSERT INTO messages (sender, receiver, content) VALUES (?, ?, ?)",
        (sender, receiver, content),
    )
    db.commit()


def load_messages_between(user1, user2):
    cur = get_db().execute(
        """
        SELECT sender, receiver, content, timestamp
        FROM messages
        WHERE (sender = ? AND receiver = ?)
           OR (sender = ? AND receiver = ?)
        ORDER BY timestamp ASC
        """,
        (user1, user2, user2, user1),
    )
    return cur.fetchall()


# ----------------- ROUTES -----------------
@app.route("/")
def index():
    if "email" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        subjects = ",".join(request.form.getlist("subjects"))

        save_user(name, email, subjects)
        session["email"] = email
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
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

@app.route("/lobby")
def lobby():
    if "email" not in session:
        return redirect(url_for("login"))
    users = get_all_users()
    # decorate each user with .online boolean
    user_objs = []
    for u in users:
        user_objs.append({
            "name": u[0],
            "email": u[1],
            "subjects": u[2].split(","),
            "online": u[1] in online_users
        })
    return render_template("lobby.html", users=user_objs, me=session["email"])



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
    email = data.get("email")
    if email:
        online_users.add(email)
        # broadcast updated list
        emit("user_list", {"users": list(online_users)}, broadcast=True)

@socketio.on("disconnect")
def on_disconnect():
    # try to remove user on disconnect
    email = session.get("email")
    if email in online_users:
        online_users.remove(email)
        emit("user_list", {"users": list(online_users)}, broadcast=True)



# ----------------- MAIN -----------------
if __name__ == "__main__":
    if not os.path.exists(DB_NAME):
        with app.app_context():
            init_db()

    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    socketio.run(app, host="127.0.0.1", port=port, debug=True)
