import os
import sqlite3
from datetime import datetime
from flask import Flask, request, send_file, redirect, url_for, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_CSS = os.path.join(BASE_DIR, "global.css")
DB_PATH = os.path.join(os.path.dirname(__file__), "insurance.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "insurance.html")

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
    input[type="text"], input[type="email"], input[type="number"], input[type="date"], textarea, select { width: 280px; padding: 6px 8px; margin-bottom: 10px; border: 1px solid #b0c2d0; border-radius: 3px; box-sizing: border-box; }
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
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            region TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            agent_id INTEGER,
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_name TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            description TEXT NOT NULL,
            premium_amount REAL NOT NULL,
            duration_years INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            policy_id INTEGER NOT NULL,
            agent_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (policy_id) REFERENCES policies(id),
            FOREIGN KEY (agent_id) REFERENCES agents(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            policy_id INTEGER,
            message TEXT NOT NULL,
            date_submitted TEXT NOT NULL,
            FOREIGN KEY (policy_id) REFERENCES policies(id)
        )
    """)

    # Seed sample policies
    cur.execute("SELECT COUNT(*) FROM policies")
    if cur.fetchone()[0] == 0:
        sample_policies = [
            ("Jeevan Suraksha Term Plan", "Term Life", "Pure life insurance coverage with high sum assured and family security", 12000.0, 20),
            ("Health Shield Family Floater", "Health", "Comprehensive cashless hospitalization cover for entire family", 18500.0, 1),
            ("Safe Drive Motor Policy", "Vehicle", "Comprehensive motor insurance with zero depreciation add-on", 7500.0, 1),
            ("Home Care Protection", "Property", "Protects residential buildings and contents against damage and theft", 5500.0, 5)
        ]
        cur.executemany(
            "INSERT INTO policies (policy_name, policy_type, description, premium_amount, duration_years) VALUES (?, ?, ?, ?, ?)",
            sample_policies
        )

    # Seed sample agents
    cur.execute("SELECT COUNT(*) FROM agents")
    if cur.fetchone()[0] == 0:
        sample_agents = [
            ("Ramesh Kumar", "9876543210", "ramesh@insurance.com", "South Zone"),
            ("Sunita Iyer", "9876543211", "sunita@insurance.com", "Central Zone")
        ]
        cur.executemany(
            "INSERT INTO agents (name, phone, email, region) VALUES (?, ?, ?, ?)",
            sample_agents
        )

    # Seed sample customer
    cur.execute("SELECT COUNT(*) FROM customers")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO customers (name, phone, email, address, agent_id) VALUES (?, ?, ?, ?, ?)",
            ("Vijay Anand", "9840123456", "vijay@gmail.com", "12, Anna Nagar, Chennai", 1)
        )
        # Seed customer policy
        cur.execute(
            "INSERT INTO customer_policies (customer_id, policy_id, agent_id, start_date, status) VALUES (?, ?, ?, ?, ?)",
            (1, 1, 1, "2024-01-15", "Active")
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


@app.route("/api/policies")
def api_policies():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM policies ORDER BY id")
    policies = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(policies)


@app.route("/api/agents")
def api_agents():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM agents ORDER BY id")
    agents = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(agents)


@app.route("/api/customers")
def api_customers():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.*, a.name AS agent_name
        FROM customers c
        LEFT JOIN agents a ON c.agent_id = a.id
        ORDER BY c.id
    """)
    customers = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(customers)


@app.route("/api/customer_policies")
def api_customer_policies():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT cp.id, cp.start_date, cp.status,
               c.name AS customer_name, c.phone AS customer_phone,
               p.policy_name, p.policy_type, p.premium_amount, p.duration_years,
               a.name AS agent_name
        FROM customer_policies cp
        JOIN customers c ON cp.customer_id = c.id
        JOIN policies p ON cp.policy_id = p.id
        JOIN agents a ON cp.agent_id = a.id
        ORDER BY cp.id DESC
    """)
    records = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(records)


# ==========================================
# USER ROUTES
# ==========================================

@app.route("/submit_enquiry", methods=["POST"])
def submit_enquiry():
    customer_name = request.form["customer_name"].strip()
    phone = request.form["phone"].strip()
    policy_id = int(request.form["policy_id"])
    message = request.form["message"].strip()
    date_submitted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT policy_name, policy_type FROM policies WHERE id = ?", (policy_id,))
    pol = cur.fetchone()

    cur.execute("""
        INSERT INTO enquiries (customer_name, phone, policy_id, message, date_submitted)
        VALUES (?, ?, ?, ?, ?)
    """, (customer_name, phone, policy_id, message, date_submitted))
    enquiry_id = cur.lastrowid
    conn.commit()
    conn.close()

    return f"""
    <!DOCTYPE html><html><head><title>Enquiry Registered</title>{COMMON_STYLE}</head><body>
        <h2>Insurance Enquiry Submitted</h2>
        <div class="section">
            <p style="color: green; font-weight: bold;">Thank you! Your insurance enquiry has been logged successfully.</p>
            <table>
                <tr><th style="width: 200px;">Enquiry ID</th><td><b>#{enquiry_id}</b></td></tr>
                <tr><th>Customer Name</th><td>{customer_name}</td></tr>
                <tr><th>Phone Number</th><td>{phone}</td></tr>
                <tr><th>Inquired Policy</th><td>{pol['policy_name']} ({pol['policy_type']})</td></tr>
                <tr><th>Message</th><td>{message}</td></tr>
                <tr><th>Date</th><td>{date_submitted}</td></tr>
            </table>
        </div>
        <p><a href="/" class="btn">&laquo; Back to Insurance Home</a></p>
    </body></html>
    """


@app.route("/my_policies", methods=["POST"])
def my_policies():
    phone = request.form.get("phone", "").strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT cp.id, cp.start_date, cp.status,
               c.name AS customer_name, c.phone, c.email,
               p.policy_name, p.policy_type, p.premium_amount, p.duration_years,
               a.name AS agent_name, a.phone AS agent_phone
        FROM customer_policies cp
        JOIN customers c ON cp.customer_id = c.id
        JOIN policies p ON cp.policy_id = p.id
        JOIN agents a ON cp.agent_id = a.id
        WHERE c.phone = ?
        ORDER BY cp.id DESC
    """, (phone,))
    records = cur.fetchall()
    conn.close()

    rows = ""
    if records:
        for r in records:
            status_color = "green" if r['status'] == 'Active' else ("blue" if r['status'] == 'Matured' else "red")
            rows += f"""
            <tr>
                <td><b>#{r['id']}</b></td>
                <td><b>{r['policy_name']}</b></td>
                <td>{r['policy_type']}</td>
                <td>₹{r['premium_amount']:,.2f}</td>
                <td>{r['duration_years']} Yrs</td>
                <td>{r['start_date']}</td>
                <td>{r['agent_name']} ({r['agent_phone']})</td>
                <td style="color: {status_color}; font-weight: bold;">{r['status']}</td>
            </tr>
            """
    else:
        rows = "<tr><td colspan='8' style='text-align:center;'>No insurance policy records found for phone: " + phone + "</td></tr>"

    return f"""
    <!DOCTYPE html><html><head><title>My Insurance Policies</title>{COMMON_STYLE}</head><body>
        <h2>Personal Insurance Policies & Status</h2>
        <p>Customer Records for Phone: <b>{phone}</b></p>
        <table>
            <tr><th>Policy ID</th><th>Policy Name</th><th>Type</th><th>Annual Premium</th><th>Duration</th><th>Start Date</th><th>Agent</th><th>Status</th></tr>
            {rows}
        </table>
        <br>
        <p><a href="/" class="btn">&laquo; Back to Insurance Home</a></p>
    </body></html>
    """


# ==========================================
# AGENT ROUTES
# ==========================================

@app.route("/agent/add_customer", methods=["POST"])
def agent_add_customer():
    name = request.form["name"].strip()
    phone = request.form["phone"].strip()
    email = request.form["email"].strip()
    address = request.form["address"].strip()
    agent_id = int(request.form["agent_id"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO customers (name, phone, email, address, agent_id) VALUES (?, ?, ?, ?, ?)",
        (name, phone, email, address, agent_id)
    )
    conn.commit()
    conn.close()
    return redirect("/#agent-section")


@app.route("/agent/issue_policy", methods=["POST"])
def agent_issue_policy():
    customer_id = int(request.form["customer_id"])
    policy_id = int(request.form["policy_id"])
    agent_id = int(request.form["agent_id"])
    start_date = request.form["start_date"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO customer_policies (customer_id, policy_id, agent_id, start_date, status) VALUES (?, ?, ?, ?, 'Active')",
        (customer_id, policy_id, agent_id, start_date)
    )
    conn.commit()
    conn.close()
    return redirect("/#agent-section")


@app.route("/agent/update_policy_status", methods=["POST"])
def agent_update_policy_status():
    record_id = int(request.form["record_id"])
    status = request.form["status"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE customer_policies SET status = ? WHERE id = ?", (status, record_id))
    conn.commit()
    conn.close()
    return redirect("/#agent-section")


# ==========================================
# ADMIN ROUTES
# ==========================================

@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM agents ORDER BY id")
    agents = cur.fetchall()

    cur.execute("""
        SELECT c.*, a.name AS agent_name
        FROM customers c
        LEFT JOIN agents a ON c.agent_id = a.id
        ORDER BY c.id
    """)
    customers = cur.fetchall()

    cur.execute("SELECT * FROM policies ORDER BY id")
    policies = cur.fetchall()

    cur.execute("""
        SELECT cp.id, cp.start_date, cp.status,
               c.name AS customer_name, c.phone,
               p.policy_name, p.premium_amount,
               a.name AS agent_name
        FROM customer_policies cp
        JOIN customers c ON cp.customer_id = c.id
        JOIN policies p ON cp.policy_id = p.id
        JOIN agents a ON cp.agent_id = a.id
        ORDER BY cp.id DESC
    """)
    records = cur.fetchall()

    cur.execute("""
        SELECT e.*, p.policy_name
        FROM enquiries e
        LEFT JOIN policies p ON e.policy_id = p.id
        ORDER BY e.id DESC
    """)
    enquiries = cur.fetchall()
    conn.close()

    # Agents rows
    agent_rows = "".join([f"<tr><td>{a['id']}</td><td><b>{a['name']}</b></td><td>{a['phone']}</td><td>{a['email']}</td><td>{a['region']}</td></tr>" for a in agents])

    # Customers rows
    cust_rows = "".join([f"<tr><td>{c['id']}</td><td><b>{c['name']}</b></td><td>{c['phone']}</td><td>{c['email']}</td><td>{c['address']}</td><td>{c['agent_name']}</td></tr>" for c in customers])

    # Policies rows
    policy_rows = "".join([f"<tr><td>{p['id']}</td><td><b>{p['policy_name']}</b></td><td>{p['policy_type']}</td><td>{p['description']}</td><td>₹{p['premium_amount']:,.2f}</td><td>{p['duration_years']} Years</td></tr>" for p in policies])
    policy_opts = "".join([f'<option value="{p["id"]}">#{p["id"]} - {p["policy_name"]} (₹{p["premium_amount"]}/yr)</option>' for p in policies])

    # Records rows
    record_rows = "".join([f"<tr><td>#{r['id']}</td><td>{r['customer_name']} ({r['phone']})</td><td>{r['policy_name']}</td><td>₹{r['premium_amount']:,.2f}</td><td>{r['start_date']}</td><td>{r['agent_name']}</td><td><b>{r['status']}</b></td></tr>" for r in records]) if records else "<tr><td colspan='7'>No customer policy records.</td></tr>"

    # Enquiry rows
    enquiry_rows = "".join([f"<tr><td>#{e['id']}</td><td>{e['customer_name']}</td><td>{e['phone']}</td><td>{e['policy_name']}</td><td>{e['message']}</td><td>{e['date_submitted']}</td></tr>" for e in enquiries]) if enquiries else "<tr><td colspan='6'>No enquiries.</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Insurance Admin Panel</title>
        {COMMON_STYLE}
    </head>
    <body>
        <h1>INSURANCE SYSTEM ADMIN PANEL</h1>
        <p><a href="/" class="btn">&laquo; Back to Customer / Agent Portal</a></p>
        <hr>

        <!-- 1. All Agents -->
        <h2>1. All Insurance Agents</h2>
        <div class="section">
            <table>
                <tr><th>ID</th><th>Agent Name</th><th>Phone</th><th>Email</th><th>Region</th></tr>
                {agent_rows}
            </table>
        </div>

        <!-- 2. All Customers -->
        <h2>2. All Registered Customers</h2>
        <div class="section">
            <table>
                <tr><th>ID</th><th>Customer Name</th><th>Phone</th><th>Email</th><th>Address</th><th>Assigned Agent</th></tr>
                {cust_rows}
            </table>
        </div>

        <!-- 3. All Insurance Policies -->
        <h2>3. Insurance Policies Catalog</h2>
        <div class="section">
            <table>
                <tr><th>ID</th><th>Policy Name</th><th>Type</th><th>Description</th><th>Premium Amount</th><th>Duration</th></tr>
                {policy_rows}
            </table>
        </div>

        <!-- 4. Add New Policy -->
        <h2>4. Add New Insurance Policy</h2>
        <div class="section">
            <form action="/admin/add_policy" method="post">
                <label>Policy Name:</label>
                <input type="text" name="policy_name" required><br>
                <label>Policy Type:</label>
                <input type="text" name="policy_type" placeholder="e.g. Health, Life, Vehicle" required><br>
                <label>Description:</label>
                <textarea name="description" rows="2" style="width: 280px;" required></textarea><br>
                <label>Premium Amount (₹):</label>
                <input type="number" step="0.01" name="premium_amount" required><br>
                <label>Duration (Years):</label>
                <input type="number" name="duration_years" min="1" required><br>
                <input type="submit" value="Add Policy">
            </form>
        </div>

        <!-- 5. Update Policy Details -->
        <h2>5. Update Policy Details</h2>
        <div class="section">
            <form action="/admin/update_policy" method="post">
                <label>Select Policy:</label>
                <select name="policy_id" style="width: 420px;" required>
                    <option value="">-- Select Policy to Update --</option>
                    {policy_opts}
                </select><br>
                <label>Updated Description:</label>
                <textarea name="description" rows="2" style="width: 280px;" required></textarea><br>
                <label>Updated Premium (₹):</label>
                <input type="number" step="0.01" name="premium_amount" required><br>
                <label>Updated Duration (Yrs):</label>
                <input type="number" name="duration_years" min="1" required><br>
                <input type="submit" value="Update Policy">
            </form>
        </div>

        <!-- 6. View Policy Records & Enquiries -->
        <h2>6. Policy Records & Customer Enquiries</h2>
        <div class="section">
            <h3>Active / Registered Policy Records</h3>
            <table>
                <tr><th>Record ID</th><th>Customer</th><th>Policy</th><th>Premium</th><th>Start Date</th><th>Agent</th><th>Status</th></tr>
                {record_rows}
            </table>

            <h3 style="margin-top: 25px;">Customer Policy Enquiries</h3>
            <table>
                <tr><th>Enquiry ID</th><th>Customer</th><th>Phone</th><th>Policy</th><th>Message</th><th>Date Submitted</th></tr>
                {enquiry_rows}
            </table>
        </div>
    </body>
    </html>
    """


@app.route("/admin/add_policy", methods=["POST"])
def admin_add_policy():
    policy_name = request.form["policy_name"].strip()
    policy_type = request.form["policy_type"].strip()
    description = request.form["description"].strip()
    premium_amount = float(request.form["premium_amount"])
    duration_years = int(request.form["duration_years"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO policies (policy_name, policy_type, description, premium_amount, duration_years) VALUES (?, ?, ?, ?, ?)",
        (policy_name, policy_type, description, premium_amount, duration_years)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/update_policy", methods=["POST"])
def admin_update_policy():
    policy_id = int(request.form["policy_id"])
    description = request.form["description"].strip()
    premium_amount = float(request.form["premium_amount"])
    duration_years = int(request.form["duration_years"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE policies SET description = ?, premium_amount = ?, duration_years = ? WHERE id = ?",
        (description, premium_amount, duration_years, policy_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
