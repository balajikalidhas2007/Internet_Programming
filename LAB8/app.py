import os
import sqlite3
from flask import Flask, request, send_file, redirect, url_for, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_CSS = os.path.join(BASE_DIR, "global.css")
DB_PATH = os.path.join(os.path.dirname(__file__), "hospital.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "hospital.html")

COMMON_STYLE = """
<style>
    body { font-family: Arial, sans-serif; background-color: #ffffff; color: #333333; margin: 30px; }
    h1 { color: #1e4d6b; }
    h2, h3 { color: #245b7a; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #ffffff; }
    th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }
    th { background-color: #eef3f7; color: #1e4d6b; }
    tr:nth-child(even) { background-color: #f8fafc; }
    .section { background-color: #fafbfc; border: 1px solid #d0d7de; border-radius: 4px; padding: 18px; margin: 18px 0; }
    label { display: inline-block; width: 180px; font-weight: bold; margin-bottom: 8px; }
    input[type="text"], input[type="number"], select { width: 280px; padding: 6px 8px; margin-bottom: 10px; border: 1px solid #b0c2d0; border-radius: 3px; }
    input[type="submit"], button, .btn { background-color: #2d6a8e; color: #ffffff; border: 1px solid #245b7a; padding: 7px 18px; border-radius: 3px; cursor: pointer; text-decoration: none; display: inline-block; }
    input[type="submit"]:hover, button:hover, .btn:hover { background-color: #1e4d6b; }
    a { color: #1e5a8a; text-decoration: none; }
    a:hover { text-decoration: underline; }
</style>
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            contact TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            hospital_id INTEGER NOT NULL,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            hospital_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Booked',
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)

    cur.execute("SELECT COUNT(*) FROM hospitals")
    if cur.fetchone()[0] == 0:
        sample_hospitals = [
            ("Apollo Multi-Speciality Hospital", "Chennai", "044-28290200"),
            ("City Care General Hospital", "Coimbatore", "0422-2453100"),
            ("Sunrise Healthcare Clinic", "Madurai", "0452-2587400")
        ]
        cur.executemany(
            "INSERT INTO hospitals (name, location, contact) VALUES (?, ?, ?)",
            sample_hospitals
        )

    cur.execute("SELECT COUNT(*) FROM doctors")
    if cur.fetchone()[0] == 0:
        sample_doctors = [
            ("Dr. Rajesh Sharma", "Cardiology", 1),
            ("Dr. Sneha Patel", "Dermatology", 1),
            ("Dr. Amit Verma", "Orthopedics", 2),
            ("Dr. Priya Nair", "Pediatrics", 2),
            ("Dr. Karthik Raman", "General Medicine", 3)
        ]
        cur.executemany(
            "INSERT INTO doctors (name, specialty, hospital_id) VALUES (?, ?, ?)",
            sample_doctors
        )

    conn.commit()
    conn.close()


@app.route("/global.css")
def global_css():
    if os.path.exists(GLOBAL_CSS):
        return send_file(GLOBAL_CSS)
    return "", 404


@app.route("/")
def home():
    return send_file(HTML_PATH)


@app.route("/hospitals_list")
def hospitals_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM hospitals")
    hospitals = cur.fetchall()
    conn.close()

    html = "<table>"
    html += "<tr><th>ID</th><th>Hospital Name</th><th>Location</th><th>Contact</th></tr>"
    for h in hospitals:
        html += f"<tr><td>{h['id']}</td><td><b>{h['name']}</b></td><td>{h['location']}</td><td>{h['contact']}</td></tr>"
    html += "</table>"
    return html


@app.route("/doctors_list")
def doctors_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, d.name AS doctor_name, d.specialty, h.name AS hospital_name, h.location
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
        ORDER BY d.id
    """)
    doctors = cur.fetchall()
    conn.close()

    html = "<table>"
    html += "<tr><th>Doctor ID</th><th>Doctor Name</th><th>Specialty</th><th>Hospital</th><th>Location</th></tr>"
    for d in doctors:
        html += f"<tr><td>{d['id']}</td><td><b>{d['doctor_name']}</b></td><td>{d['specialty']}</td><td>{d['hospital_name']}</td><td>{d['location']}</td></tr>"
    html += "</table>"
    return html


@app.route("/get_booking_data")
def get_booking_data():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, location FROM hospitals")
    hospitals = [dict(row) for row in cur.fetchall()]

    cur.execute("""
        SELECT d.id, d.name, d.specialty, d.hospital_id, h.name AS hospital_name
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
    """)
    doctors = [dict(row) for row in cur.fetchall()]
    conn.close()

    return jsonify({"hospitals": hospitals, "doctors": doctors})


@app.route("/book_appointment", methods=["POST"])
def book_appointment():
    patient_name = request.form["patient_name"].strip()
    phone = request.form["phone"].strip()
    hospital_id = int(request.form["hospital_id"])
    doctor_id = int(request.form["doctor_id"])
    date = request.form["date"].strip()
    time = request.form["time"].strip()

    conn = get_db()
    cur = conn.cursor()

    # BOOKING LOGIC: Prevent doctor from being booked by multiple patients for same date & time
    cur.execute("""
        SELECT a.id, d.name AS doctor_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.doctor_id = ? AND a.date = ? AND a.time = ? AND a.status != 'Cancelled'
    """, (doctor_id, date, time))
    existing = cur.fetchone()

    if existing:
        conn.close()
        return f"""
        <!DOCTYPE html>
        <html><head><title>Booking Conflict</title>{COMMON_STYLE}</head><body>
            <h2>Slot Unavailable</h2>
            <div class="section" style="border-left: 4px solid #c0392b;">
                <p><b>Error:</b> {existing['doctor_name']} already has an active appointment on <b>{date}</b> at <b>{time}</b>.</p>
                <p>Please select another date, time, or doctor.</p>
            </div>
            <p><a href="/" class="btn">&laquo; Go Back to Booking</a></p>
        </body></html>
        """

    # Fetch doctor and hospital details for receipt
    cur.execute("SELECT name FROM hospitals WHERE id = ?", (hospital_id,))
    hospital_name = cur.fetchone()["name"]

    cur.execute("SELECT name, specialty FROM doctors WHERE id = ?", (doctor_id,))
    doctor = cur.fetchone()

    cur.execute("""
        INSERT INTO appointments (patient_name, phone, hospital_id, doctor_id, date, time, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Booked')
    """, (patient_name, phone, hospital_id, doctor_id, date, time))
    appointment_id = cur.lastrowid
    conn.commit()
    conn.close()

    return f"""
    <!DOCTYPE html>
    <html><head><title>Appointment Confirmed</title>{COMMON_STYLE}</head><body>
        <h2>Appointment Booked Successfully!</h2>
        <div class="section">
            <table>
                <tr><th style="width: 200px;">Appointment ID</th><td><b>#{appointment_id}</b></td></tr>
                <tr><th>Patient Name</th><td>{patient_name}</td></tr>
                <tr><th>Phone Number</th><td>{phone}</td></tr>
                <tr><th>Hospital</th><td>{hospital_name}</td></tr>
                <tr><th>Doctor</th><td>{doctor['name']} ({doctor['specialty']})</td></tr>
                <tr><th>Date</th><td>{date}</td></tr>
                <tr><th>Time Slot</th><td>{time}</td></tr>
                <tr><th>Status</th><td><span style="color: green; font-weight: bold;">Booked</span></td></tr>
            </table>
        </div>
        <p><a href="/" class="btn">&laquo; Go Back to Home</a></p>
    </body></html>
    """


@app.route("/view_status", methods=["GET", "POST"])
def view_status():
    phone = request.form.get("phone", "").strip() if request.method == "POST" else request.args.get("phone", "").strip()

    conn = get_db()
    cur = conn.cursor()

    if phone:
        cur.execute("""
            SELECT a.id, a.patient_name, a.phone, h.name AS hospital_name, d.name AS doctor_name, d.specialty, a.date, a.time, a.status
            FROM appointments a
            JOIN hospitals h ON a.hospital_id = h.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.phone = ?
            ORDER BY a.id DESC
        """, (phone,))
    else:
        cur.execute("""
            SELECT a.id, a.patient_name, a.phone, h.name AS hospital_name, d.name AS doctor_name, d.specialty, a.date, a.time, a.status
            FROM appointments a
            JOIN hospitals h ON a.hospital_id = h.id
            JOIN doctors d ON a.doctor_id = d.id
            ORDER BY a.id DESC
        """)

    appointments = cur.fetchall()
    conn.close()

    rows = ""
    if appointments:
        for a in appointments:
            status_color = "green" if a['status'] == 'Booked' else ("blue" if a['status'] == 'Completed' else "red")
            rows += f"""
            <tr>
                <td><b>#{a['id']}</b></td>
                <td>{a['patient_name']}</td>
                <td>{a['phone']}</td>
                <td>{a['hospital_name']}</td>
                <td>{a['doctor_name']} ({a['specialty']})</td>
                <td>{a['date']}</td>
                <td>{a['time']}</td>
                <td style="color: {status_color}; font-weight: bold;">{a['status']}</td>
            </tr>
            """
    else:
        rows = "<tr><td colspan='8' style='text-align:center;'>No appointments found.</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html><head><title>Appointment Status</title>{COMMON_STYLE}</head><body>
        <h2>Appointment Records</h2>
        <p>Showing records {f'for phone: <b>{phone}</b>' if phone else '(All Records)'}</p>
        <table>
            <tr><th>ID</th><th>Patient</th><th>Phone</th><th>Hospital</th><th>Doctor</th><th>Date</th><th>Time</th><th>Status</th></tr>
            {rows}
        </table>
        <br>
        <p><a href="/" class="btn">&laquo; Go Back to Home</a></p>
    </body></html>
    """


@app.route("/cancel_appointment", methods=["POST"])
def cancel_appointment():
    appointment_id = int(request.form["appointment_id"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    apt = cur.fetchone()

    if not apt:
        conn.close()
        return f"""
        <!DOCTYPE html>
        <html><head><title>Not Found</title>{COMMON_STYLE}</head><body>
            <h2>Error: Appointment #{appointment_id} Not Found</h2>
            <p><a href="/" class="btn">&laquo; Go Back to Home</a></p>
        </body></html>
        """

    cur.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()

    return f"""
    <!DOCTYPE html>
    <html><head><title>Appointment Cancelled</title>{COMMON_STYLE}</head><body>
        <h2>Appointment Cancelled</h2>
        <div class="section">
            <p>Appointment <b>#{appointment_id}</b> for patient <b>{apt['patient_name']}</b> has been successfully <b>Cancelled</b>.</p>
        </div>
        <p><a href="/" class="btn">&laquo; Go Back to Home</a></p>
    </body></html>
    """


# ==========================================
# ADMIN ROUTES
# ==========================================

@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM hospitals")
    hospitals = cur.fetchall()

    cur.execute("""
        SELECT d.id, d.name AS doctor_name, d.specialty, h.name AS hospital_name
        FROM doctors d
        JOIN hospitals h ON d.hospital_id = h.id
        ORDER BY d.id
    """)
    doctors = cur.fetchall()

    cur.execute("""
        SELECT a.id, a.patient_name, a.phone, h.name AS hospital_name, d.name AS doctor_name, a.date, a.time, a.status
        FROM appointments a
        JOIN hospitals h ON a.hospital_id = h.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.id DESC
    """)
    appointments = cur.fetchall()
    conn.close()

    # Hospitals options for doctor addition
    hospital_opts = "".join([f'<option value="{h["id"]}">{h["name"]} ({h["location"]})</option>' for h in hospitals])
    appointment_opts = "".join([f'<option value="{a["id"]}">#{a["id"]} - {a["patient_name"]} ({a["doctor_name"]} on {a["date"]}) - Status: {a["status"]}</option>' for a in appointments])

    # Table rows
    hosp_rows = "".join([f"<tr><td>{h['id']}</td><td><b>{h['name']}</b></td><td>{h['location']}</td><td>{h['contact']}</td></tr>" for h in hospitals])
    doc_rows = "".join([f"<tr><td>{d['id']}</td><td><b>{d['doctor_name']}</b></td><td>{d['specialty']}</td><td>{d['hospital_name']}</td></tr>" for d in doctors])
    
    if appointments:
        apt_rows = "".join([
            f"<tr><td>#{a['id']}</td><td>{a['patient_name']}</td><td>{a['phone']}</td><td>{a['hospital_name']}</td><td>{a['doctor_name']}</td><td>{a['date']}</td><td>{a['time']}</td><td><b>{a['status']}</b></td></tr>"
            for a in appointments
        ])
    else:
        apt_rows = "<tr><td colspan='8'>No appointments recorded yet.</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hospital Admin Panel</title>
        {COMMON_STYLE}
    </head>
    <body>
        <h1>HOSPITAL ADMIN PANEL</h1>
        <p><a href="/" class="btn">&laquo; Back to Patient Portal</a></p>
        <hr>

        <!-- 1. View Hospitals and Doctors -->
        <h2>1. All Hospitals & Doctors</h2>
        <div class="section">
            <h3>Registered Hospitals</h3>
            <table>
                <tr><th>ID</th><th>Hospital Name</th><th>Location</th><th>Contact</th></tr>
                {hosp_rows}
            </table>

            <h3 style="margin-top: 20px;">Registered Doctors</h3>
            <table>
                <tr><th>ID</th><th>Doctor Name</th><th>Specialty</th><th>Hospital</th></tr>
                {doc_rows}
            </table>
        </div>

        <!-- 2. Add Hospital -->
        <h2>2. Add a New Hospital</h2>
        <div class="section">
            <form action="/admin/add_hospital" method="post">
                <label>Hospital Name:</label>
                <input type="text" name="name" required><br>
                <label>Location / City:</label>
                <input type="text" name="location" required><br>
                <label>Contact Number:</label>
                <input type="text" name="contact" required><br>
                <input type="submit" value="Add Hospital">
            </form>
        </div>

        <!-- 3. Add Doctor -->
        <h2>3. Add a Doctor</h2>
        <div class="section">
            <form action="/admin/add_doctor" method="post">
                <label>Doctor Name:</label>
                <input type="text" name="name" placeholder="Dr. ..." required><br>
                <label>Specialty:</label>
                <input type="text" name="specialty" placeholder="e.g. Cardiology, Neurology" required><br>
                <label>Hospital:</label>
                <select name="hospital_id" required>
                    <option value="">-- Select Hospital --</option>
                    {hospital_opts}
                </select><br>
                <input type="submit" value="Add Doctor">
            </form>
        </div>

        <!-- 4. View All Appointments -->
        <h2>4. All Patient Appointments</h2>
        <div class="section">
            <table>
                <tr><th>ID</th><th>Patient</th><th>Phone</th><th>Hospital</th><th>Doctor</th><th>Date</th><th>Time</th><th>Status</th></tr>
                {apt_rows}
            </table>
        </div>

        <!-- 5. Update Appointment Status -->
        <h2>5. Update Appointment Status</h2>
        <div class="section">
            <form action="/admin/update_status" method="post">
                <label>Select Appointment:</label>
                <select name="appointment_id" style="width: 400px;" required>
                    <option value="">-- Select Appointment --</option>
                    {appointment_opts}
                </select><br>
                <label>New Status:</label>
                <select name="status" required>
                    <option value="Booked">Booked</option>
                    <option value="Completed">Completed</option>
                    <option value="Cancelled">Cancelled</option>
                </select><br>
                <input type="submit" value="Update Status">
            </form>
        </div>
    </body>
    </html>
    """


@app.route("/admin/add_hospital", methods=["POST"])
def admin_add_hospital():
    name = request.form["name"].strip()
    location = request.form["location"].strip()
    contact = request.form["contact"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO hospitals (name, location, contact) VALUES (?, ?, ?)", (name, location, contact))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/add_doctor", methods=["POST"])
def admin_add_doctor():
    name = request.form["name"].strip()
    specialty = request.form["specialty"].strip()
    hospital_id = int(request.form["hospital_id"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO doctors (name, specialty, hospital_id) VALUES (?, ?, ?)", (name, specialty, hospital_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/update_status", methods=["POST"])
def admin_update_status():
    appointment_id = int(request.form["appointment_id"])
    status = request.form["status"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appointment_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
