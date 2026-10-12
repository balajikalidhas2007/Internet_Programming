import os
import sqlite3
import random
from flask import Flask, request, send_file, redirect, url_for

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "train.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "train.html")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_pnr():
    return "PNR" + str(random.randint(10000000, 99999999))


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_number TEXT NOT NULL,
            train_name TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            journey_date TEXT NOT NULL,
            class_type TEXT NOT NULL,
            available_seats INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnr TEXT NOT NULL,
            passenger_name TEXT NOT NULL,
            train_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            journey_date TEXT NOT NULL,
            class_type TEXT NOT NULL,
            passengers INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (train_id) REFERENCES trains(id)
        )
    """)
    # Insert sample trains if table is empty
    cur.execute("SELECT COUNT(*) FROM trains")
    if cur.fetchone()[0] == 0:
        sample = [
            ("12345", "Chennai Express", "Chennai", "Bangalore", "2026-10-20", "Sleeper", 40),
            ("12345", "Chennai Express", "Chennai", "Bangalore", "2026-10-20", "AC 3-Tier", 30),
            ("67890", "Rajdhani Express", "Delhi", "Mumbai", "2026-10-22", "AC 2-Tier", 25),
            ("67890", "Rajdhani Express", "Delhi", "Mumbai", "2026-10-22", "AC 1st Class", 15),
            ("11223", "Coromandel Express", "Chennai", "Kolkata", "2026-10-25", "Sleeper", 50),
            ("44556", "Shatabdi Express", "Bangalore", "Mysore", "2026-10-18", "AC Chair Car", 60),
        ]
        cur.executemany(
            "INSERT INTO trains (train_number, train_name, source, destination, journey_date, class_type, available_seats) VALUES (?, ?, ?, ?, ?, ?, ?)",
            sample,
        )
    conn.commit()
    conn.close()


# ---------- Routes ----------

@app.route("/")
def home():
    return send_file(HTML_PATH)


@app.route("/book", methods=["POST"])
def book_ticket():
    passenger_name = request.form["passenger_name"]
    train_id = int(request.form["train_id"])
    num_passengers = int(request.form["num_passengers"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trains WHERE id = ?", (train_id,))
    train = cur.fetchone()

    if train is None:
        conn.close()
        return "<h3>Error: Train not found.</h3><br><a href='/'>Go Back</a>"

    if train["available_seats"] < num_passengers:
        conn.close()
        return "<h3>Error: Not enough seats available. Only {} seats left.</h3><br><a href='/'>Go Back</a>".format(
            train["available_seats"]
        )

    pnr = generate_pnr()
    cur.execute(
        "INSERT INTO reservations (pnr, passenger_name, train_id, source, destination, journey_date, class_type, passengers, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (pnr, passenger_name, train_id, train["source"], train["destination"],
         train["journey_date"], train["class_type"], num_passengers, "CONFIRMED"),
    )
    cur.execute(
        "UPDATE trains SET available_seats = available_seats - ? WHERE id = ?",
        (num_passengers, train_id),
    )
    conn.commit()
    conn.close()

    return """
    <h2>Ticket Booked Successfully!</h2>
    <p><b>PNR Number: {}</b></p>
    <p>Passenger: {}</p>
    <p>Train: {} - {}</p>
    <p>Route: {} → {}</p>
    <p>Journey Date: {}</p>
    <p>Class: {}</p>
    <p>Passengers: {}</p>
    <p>Status: CONFIRMED</p>
    <br><a href="/">Go Back</a>
    """.format(pnr, passenger_name, train["train_number"], train["train_name"],
               train["source"], train["destination"], train["journey_date"],
               train["class_type"], num_passengers)


@app.route("/pnr", methods=["POST"])
def check_pnr():
    pnr = request.form["pnr"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.*, t.train_number, t.train_name
        FROM reservations r
        JOIN trains t ON r.train_id = t.id
        WHERE r.pnr = ?
    """, (pnr,))
    res = cur.fetchone()
    conn.close()

    if res is None:
        return "<h3>Error: PNR not found.</h3><br><a href='/'>Go Back</a>"

    return """
    <h2>PNR Status</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><td><b>PNR</b></td><td>{}</td></tr>
        <tr><td><b>Passenger</b></td><td>{}</td></tr>
        <tr><td><b>Train</b></td><td>{} - {}</td></tr>
        <tr><td><b>Route</b></td><td>{} → {}</td></tr>
        <tr><td><b>Journey Date</b></td><td>{}</td></tr>
        <tr><td><b>Class</b></td><td>{}</td></tr>
        <tr><td><b>Passengers</b></td><td>{}</td></tr>
        <tr><td><b>Status</b></td><td>{}</td></tr>
    </table>
    <br><a href="/">Go Back</a>
    """.format(res["pnr"], res["passenger_name"], res["train_number"], res["train_name"],
               res["source"], res["destination"], res["journey_date"],
               res["class_type"], res["passengers"], res["status"])


@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM trains")
    trains = cur.fetchall()

    cur.execute("""
        SELECT r.pnr, r.passenger_name, t.train_number, t.train_name,
               r.source, r.destination, r.journey_date, r.class_type,
               r.passengers, r.status
        FROM reservations r
        JOIN trains t ON r.train_id = t.id
    """)
    reservations = cur.fetchall()
    conn.close()

    html = "<h1>Admin Page - Train Reservation System</h1>"

    html += "<h2>Train Information</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>ID</th><th>Train No</th><th>Train Name</th><th>Source</th><th>Destination</th><th>Date</th><th>Class</th><th>Available Seats</th></tr>"
    for t in trains:
        html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            t["id"], t["train_number"], t["train_name"], t["source"],
            t["destination"], t["journey_date"], t["class_type"], t["available_seats"]
        )
    html += "</table>"

    html += "<h2>Reservation Information</h2>"
    if reservations:
        html += "<table border='1' cellpadding='5' cellspacing='0'>"
        html += "<tr><th>PNR</th><th>Passenger</th><th>Train No</th><th>Train Name</th><th>Source</th><th>Destination</th><th>Date</th><th>Class</th><th>Passengers</th><th>Status</th></tr>"
        for r in reservations:
            html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                r["pnr"], r["passenger_name"], r["train_number"], r["train_name"],
                r["source"], r["destination"], r["journey_date"], r["class_type"],
                r["passengers"], r["status"]
            )
        html += "</table>"
    else:
        html += "<p>No reservations yet.</p>"

    html += "<br><hr>"
    html += "<h2>Add New Train</h2>"
    html += """
    <form action="/add_train" method="post">
        Train Number: <input type="text" name="train_number" required><br><br>
        Train Name: <input type="text" name="train_name" required><br><br>
        Source: <input type="text" name="source" required><br><br>
        Destination: <input type="text" name="destination" required><br><br>
        Journey Date: <input type="date" name="journey_date" required><br><br>
        Class Type: <input type="text" name="class_type" required><br><br>
        Available Seats: <input type="number" name="available_seats" required><br><br>
        <input type="submit" value="Add Train">
    </form>
    """
    html += "<br><a href='/'>Go Back to Home</a>"
    return html


@app.route("/add_train", methods=["POST"])
def add_train():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trains (train_number, train_name, source, destination, journey_date, class_type, available_seats) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            request.form["train_number"],
            request.form["train_name"],
            request.form["source"],
            request.form["destination"],
            request.form["journey_date"],
            request.form["class_type"],
            int(request.form["available_seats"]),
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/trains_options")
def trains_options():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, train_number, train_name, source, destination, journey_date, class_type, available_seats FROM trains")
    trains = cur.fetchall()
    conn.close()
    options = ""
    for t in trains:
        options += '<option value="{}">{} - {} | {} → {} | {} | {} | Seats: {}</option>\n'.format(
            t["id"], t["train_number"], t["train_name"], t["source"],
            t["destination"], t["journey_date"], t["class_type"], t["available_seats"]
        )
    return options


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
