import os
import sqlite3
from flask import Flask, request, send_file, redirect, url_for

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "beauty.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "beauty.html")


# ---------- Database Connection ----------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- Create Database ----------

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Services table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    # Stylists table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stylists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL
        )
    """)

    # Appointments table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            service_id INTEGER NOT NULL,
            stylist_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Booked',
            FOREIGN KEY (service_id) REFERENCES services(id),
            FOREIGN KEY (stylist_id) REFERENCES stylists(id)
        )
    """)

    # Sample Services
    cur.execute("SELECT COUNT(*) FROM services")

    if cur.fetchone()[0] == 0:

        sample_services = [
            (
                "Haircut & Styling",
                "Professional hair trimming and styling",
                400.0
            ),
            (
                "Facial & Cleanup",
                "Facial with deep cleansing",
                750.0
            ),
            (
                "Bridal Makeup",
                "Bridal and party makeup",
                2500.0
            ),
            (
                "Manicure & Pedicure",
                "Hand and foot spa",
                600.0
            ),
            (
                "Hair Spa",
                "Hair nourishment and conditioning",
                900.0
            )
        ]

        cur.executemany(
            """
            INSERT INTO services
            (name, description, price)
            VALUES (?, ?, ?)
            """,
            sample_services
        )

    # Sample Stylists
    cur.execute("SELECT COUNT(*) FROM stylists")

    if cur.fetchone()[0] == 0:

        sample_stylists = [
            ("Priya Sharma", "Hair Specialist"),
            ("Ananya Rao", "Skin & Facial Expert"),
            ("Deepa Nair", "Bridal & Party Makeup"),
            ("Sneha Patel", "Nail Art & Spa Specialist")
        ]

        cur.executemany(
            """
            INSERT INTO stylists
            (name, specialization)
            VALUES (?, ?)
            """,
            sample_stylists
        )

    conn.commit()
    conn.close()


# ---------- Home ----------

@app.route("/")
def home():
    return send_file(HTML_PATH)


# ---------- Get Services and Stylists ----------

@app.route("/get_data")
def get_data():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM services")
    services = cur.fetchall()

    cur.execute("SELECT * FROM stylists")
    stylists = cur.fetchall()

    conn.close()

    service_opts = ""

    for s in services:
        service_opts += (
            '<option value="{}">{} (₹{})</option>'
            .format(s["id"], s["name"], s["price"])
        )

    stylist_opts = ""

    for st in stylists:
        stylist_opts += (
            '<option value="{}">{} - {}</option>'
            .format(
                st["id"],
                st["name"],
                st["specialization"]
            )
        )

    return {
        "services": service_opts,
        "stylists": stylist_opts
    }


# ---------- Services List ----------

@app.route("/services_list")
def services_list():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM services")
    services = cur.fetchall()

    conn.close()

    html = """
    <h2>Beauty Services</h2>

    <table border="1" cellpadding="5" cellspacing="0">

    <tr>
        <th>ID</th>
        <th>Service</th>
        <th>Description</th>
        <th>Price</th>
    </tr>
    """

    for s in services:

        html += """
        <tr>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>₹{}</td>
        </tr>
        """.format(
            s["id"],
            s["name"],
            s["description"],
            s["price"]
        )

    html += """
    </table>

    <br>

    <a href="/">Go Back</a>
    """

    return html


# ---------- Stylists List ----------

@app.route("/stylists_list")
def stylists_list():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM stylists")
    stylists = cur.fetchall()

    conn.close()

    html = """
    <h2>Stylists</h2>

    <table border="1" cellpadding="5" cellspacing="0">

    <tr>
        <th>ID</th>
        <th>Stylist Name</th>
        <th>Specialization</th>
    </tr>
    """

    for st in stylists:

        html += """
        <tr>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
        </tr>
        """.format(
            st["id"],
            st["name"],
            st["specialization"]
        )

    html += """
    </table>

    <br>

    <a href="/">Go Back</a>
    """

    return html


# ---------- Book Appointment ----------

@app.route("/book", methods=["POST"])
def book_appointment():

    customer_name = request.form["customer_name"].strip()
    phone = request.form["phone"].strip()

    service_id = int(request.form["service_id"])
    stylist_id = int(request.form["stylist_id"])

    date = request.form["date"].strip()
    time_slot = request.form["time"].strip()

    conn = get_db()
    cur = conn.cursor()

    # Check whether slot is already booked

    cur.execute("""
        SELECT *
        FROM appointments
        WHERE stylist_id = ?
        AND date = ?
        AND time = ?
        AND status != 'Cancelled'
    """, (
        stylist_id,
        date,
        time_slot
    ))

    existing = cur.fetchone()

    if existing:

        conn.close()

        return """
        <h3>
        Error: This slot is already booked for the selected stylist.
        Please choose another time or stylist.
        </h3>

        <br>

        <a href="/">Go Back</a>
        """

    # Get service details

    cur.execute(
        "SELECT name, price FROM services WHERE id = ?",
        (service_id,)
    )

    service = cur.fetchone()

    # Get stylist details

    cur.execute(
        "SELECT name FROM stylists WHERE id = ?",
        (stylist_id,)
    )

    stylist = cur.fetchone()

    # Insert appointment

    cur.execute("""
        INSERT INTO appointments
        (
            customer_name,
            phone,
            service_id,
            stylist_id,
            date,
            time,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, 'Booked')
    """, (
        customer_name,
        phone,
        service_id,
        stylist_id,
        date,
        time_slot
    ))

    appointment_id = cur.lastrowid

    conn.commit()
    conn.close()

    return """
    <h2>Appointment Booked Successfully!</h2>

    <table border="1" cellpadding="5" cellspacing="0">

        <tr>
            <td><b>Appointment ID</b></td>
            <td>{}</td>
        </tr>

        <tr>
            <td><b>Customer Name</b></td>
            <td>{}</td>
        </tr>

        <tr>
            <td><b>Phone</b></td>
            <td>{}</td>
        </tr>

        <tr>
            <td><b>Service</b></td>
            <td>{} (₹{})</td>
        </tr>

        <tr>
            <td><b>Stylist</b></td>
            <td>{}</td>
        </tr>

        <tr>
            <td><b>Date</b></td>
            <td>{}</td>
        </tr>

        <tr>
            <td><b>Time</b></td>
            <td>{}</td>
        </tr>

        <tr>
            <td><b>Status</b></td>
            <td>Booked</td>
        </tr>

    </table>

    <br>

    <a href="/">Go Back to Home</a>
    """.format(
        appointment_id,
        customer_name,
        phone,
        service["name"],
        service["price"],
        stylist["name"],
        date,
        time_slot
    )


# ---------- My Appointments ----------

@app.route("/my_appointments", methods=["POST"])
def my_appointments():

    phone = request.form.get("phone", "").strip()

    conn = get_db()
    cur = conn.cursor()

    if phone:

        cur.execute("""
            SELECT
                a.id,
                a.customer_name,
                a.phone,
                s.name AS service_name,
                st.name AS stylist_name,
                a.date,
                a.time,
                a.status
            FROM appointments a
            JOIN services s
                ON a.service_id = s.id
            JOIN stylists st
                ON a.stylist_id = st.id
            WHERE a.phone = ?
            ORDER BY a.id DESC
        """, (phone,))

    else:

        cur.execute("""
            SELECT
                a.id,
                a.customer_name,
                a.phone,
                s.name AS service_name,
                st.name AS stylist_name,
                a.date,
                a.time,
                a.status
            FROM appointments a
            JOIN services s
                ON a.service_id = s.id
            JOIN stylists st
                ON a.stylist_id = st.id
            ORDER BY a.id DESC
        """)

    appointments = cur.fetchall()

    conn.close()

    if not appointments:

        return """
        <p>No appointments found.</p>

        <br>

        <a href="/">Go Back</a>
        """

    html = "<h2>My Appointments</h2>"

    html += """
    <table border="1" cellpadding="5" cellspacing="0">

    <tr>
        <th>ID</th>
        <th>Customer</th>
        <th>Phone</th>
        <th>Service</th>
        <th>Stylist</th>
        <th>Date</th>
        <th>Time</th>
        <th>Status</th>
    </tr>
    """

    for a in appointments:

        html += """
        <tr>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td><b>{}</b></td>
        </tr>
        """.format(
            a["id"],
            a["customer_name"],
            a["phone"],
            a["service_name"],
            a["stylist_name"],
            a["date"],
            a["time"],
            a["status"]
        )

    html += """
    </table>

    <br>

    <a href="/">Go Back</a>
    """

    return html


# ---------- Cancel Appointment ----------

@app.route("/cancel_appointment", methods=["POST"])
def cancel_appointment():

    app_id = int(request.form["appointment_id"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM appointments WHERE id = ?",
        (app_id,)
    )

    row = cur.fetchone()

    if not row:

        conn.close()

        return """
        <h3>Error: Appointment ID not found.</h3>

        <br>

        <a href="/">Go Back</a>
        """

    cur.execute("""
        UPDATE appointments
        SET status = 'Cancelled'
        WHERE id = ?
    """, (app_id,))

    conn.commit()
    conn.close()

    return """
    <h2>Appointment Cancelled Successfully!</h2>

    <p>
    Appointment ID {} has been cancelled.
    </p>

    <br>

    <a href="/">Go Back</a>
    """.format(app_id)


# ==========================================================
# ADMIN
# ==========================================================

@app.route("/admin")
def admin():

    conn = get_db()
    cur = conn.cursor()

    # Services

    cur.execute("SELECT * FROM services")
    services = cur.fetchall()

    # Stylists

    cur.execute("SELECT * FROM stylists")
    stylists = cur.fetchall()

    # Appointments

    cur.execute("""
        SELECT
            a.id,
            a.customer_name,
            a.phone,
            s.name AS service_name,
            st.name AS stylist_name,
            a.date,
            a.time,
            a.status
        FROM appointments a
        JOIN services s
            ON a.service_id = s.id
        JOIN stylists st
            ON a.stylist_id = st.id
        ORDER BY a.id DESC
    """)

    appointments = cur.fetchall()

    conn.close()

    html = "<h1>Admin / Salon Manager Page</h1>"

    # ---------- Services ----------

    html += "<h2>1. Beauty Services</h2>"

    html += """
    <table border="1" cellpadding="5" cellspacing="0">

    <tr>
        <th>ID</th>
        <th>Service</th>
        <th>Description</th>
        <th>Price</th>
    </tr>
    """

    for s in services:

        html += """
        <tr>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
            <td>₹{}</td>
        </tr>
        """.format(
            s["id"],
            s["name"],
            s["description"],
            s["price"]
        )

    html += "</table>"

    # Add Service

    html += """
    <br>

    <h3>Add New Service</h3>

    <form action="/admin/add_service" method="post">

        Service Name:
        <input type="text" name="name" required>

        <br><br>

        Description:
        <input type="text" name="description" required>

        <br><br>

        Price:
        <input type="number" step="0.01" name="price" required>

        <br><br>

        <input type="submit" value="Add Service">

    </form>
    """

    # Update Service Price

    html += """
    <br>

    <h3>Update Service Price</h3>

    <form action="/admin/update_service_price" method="post">

        Select Service:

        <select name="service_id" required>
    """

    for s in services:

        html += """
        <option value="{}">
            {} (Current: ₹{})
        </option>
        """.format(
            s["id"],
            s["name"],
            s["price"]
        )

    html += """
        </select>

        <br><br>

        New Price:
        <input type="number" step="0.01" name="price" required>

        <br><br>

        <input type="submit" value="Update Price">

    </form>
    """

    # ---------- Stylists ----------

    html += "<hr><h2>2. Stylists</h2>"

    html += """
    <table border="1" cellpadding="5" cellspacing="0">

    <tr>
        <th>ID</th>
        <th>Stylist Name</th>
        <th>Specialization</th>
    </tr>
    """

    for st in stylists:

        html += """
        <tr>
            <td>{}</td>
            <td>{}</td>
            <td>{}</td>
        </tr>
        """.format(
            st["id"],
            st["name"],
            st["specialization"]
        )

    html += "</table>"

    # Add Stylist

    html += """
    <br>

    <h3>Add New Stylist</h3>

    <form action="/admin/add_stylist" method="post">

        Stylist Name:
        <input type="text" name="name" required>

        <br><br>

        Specialization:
        <input type="text" name="specialization" required>

        <br><br>

        <input type="submit" value="Add Stylist">

    </form>
    """

    # ---------- Appointments ----------

    html += "<hr><h2>3. All Appointments</h2>"

    if appointments:

        html += """
        <table border="1" cellpadding="5" cellspacing="0">

        <tr>
            <th>ID</th>
            <th>Customer</th>
            <th>Phone</th>
            <th>Service</th>
            <th>Stylist</th>
            <th>Date</th>
            <th>Time</th>
            <th>Status</th>
        </tr>
        """

        for a in appointments:

            html += """
            <tr>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td><b>{}</b></td>
            </tr>
            """.format(
                a["id"],
                a["customer_name"],
                a["phone"],
                a["service_name"],
                a["stylist_name"],
                a["date"],
                a["time"],
                a["status"]
            )

        html += "</table>"

        # Update Status

        html += """
        <br>

        <h3>Update Appointment Status</h3>

        <form action="/admin/update_status" method="post">

            Select Appointment:

            <select name="appointment_id" required>
        """

        for a in appointments:

            html += """
            <option value="{}">
                ID #{} - {} ({}) on {} {} - [{}]
            </option>
            """.format(
                a["id"],
                a["id"],
                a["customer_name"],
                a["service_name"],
                a["date"],
                a["time"],
                a["status"]
            )

        html += """
            </select>

            <br><br>

            Status:

            <select name="status" required>

                <option value="Booked">
                    Booked
                </option>

                <option value="Completed">
                    Completed
                </option>

                <option value="Cancelled">
                    Cancelled
                </option>

            </select>

            <br><br>

            <input type="submit" value="Update Status">

        </form>
        """

    else:

        html += "<p>No appointments booked yet.</p>"

    html += """
    <br>
    <hr>

    <a href="/">Go Back to Home</a>
    """

    return html


# ---------- Admin: Add Service ----------

@app.route("/admin/add_service", methods=["POST"])
def add_service():

    name = request.form["name"].strip()
    description = request.form["description"].strip()
    price = float(request.form["price"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO services
        (name, description, price)
        VALUES (?, ?, ?)
    """, (
        name,
        description,
        price
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# ---------- Admin: Update Service Price ----------

@app.route("/admin/update_service_price", methods=["POST"])
def update_service_price():

    service_id = int(request.form["service_id"])
    price = float(request.form["price"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE services
        SET price = ?
        WHERE id = ?
    """, (
        price,
        service_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# ---------- Admin: Add Stylist ----------

@app.route("/admin/add_stylist", methods=["POST"])
def add_stylist():

    name = request.form["name"].strip()
    specialization = request.form["specialization"].strip()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO stylists
        (name, specialization)
        VALUES (?, ?)
    """, (
        name,
        specialization
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# ---------- Admin: Update Appointment Status ----------

@app.route("/admin/update_status", methods=["POST"])
def update_status():

    app_id = int(request.form["appointment_id"])
    status = request.form["status"].strip()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE appointments
        SET status = ?
        WHERE id = ?
    """, (
        status,
        app_id
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# ---------- Run Application ----------

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)