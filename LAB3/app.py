import os
import sqlite3
from flask import Flask, request, send_file, redirect, url_for

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_CSS = os.path.join(BASE_DIR, "global.css")
DB_PATH = os.path.join(os.path.dirname(__file__), "bus.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "bus.html")


@app.route("/global.css")
def global_css():
    return send_file(GLOBAL_CSS)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            available_seats INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger_name TEXT NOT NULL,
            bus_id INTEGER NOT NULL,
            travel_date TEXT NOT NULL,
            num_passengers INTEGER NOT NULL,
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )
    """)
    # Insert sample buses if table is empty
    cur.execute("SELECT COUNT(*) FROM buses")
    if cur.fetchone()[0] == 0:
        sample_buses = [
            ("Volvo AC", "Chennai", "Bangalore", "2026-10-15", 40),
            ("Volvo AC", "Bangalore", "Hyderabad", "2026-10-16", 35),
            ("Semi Sleeper", "Chennai", "Madurai", "2026-10-15", 45),
            ("Sleeper", "Hyderabad", "Mumbai", "2026-10-17", 30),
            ("Ordinary", "Coimbatore", "Chennai", "2026-10-18", 50),
        ]
        cur.executemany(
            "INSERT INTO buses (category, source, destination, travel_date, available_seats) VALUES (?, ?, ?, ?, ?)",
            sample_buses,
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
    bus_id = int(request.form["bus_id"])
    num_passengers = int(request.form["num_passengers"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT available_seats, travel_date FROM buses WHERE id = ?", (bus_id,))
    row = cur.fetchone()

    if row is None:
        conn.close()
        return "<h3>Error: Bus not found.</h3><br><a href='/'>Go Back</a>"

    if row["available_seats"] < num_passengers:
        conn.close()
        return "<h3>Error: Not enough seats available. Only {} seats left.</h3><br><a href='/'>Go Back</a>".format(
            row["available_seats"]
        )

    travel_date = row["travel_date"]
    cur.execute(
        "INSERT INTO bookings (passenger_name, bus_id, travel_date, num_passengers) VALUES (?, ?, ?, ?)",
        (passenger_name, bus_id, travel_date, num_passengers),
    )
    cur.execute(
        "UPDATE buses SET available_seats = available_seats - ? WHERE id = ?",
        (num_passengers, bus_id),
    )
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()

    return """
    <h2>Ticket Booked Successfully!</h2>
    <p>Booking ID: {}</p>
    <p>Passenger: {}</p>
    <p>Bus ID: {}</p>
    <p>Travel Date: {}</p>
    <p>Passengers: {}</p>
    <br><a href="/">Go Back</a>
    """.format(booking_id, passenger_name, bus_id, travel_date, num_passengers)


@app.route("/cancel", methods=["POST"])
def cancel_ticket():
    booking_id = int(request.form["booking_id"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT bus_id, num_passengers FROM bookings WHERE booking_id = ?", (booking_id,))
    row = cur.fetchone()

    if row is None:
        conn.close()
        return "<h3>Error: Booking ID not found.</h3><br><a href='/'>Go Back</a>"

    bus_id = row["bus_id"]
    num_passengers = row["num_passengers"]

    cur.execute("DELETE FROM bookings WHERE booking_id = ?", (booking_id,))
    cur.execute(
        "UPDATE buses SET available_seats = available_seats + ? WHERE id = ?",
        (num_passengers, bus_id),
    )
    conn.commit()
    conn.close()

    return "<h2>Ticket Cancelled Successfully!</h2><p>Booking ID {} has been cancelled.</p><br><a href='/'>Go Back</a>".format(
        booking_id
    )


@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM buses")
    buses = cur.fetchall()

    cur.execute("""
        SELECT b.booking_id, b.passenger_name, b.bus_id, bu.category, bu.source, bu.destination,
               b.travel_date, b.num_passengers
        FROM bookings b
        JOIN buses bu ON b.bus_id = bu.id
    """)
    bookings = cur.fetchall()
    conn.close()

    html = "<h1>Admin Page - Bus Ticket Booking</h1>"
    html += "<h2>Available Buses</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>ID</th><th>Category</th><th>Source</th><th>Destination</th><th>Travel Date</th><th>Available Seats</th></tr>"
    for bus in buses:
        html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            bus["id"], bus["category"], bus["source"], bus["destination"], bus["travel_date"], bus["available_seats"]
        )
    html += "</table>"

    html += "<h2>All Bookings</h2>"
    if bookings:
        html += "<table border='1' cellpadding='5' cellspacing='0'>"
        html += "<tr><th>Booking ID</th><th>Passenger</th><th>Bus ID</th><th>Category</th><th>Source</th><th>Destination</th><th>Travel Date</th><th>Passengers</th></tr>"
        for bk in bookings:
            html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                bk["booking_id"], bk["passenger_name"], bk["bus_id"], bk["category"],
                bk["source"], bk["destination"], bk["travel_date"], bk["num_passengers"]
            )
        html += "</table>"
    else:
        html += "<p>No bookings yet.</p>"

    html += "<br><hr>"
    html += "<h2>Add New Bus</h2>"
    html += """
    <form action="/add_bus" method="post">
        Category: <input type="text" name="category" required><br><br>
        Source: <input type="text" name="source" required><br><br>
        Destination: <input type="text" name="destination" required><br><br>
        Travel Date: <input type="date" name="travel_date" required><br><br>
        Available Seats: <input type="number" name="available_seats" required><br><br>
        <input type="submit" value="Add Bus">
    </form>
    """

    html += "<br><a href='/'>Go Back to Home</a>"
    return html


@app.route("/add_bus", methods=["POST"])
def add_bus():
    category = request.form["category"]
    source = request.form["source"]
    destination = request.form["destination"]
    travel_date = request.form["travel_date"]
    available_seats = int(request.form["available_seats"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO buses (category, source, destination, travel_date, available_seats) VALUES (?, ?, ?, ?, ?)",
        (category, source, destination, travel_date, available_seats),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


@app.route("/buses_json")
def buses_json():
    """Return bus list as simple HTML options (used by the form)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, category, source, destination, travel_date, available_seats FROM buses")
    buses = cur.fetchall()
    conn.close()

    options = ""
    for bus in buses:
        options += '<option value="{}">{} | {} → {} | {} | Seats: {}</option>\n'.format(
            bus["id"], bus["category"], bus["source"], bus["destination"], bus["travel_date"], bus["available_seats"]
        )
    return options


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
