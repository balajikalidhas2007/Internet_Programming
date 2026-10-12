from flask import Flask, request, send_file
import sqlite3
import os

app = Flask(__name__)


# Create database
def create_database():

    conn = sqlite3.connect("hotel.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            room TEXT,
            date TEXT,
            guests INTEGER
        )
    """)

    conn.commit()
    conn.close()


# Home page
@app.route("/")
def home():

    return send_file(
        os.path.join(os.path.dirname(__file__), "hotel.html")
    )


# Check room availability
@app.route("/availability", methods=["GET", "POST"])
def availability():

    if request.method == "GET":
        return """
        <h2>Check Room Availability</h2>

        <p>Please select a room and date from the hotel page.</p>

        <a href="/">Back to Hotel</a>
        """

    room = request.form["room"]
    date = request.form["date"]

    room_quantity = {
        "Single Room": 5,
        "Double Room": 5,
        "Deluxe Room": 3,
        "Suite Room": 2
    }

    conn = sqlite3.connect("hotel.db")

    result = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE room = ? AND date = ?",
        (room, date)
    ).fetchone()

    conn.close()

    booked = result[0]

    available = room_quantity[room] - booked

    if available > 0:

        return f"""
        <html>

        <head>
            <title>Room Availability</title>
        </head>

        <body>

            <h2>Room Available</h2>

            <p>Room Type: {room}</p>

            <p>Date: {date}</p>

            <p>Available Rooms: {available}</p>

            <br>

            <a href="/">Back to Hotel</a>

        </body>

        </html>
        """

    else:

        return f"""
        <html>

        <head>
            <title>Room Availability</title>
        </head>

        <body>

            <h2>Room Not Available</h2>

            <p>{room} is fully booked on {date}.</p>

            <br>

            <a href="/">Back to Hotel</a>

        </body>

        </html>
        """


# Book room
@app.route("/book", methods=["POST"])
def book():

    name = request.form["name"]
    room = request.form["room"]
    date = request.form["date"]
    guests = request.form["guests"]

    room_quantity = {
        "Single Room": 5,
        "Double Room": 5,
        "Deluxe Room": 3,
        "Suite Room": 2
    }

    conn = sqlite3.connect("hotel.db")

    result = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE room = ? AND date = ?",
        (room, date)
    ).fetchone()

    booked = result[0]

    if booked >= room_quantity[room]:

        conn.close()

        return """
        <h2>Room Not Available</h2>

        <p>Sorry, this room is fully booked.</p>

        <a href="/">Back to Hotel</a>
        """

    conn.execute(
        """
        INSERT INTO bookings (name, room, date, guests)
        VALUES (?, ?, ?, ?)
        """,
        (name, room, date, guests)
    )

    conn.commit()
    conn.close()

    return """
    <h2>Room Booked Successfully!</h2>

    <p>Your booking has been saved in the database.</p>

    <a href="/">Back to Hotel</a>
    """


# Admin page
@app.route("/admin")
def admin():

    conn = sqlite3.connect("hotel.db")

    bookings = conn.execute(
        "SELECT * FROM bookings"
    ).fetchall()

    conn.close()

    html = """
    <html>

    <head>

        <title>Hotel Administrator</title>

        <style>

            body {
                font-family: Arial;
                margin: 40px;
            }

            table {
                border-collapse: collapse;
            }

            th, td {
                padding: 8px;
            }

        </style>

    </head>

    <body>

        <h1>Hotel Administrator</h1>

        <h2>Booking Details</h2>

        <table border="1">

            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Room</th>
                <th>Date</th>
                <th>Guests</th>
                <th>Action</th>
            </tr>
    """

    for booking in bookings:

        html += f"""
            <tr>
                <td>{booking[0]}</td>
                <td>{booking[1]}</td>
                <td>{booking[2]}</td>
                <td>{booking[3]}</td>
                <td>{booking[4]}</td>

                <td>
                    <a href="/cancel/{booking[0]}">Cancel</a>
                </td>
            </tr>
        """

    html += """
        </table>

        <br>

        <a href="/">Back to Hotel</a>

    </body>

    </html>
    """

    return html


# Cancel booking
@app.route("/cancel/<int:id>")
def cancel(id):

    conn = sqlite3.connect("hotel.db")

    conn.execute(
        "DELETE FROM bookings WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return """
    <h2>Booking Cancelled</h2>

    <p>The booking has been removed.</p>

    <a href="/admin">Back to Admin</a>
    """


if __name__ == "__main__":

    create_database()

    app.run(debug=True)