import os
import sqlite3
from datetime import datetime
from flask import Flask, request, send_file, redirect, url_for, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_CSS = os.path.join(BASE_DIR, "global.css")
DB_PATH = os.path.join(os.path.dirname(__file__), "property.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "property.html")

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
    label { display: inline-block; width: 180px; font-weight: bold; margin-bottom: 8px; vertical-align: top; }
    input[type="text"], input[type="number"], textarea, select { width: 280px; padding: 6px 8px; margin-bottom: 10px; border: 1px solid #b0c2d0; border-radius: 3px; box-sizing: border-box; }
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
        CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            availability TEXT NOT NULL DEFAULT 'Available'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            message TEXT NOT NULL,
            date_submitted TEXT NOT NULL,
            FOREIGN KEY (property_id) REFERENCES properties(id)
        )
    """)

    cur.execute("SELECT COUNT(*) FROM properties")
    if cur.fetchone()[0] == 0:
        sample_properties = [
            ("Green Meadows Villa", "House", "Anna Nagar", "Luxury 3BHK independent villa with private garden", 8500000.0, "Available"),
            ("Sunrise Plots Phase 1", "Land", "OMR", "DTCP approved 1200 sq.ft residential plot near IT corridor", 2400000.0, "Available"),
            ("Royal Palm Apartment", "House", "Velachery", "Modern 2BHK flat with covered car parking and lift", 5200000.0, "Available"),
            ("Serene Acres Farmland", "Land", "Chengalpattu", "1 Acre fertile agricultural & weekend farmhouse land", 3500000.0, "Available"),
            ("Hillview Duplex Home", "House", "Tambaram", "Spacious 4BHK duplex with private terrace view", 9500000.0, "Available")
        ]
        cur.executemany(
            "INSERT INTO properties (name, type, location, description, price, availability) VALUES (?, ?, ?, ?, ?, ?)",
            sample_properties
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


@app.route("/api/properties")
def api_properties():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM properties ORDER BY id")
    properties = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(properties)


@app.route("/property/<int:prop_id>")
def property_details(prop_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM properties WHERE id = ?", (prop_id,))
    p = cur.fetchone()
    conn.close()

    if not p:
        return f"""
        <!DOCTYPE html><html><head><title>Property Not Found</title>{COMMON_STYLE}</head><body>
            <h2>Property Not Found</h2>
            <p><a href="/" class="btn">&laquo; Back to Finder</a></p>
        </body></html>
        """

    return f"""
    <!DOCTYPE html><html><head><title>{p['name']} - Property Details</title>{COMMON_STYLE}</head><body>
        <h2>Property Details: {p['name']}</h2>
        <div class="section">
            <table>
                <tr><th style="width: 200px;">Property ID</th><td>#{p['id']}</td></tr>
                <tr><th>Property Name</th><td><b>{p['name']}</b></td></tr>
                <tr><th>Property Type</th><td>{p['type']}</td></tr>
                <tr><th>Location</th><td>{p['location']}</td></tr>
                <tr><th>Description</th><td>{p['description']}</td></tr>
                <tr><th>Price</th><td><b>₹{p['price']:,.2f}</b></td></tr>
                <tr><th>Availability</th><td><b>{p['availability']}</b></td></tr>
            </table>
        </div>
        <p><a href="/" class="btn">&laquo; Back to Finder</a></p>
    </body></html>
    """


@app.route("/submit_enquiry", methods=["POST"])
def submit_enquiry():
    property_id = int(request.form["property_id"])
    customer_name = request.form["customer_name"].strip()
    phone = request.form["phone"].strip()
    message = request.form["message"].strip()
    date_submitted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
    prop = cur.fetchone()

    if not prop:
        conn.close()
        return f"""
        <!DOCTYPE html><html><head><title>Error</title>{COMMON_STYLE}</head><body>
            <h2>Error: Property not found!</h2>
            <p><a href="/" class="btn">&laquo; Go Back</a></p>
        </body></html>
        """

    cur.execute("""
        INSERT INTO enquiries (property_id, customer_name, phone, message, date_submitted)
        VALUES (?, ?, ?, ?, ?)
    """, (property_id, customer_name, phone, message, date_submitted))
    enquiry_id = cur.lastrowid
    conn.commit()
    conn.close()

    return f"""
    <!DOCTYPE html><html><head><title>Enquiry Submitted</title>{COMMON_STYLE}</head><body>
        <h2>Property Enquiry Submitted Successfully!</h2>
        <div class="section">
            <p style="color: green; font-weight: bold;">Thank you for your interest. A representative will contact you shortly.</p>
            <table>
                <tr><th style="width: 200px;">Enquiry ID</th><td><b>#{enquiry_id}</b></td></tr>
                <tr><th>Property</th><td>{prop['name']} ({prop['type']} in {prop['location']})</td></tr>
                <tr><th>Price</th><td>₹{prop['price']:,.2f}</td></tr>
                <tr><th>Customer Name</th><td>{customer_name}</td></tr>
                <tr><th>Phone Number</th><td>{phone}</td></tr>
                <tr><th>Enquiry Message</th><td>{message}</td></tr>
                <tr><th>Submission Date</th><td>{date_submitted}</td></tr>
            </table>
        </div>
        <p><a href="/" class="btn">&laquo; Go Back to Property Listings</a></p>
    </body></html>
    """


# ==========================================
# ADMIN ROUTES
# ==========================================

@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM properties ORDER BY id")
    properties = cur.fetchall()

    cur.execute("""
        SELECT e.id, e.customer_name, e.phone, e.message, e.date_submitted,
               p.name AS property_name, p.type, p.location
        FROM enquiries e
        JOIN properties p ON e.property_id = p.id
        ORDER BY e.id DESC
    """)
    enquiries = cur.fetchall()
    conn.close()

    # Property table rows
    prop_rows = "".join([
        f"<tr><td>{p['id']}</td><td><b>{p['name']}</b></td><td>{p['type']}</td><td>{p['location']}</td><td>{p['description']}</td><td>₹{p['price']:,.2f}</td><td><b>{p['availability']}</b></td></tr>"
        for p in properties
    ])

    prop_opts = "".join([f'<option value="{p["id"]}">#{p["id"]} - {p["name"]} ({p["type"]}, {p["location"]}, ₹{p["price"]:,.2f})</option>' for p in properties])

    # Enquiries table rows
    if enquiries:
        enquiry_rows = "".join([
            f"<tr><td>#{e['id']}</td><td>{e['customer_name']}</td><td>{e['phone']}</td><td>{e['property_name']} ({e['type']})</td><td>{e['message']}</td><td>{e['date_submitted']}</td></tr>"
            for e in enquiries
        ])
    else:
        enquiry_rows = "<tr><td colspan='6'>No customer enquiries received yet.</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Property Admin Panel</title>
        {COMMON_STYLE}
    </head>
    <body>
        <h1>REAL ESTATE ADMIN PANEL</h1>
        <p><a href="/" class="btn">&laquo; Back to Finder Portal</a></p>
        <hr>

        <!-- 1. View All Properties -->
        <h2>1. All Property Listings</h2>
        <div class="section">
            <table>
                <tr><th>ID</th><th>Property Name</th><th>Type</th><th>Location</th><th>Description</th><th>Price (₹)</th><th>Availability</th></tr>
                {prop_rows}
            </table>
        </div>

        <!-- 2. Add New Listing -->
        <h2>2. Add a New House / Land Listing</h2>
        <div class="section">
            <form action="/admin/add_property" method="post">
                <label>Property Name:</label>
                <input type="text" name="name" required><br>
                <label>Property Type:</label>
                <select name="type" required>
                    <option value="House">House</option>
                    <option value="Land">Land</option>
                </select><br>
                <label>Location / Area:</label>
                <input type="text" name="location" required><br>
                <label>Description:</label>
                <textarea name="description" rows="2" style="width: 280px;" required></textarea><br>
                <label>Price (₹):</label>
                <input type="number" step="1000" name="price" required><br>
                <label>Availability:</label>
                <select name="availability" required>
                    <option value="Available">Available</option>
                    <option value="Under Offer">Under Offer</option>
                    <option value="Sold">Sold</option>
                </select><br>
                <input type="submit" value="Add Property Listing">
            </form>
        </div>

        <!-- 3. Update Property Details & Price -->
        <h2>3. Update Property Details and Price</h2>
        <div class="section">
            <form action="/admin/update_property" method="post">
                <label>Select Property:</label>
                <select name="property_id" style="width: 420px;" required>
                    <option value="">-- Select Property --</option>
                    {prop_opts}
                </select><br>
                <label>Updated Location:</label>
                <input type="text" name="location" required><br>
                <label>Updated Description:</label>
                <textarea name="description" rows="2" style="width: 280px;" required></textarea><br>
                <label>Updated Price (₹):</label>
                <input type="number" step="1000" name="price" required><br>
                <input type="submit" value="Update Property Details">
            </form>
        </div>

        <!-- 4. Update Property Availability -->
        <h2>4. Update Property Availability</h2>
        <div class="section">
            <form action="/admin/update_availability" method="post">
                <label>Select Property:</label>
                <select name="property_id" style="width: 420px;" required>
                    <option value="">-- Select Property --</option>
                    {prop_opts}
                </select><br>
                <label>Availability Status:</label>
                <select name="availability" required>
                    <option value="Available">Available</option>
                    <option value="Under Offer">Under Offer</option>
                    <option value="Sold">Sold</option>
                </select><br>
                <input type="submit" value="Update Availability">
            </form>
        </div>

        <!-- 5. Delete Property Listing -->
        <h2>5. Delete a Property Listing</h2>
        <div class="section">
            <form action="/admin/delete_property" method="post" onsubmit="return confirm('Are you sure you want to delete this property listing?');">
                <label>Select Property:</label>
                <select name="property_id" style="width: 420px;" required>
                    <option value="">-- Select Property to Delete --</option>
                    {prop_opts}
                </select><br>
                <input type="submit" value="Delete Listing" style="background-color: #c0392b; border-color: #a93226;">
            </form>
        </div>

        <!-- 6. View Customer Enquiries -->
        <h2>6. Buyer Enquiries</h2>
        <div class="section">
            <table>
                <tr><th>ID</th><th>Customer Name</th><th>Phone</th><th>Property</th><th>Message</th><th>Date Submitted</th></tr>
                {enquiry_rows}
            </table>
        </div>
    </body>
    </html>
    """


@app.route("/admin/add_property", methods=["POST"])
def admin_add_property():
    name = request.form["name"].strip()
    ptype = request.form["type"].strip()
    location = request.form["location"].strip()
    description = request.form["description"].strip()
    price = float(request.form["price"])
    availability = request.form["availability"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO properties (name, type, location, description, price, availability) VALUES (?, ?, ?, ?, ?, ?)",
        (name, ptype, location, description, price, availability)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/update_property", methods=["POST"])
def admin_update_property():
    property_id = int(request.form["property_id"])
    location = request.form["location"].strip()
    description = request.form["description"].strip()
    price = float(request.form["price"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE properties SET location = ?, description = ?, price = ? WHERE id = ?",
        (location, description, price, property_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/update_availability", methods=["POST"])
def admin_update_availability():
    property_id = int(request.form["property_id"])
    availability = request.form["availability"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE properties SET availability = ? WHERE id = ?", (availability, property_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/delete_property", methods=["POST"])
def admin_delete_property():
    property_id = int(request.form["property_id"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM enquiries WHERE property_id = ?", (property_id,))
    cur.execute("DELETE FROM properties WHERE id = ?", (property_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
