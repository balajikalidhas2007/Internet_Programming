import os
import sqlite3
import random
import string
from flask import Flask, request, send_file, redirect, url_for

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "flight.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "flight.html")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def generate_ticket_id():
    return "TKT" + "".join(random.choices(string.digits, k=8))


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_number TEXT NOT NULL,
            airline TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            class_type TEXT NOT NULL,
            available_seats INTEGER NOT NULL,
            fare INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            passenger_name TEXT NOT NULL,
            flight_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            class_type TEXT NOT NULL,
            passengers INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (flight_id) REFERENCES flights(id)
        )
    """)
    # Insert sample flights if table is empty
    cur.execute("SELECT COUNT(*) FROM flights")
    if cur.fetchone()[0] == 0:
        sample = [
            ("AI-101", "Air India", "Delhi", "Mumbai", "2026-10-20", "Economy", 120, 4500),
            ("AI-101", "Air India", "Delhi", "Mumbai", "2026-10-20", "Business", 30, 12000),
            ("6E-302", "IndiGo", "Chennai", "Bangalore", "2026-10-22", "Economy", 150, 3200),
            ("SG-410", "SpiceJet", "Hyderabad", "Kolkata", "2026-10-25", "Economy", 100, 5500),
            ("UK-805", "Vistara", "Mumbai", "Delhi", "2026-10-18", "Business", 25, 15000),
            ("6E-550", "IndiGo", "Bangalore", "Hyderabad", "2026-10-21", "Economy", 140, 2800),
        ]
        cur.executemany(
            "INSERT INTO flights (flight_number, airline, source, destination, departure_date, class_type, available_seats, fare) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            sample,
        )
    conn.commit()
    conn.close()


# ---------- Routes ----------

@app.route("/")
def home():
    return send_file(HTML_PATH)


@app.route("/search", methods=["POST"])
def search_flights():
    source = request.form.get("source", "").strip()
    destination = request.form.get("destination", "").strip()
    date = request.form.get("departure_date", "").strip()

    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM flights WHERE 1=1"
    params = []
    if source:
        query += " AND LOWER(source) = LOWER(?)"
        params.append(source)
    if destination:
        query += " AND LOWER(destination) = LOWER(?)"
        params.append(destination)
    if date:
        query += " AND departure_date = ?"
        params.append(date)

    cur.execute(query, params)
    flights = cur.fetchall()
    conn.close()

    html = "<h1>Search Results</h1>"
    if not flights:
        html += "<p>No flights found.</p>"
    else:
        html += "<table border='1' cellpadding='5' cellspacing='0'>"
        html += "<tr><th>ID</th><th>Flight No</th><th>Airline</th><th>Source</th><th>Destination</th><th>Date</th><th>Class</th><th>Seats</th><th>Fare (₹)</th></tr>"
        for f in flights:
            html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                f["id"], f["flight_number"], f["airline"], f["source"],
                f["destination"], f["departure_date"], f["class_type"],
                f["available_seats"], f["fare"]
            )
        html += "</table>"
    html += "<br><a href='/'>Go Back</a>"
    return html


@app.route("/book", methods=["POST"])
def book_ticket():
    passenger_name = request.form["passenger_name"]
    flight_id = int(request.form["flight_id"])
    num_passengers = int(request.form["num_passengers"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM flights WHERE id = ?", (flight_id,))
    flight = cur.fetchone()

    if flight is None:
        conn.close()
        return "<h3>Error: Flight not found.</h3><br><a href='/'>Go Back</a>"

    if flight["available_seats"] < num_passengers:
        conn.close()
        return "<h3>Error: Not enough seats. Only {} seats available.</h3><br><a href='/'>Go Back</a>".format(
            flight["available_seats"]
        )

    ticket_id = generate_ticket_id()
    total_fare = flight["fare"] * num_passengers

    cur.execute(
        "INSERT INTO bookings (ticket_id, passenger_name, flight_id, source, destination, departure_date, class_type, passengers, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ticket_id, passenger_name, flight_id, flight["source"], flight["destination"],
         flight["departure_date"], flight["class_type"], num_passengers, "CONFIRMED"),
    )
    cur.execute(
        "UPDATE flights SET available_seats = available_seats - ? WHERE id = ?",
        (num_passengers, flight_id),
    )
    conn.commit()
    conn.close()

    return """
    <h2>Ticket Booked Successfully!</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><td><b>Ticket ID</b></td><td>{}</td></tr>
        <tr><td><b>Passenger</b></td><td>{}</td></tr>
        <tr><td><b>Flight</b></td><td>{} - {}</td></tr>
        <tr><td><b>Route</b></td><td>{} → {}</td></tr>
        <tr><td><b>Date</b></td><td>{}</td></tr>
        <tr><td><b>Class</b></td><td>{}</td></tr>
        <tr><td><b>Passengers</b></td><td>{}</td></tr>
        <tr><td><b>Total Fare</b></td><td>₹{}</td></tr>
        <tr><td><b>Status</b></td><td>CONFIRMED</td></tr>
    </table>
    <br><a href="/">Go Back</a>
    """.format(ticket_id, passenger_name, flight["flight_number"], flight["airline"],
               flight["source"], flight["destination"], flight["departure_date"],
               flight["class_type"], num_passengers, total_fare)


@app.route("/status", methods=["POST"])
def check_status():
    ticket_id = request.form["ticket_id"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.*, f.flight_number, f.airline, f.fare
        FROM bookings b
        JOIN flights f ON b.flight_id = f.id
        WHERE b.ticket_id = ?
    """, (ticket_id,))
    booking = cur.fetchone()
    conn.close()

    if booking is None:
        return "<h3>Error: Ticket ID not found.</h3><br><a href='/'>Go Back</a>"

    return """
    <h2>Booking Status</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><td><b>Ticket ID</b></td><td>{}</td></tr>
        <tr><td><b>Passenger</b></td><td>{}</td></tr>
        <tr><td><b>Flight</b></td><td>{} - {}</td></tr>
        <tr><td><b>Route</b></td><td>{} → {}</td></tr>
        <tr><td><b>Date</b></td><td>{}</td></tr>
        <tr><td><b>Class</b></td><td>{}</td></tr>
        <tr><td><b>Passengers</b></td><td>{}</td></tr>
        <tr><td><b>Status</b></td><td>{}</td></tr>
    </table>
    <br><a href="/">Go Back</a>
    """.format(booking["ticket_id"], booking["passenger_name"],
               booking["flight_number"], booking["airline"],
               booking["source"], booking["destination"],
               booking["departure_date"], booking["class_type"],
               booking["passengers"], booking["status"])


@app.route("/cancel", methods=["POST"])
def cancel_ticket():
    ticket_id = request.form["ticket_id_cancel"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT flight_id, passengers FROM bookings WHERE ticket_id = ?", (ticket_id,))
    booking = cur.fetchone()

    if booking is None:
        conn.close()
        return "<h3>Error: Ticket ID not found.</h3><br><a href='/'>Go Back</a>"

    cur.execute("DELETE FROM bookings WHERE ticket_id = ?", (ticket_id,))
    cur.execute(
        "UPDATE flights SET available_seats = available_seats + ? WHERE id = ?",
        (booking["passengers"], booking["flight_id"]),
    )
    conn.commit()
    conn.close()

    return "<h2>Ticket Cancelled Successfully!</h2><p>Ticket {} has been cancelled.</p><br><a href='/'>Go Back</a>".format(ticket_id)


@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM flights")
    flights = cur.fetchall()

    cur.execute("""
        SELECT b.ticket_id, b.passenger_name, f.flight_number, f.airline,
               b.source, b.destination, b.departure_date, b.class_type,
               b.passengers, b.status
        FROM bookings b
        JOIN flights f ON b.flight_id = f.id
    """)
    bookings = cur.fetchall()
    conn.close()

    html = "<h1>Admin Page - Flight Reservation System</h1>"

    html += "<h2>Flight Information</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>ID</th><th>Flight No</th><th>Airline</th><th>Source</th><th>Destination</th><th>Date</th><th>Class</th><th>Seats</th><th>Fare (₹)</th></tr>"
    for f in flights:
        html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            f["id"], f["flight_number"], f["airline"], f["source"],
            f["destination"], f["departure_date"], f["class_type"],
            f["available_seats"], f["fare"]
        )
    html += "</table>"

    html += "<h2>Booking Information</h2>"
    if bookings:
        html += "<table border='1' cellpadding='5' cellspacing='0'>"
        html += "<tr><th>Ticket ID</th><th>Passenger</th><th>Flight</th><th>Airline</th><th>Source</th><th>Destination</th><th>Date</th><th>Class</th><th>Passengers</th><th>Status</th></tr>"
        for b in bookings:
            html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                b["ticket_id"], b["passenger_name"], b["flight_number"], b["airline"],
                b["source"], b["destination"], b["departure_date"], b["class_type"],
                b["passengers"], b["status"]
            )
        html += "</table>"
    else:
        html += "<p>No bookings yet.</p>"

    html += "<br><hr>"
    html += "<h2>Add New Flight</h2>"
    html += """
    <form action="/add_flight" method="post">
        Flight Number: <input type="text" name="flight_number" required><br><br>
        Airline: <input type="text" name="airline" required><br><br>
        Source: <input type="text" name="source" required><br><br>
        Destination: <input type="text" name="destination" required><br><br>
        Departure Date: <input type="date" name="departure_date" required><br><br>
        Class Type: <input type="text" name="class_type" required><br><br>
        Available Seats: <input type="number" name="available_seats" required><br><br>
        Fare (₹): <input type="number" name="fare" required><br><br>
        <input type="submit" value="Add Flight">
    </form>
    """
    html += "<br><a href='/'>Go Back to Home</a>"
    return html


@app.route("/add_flight", methods=["POST"])
def add_flight():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO flights (flight_number, airline, source, destination, departure_date, class_type, available_seats, fare) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            request.form["flight_number"],
            request.form["airline"],
            request.form["source"],
            request.form["destination"],
            request.form["departure_date"],
            request.form["class_type"],
            int(request.form["available_seats"]),
            int(request.form["fare"]),
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/flight_dates")
def flight_dates():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT departure_date FROM flights ORDER BY departure_date")
    dates = cur.fetchall()
    conn.close()
    options = ""
    for d in dates:
        options += '<option value="{}">{}</option>\n'.format(d["departure_date"], d["departure_date"])
    return options


@app.route("/flights_by_date")
def flights_by_date():
    date = request.args.get("date", "").strip()
    conn = get_db()
    cur = conn.cursor()
    if date:
        cur.execute("SELECT * FROM flights WHERE departure_date = ?", (date,))
    else:
        cur.execute("SELECT * FROM flights")
    flights = cur.fetchall()
    conn.close()

    if not flights:
        return "<p>No flights available for the selected date.</p>"

    html = "<h3>Available Flights:</h3>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Flight No</th><th>Flight Name</th><th>Source</th><th>Destination</th><th>Date</th><th>Class</th><th>Available Seats</th><th>Fare (₹)</th><th>Action</th></tr>"
    for f in flights:
        html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>₹{}</td><td><button type='button' onclick='selectFlight({})'>Select</button></td></tr>".format(
            f["flight_number"], f["airline"], f["source"],
            f["destination"], f["departure_date"], f["class_type"],
            f["available_seats"], f["fare"], f["id"]
        )
    html += "</table>"
    return html


@app.route("/flights_options")
def flights_options():
    date = request.args.get("date", "").strip()
    conn = get_db()
    cur = conn.cursor()
    if date:
        cur.execute("SELECT id, flight_number, airline, source, destination, departure_date, class_type, available_seats, fare FROM flights WHERE departure_date = ?", (date,))
    else:
        cur.execute("SELECT id, flight_number, airline, source, destination, departure_date, class_type, available_seats, fare FROM flights")
    flights = cur.fetchall()
    conn.close()
    options = ""
    for f in flights:
        options += '<option value="{}">{} - {} | {} → {} | {} | {} | Seats: {} | ₹{}</option>\n'.format(
            f["id"], f["flight_number"], f["airline"], f["source"],
            f["destination"], f["departure_date"], f["class_type"],
            f["available_seats"], f["fare"]
        )
    return options


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
