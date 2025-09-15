from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# database setup
def init_db():
    conn = sqlite3.connect("studybuddy.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        courses TEXT
    )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        courses = request.form["courses"]

        conn = sqlite3.connect("studybuddy.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO users (name, email, courses) VALUES (?, ?, ?)", 
                    (name, email, courses))
        conn.commit()
        conn.close()

        return redirect(url_for("buddies", email=email))
    return render_template("signup.html")

@app.route("/buddies/<email>")
def buddies(email):
    conn = sqlite3.connect("studybuddy.db")
    cur = conn.cursor()
    cur.execute("SELECT courses FROM users WHERE email=?", (email,))
    my_courses = cur.fetchone()[0].split(",")

    cur.execute("SELECT name, email, courses FROM users WHERE email != ?", (email,))
    others = cur.fetchall()

    matches = []
    for name, other_email, courses in others:
        overlap = set(my_courses) & set(courses.split(","))
        if overlap:
            matches.append((name, other_email, ", ".join(overlap)))

    conn.close()
    return render_template("buddies.html", matches=matches)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
