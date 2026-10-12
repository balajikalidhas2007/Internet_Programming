import os
import sqlite3
from flask import Flask, request, send_file, redirect, url_for

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "cake.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "cake.html")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            cake_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Ordered',
            FOREIGN KEY (cake_id) REFERENCES cakes(id)
        )
    """)
    # Insert sample cakes if empty
    cur.execute("SELECT COUNT(*) FROM cakes")
    if cur.fetchone()[0] == 0:
        sample_cakes = [
            ("Chocolate Truffle", "Birthday", "Rich dark chocolate layered sponge cake", 450.0, 10),
            ("Red Velvet", "Anniversary", "Classic red velvet with cream cheese frosting", 550.0, 8),
            ("Black Forest", "Celebration", "Whipped cream and cherry chocolate cake", 400.0, 15),
            ("Pineapple Delight", "Fruit", "Fresh pineapple slices layered sponge cake", 350.0, 12),
            ("Butterscotch Crunch", "Party", "Crunchy butterscotch praline with caramel drip", 380.0, 10),
        ]
        cur.executemany(
            "INSERT INTO cakes (name, category, description, price, quantity) VALUES (?, ?, ?, ?, ?)",
            sample_cakes,
        )
    conn.commit()
    conn.close()


# ---------- Routes ----------

@app.route("/")
def home():
    return send_file(HTML_PATH)


@app.route("/cakes_list")
def cakes_list():
    """Return HTML table rows for cakes list."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cakes")
    cakes = cur.fetchall()
    conn.close()

    html = "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>ID</th><th>Cake Name</th><th>Category</th><th>Description</th><th>Price (₹)</th><th>Available Qty</th><th>Action</th></tr>"
    for c in cakes:
        html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td><button type='button' onclick=\"selectCake({}, '{}', {})\">Select Cake</button></td></tr>".format(
            c["id"], c["name"], c["category"], c["description"], c["price"], c["quantity"],
            c["id"], c["name"].replace("'", ""), c["price"]
        )
    html += "</table>"
    return html


@app.route("/cakes_options")
def cakes_options():
    """Return dropdown options for cake selection."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, quantity FROM cakes WHERE quantity > 0")
    cakes = cur.fetchall()
    conn.close()

    options = ""
    for c in cakes:
        options += '<option value="{}">{} - ₹{} (Available: {})</option>\n'.format(
            c["id"], c["name"], c["price"], c["quantity"]
        )
    return options


@app.route("/place_order", methods=["POST"])
def place_order():
    customer_name = request.form["customer_name"].strip()
    phone = request.form["phone"].strip()
    address = request.form["address"].strip()
    cake_id = int(request.form["cake_id"])
    quantity = int(request.form["quantity"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cakes WHERE id = ?", (cake_id,))
    cake = cur.fetchone()

    if cake is None:
        conn.close()
        return "<h3>Error: Cake not found.</h3><br><a href='/'>Go Back</a>"

    if cake["quantity"] < quantity:
        conn.close()
        return "<h3>Error: Not enough quantity available. Only {} left.</h3><br><a href='/'>Go Back</a>".format(
            cake["quantity"]
        )

    total_price = cake["price"] * quantity

    cur.execute(
        "INSERT INTO orders (customer_name, phone, address, cake_id, quantity, total_price, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (customer_name, phone, address, cake_id, quantity, total_price, "Ordered"),
    )
    order_id = cur.lastrowid

    cur.execute(
        "UPDATE cakes SET quantity = quantity - ? WHERE id = ?",
        (quantity, cake_id),
    )
    conn.commit()
    conn.close()

    return """
    <h2>Order Placed Successfully!</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr><td><b>Order ID</b></td><td>{}</td></tr>
        <tr><td><b>Customer Name</b></td><td>{}</td></tr>
        <tr><td><b>Phone</b></td><td>{}</td></tr>
        <tr><td><b>Address</b></td><td>{}</td></tr>
        <tr><td><b>Cake</b></td><td>{}</td></tr>
        <tr><td><b>Quantity</b></td><td>{}</td></tr>
        <tr><td><b>Total Price</b></td><td>₹{}</td></tr>
        <tr><td><b>Shipping Status</b></td><td>Ordered</td></tr>
    </table>
    <br><a href="/">Go Back to Home</a>
    """.format(order_id, customer_name, phone, address, cake["name"], quantity, total_price)


@app.route("/my_orders", methods=["POST"])
def my_orders():
    phone = request.form.get("phone", "").strip()

    conn = get_db()
    cur = conn.cursor()
    if phone:
        cur.execute("""
            SELECT o.id, o.customer_name, o.phone, c.name AS cake_name, o.quantity, o.total_price, o.status
            FROM orders o
            JOIN cakes c ON o.cake_id = c.id
            WHERE o.phone = ?
            ORDER BY o.id DESC
        """, (phone,))
    else:
        cur.execute("""
            SELECT o.id, o.customer_name, o.phone, c.name AS cake_name, o.quantity, o.total_price, o.status
            FROM orders o
            JOIN cakes c ON o.cake_id = c.id
            ORDER BY o.id DESC
        """)
    orders = cur.fetchall()
    conn.close()

    if not orders:
        return "<p>No orders found.</p><br><a href='/'>Go Back</a>"

    html = "<h2>My Orders</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Order ID</th><th>Customer</th><th>Phone</th><th>Cake</th><th>Quantity</th><th>Total (₹)</th><th>Status</th></tr>"
    for o in orders:
        html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td><b>{}</b></td></tr>".format(
            o["id"], o["customer_name"], o["phone"], o["cake_name"], o["quantity"], o["total_price"], o["status"]
        )
    html += "</table>"
    html += "<br><a href='/'>Go Back</a>"
    return html


# ---------- Admin Routes ----------

@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM cakes")
    cakes = cur.fetchall()

    cur.execute("""
        SELECT o.id, o.customer_name, o.phone, o.address, c.name AS cake_name, o.quantity, o.total_price, o.status
        FROM orders o
        JOIN cakes c ON o.cake_id = c.id
        ORDER BY o.id DESC
    """)
    orders = cur.fetchall()
    conn.close()

    html = "<h1>Admin Panel - Cake Ordering System</h1>"

    # View Cakes Table
    html += "<h2>1. Cake Inventory</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>ID</th><th>Cake Name</th><th>Category</th><th>Description</th><th>Price (₹)</th><th>Available Quantity</th></tr>"
    for c in cakes:
        html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            c["id"], c["name"], c["category"], c["description"], c["price"], c["quantity"]
        )
    html += "</table>"

    # Add Cake Form
    html += "<br><hr>"
    html += "<h2>2. Add New Cake</h2>"
    html += """
    <form action="/admin/add_cake" method="post">
        Cake Name: <input type="text" name="name" required><br><br>
        Category: <input type="text" name="category" required><br><br>
        Description: <input type="text" name="description" required><br><br>
        Price (₹): <input type="number" step="0.01" name="price" required><br><br>
        Quantity: <input type="number" name="quantity" required><br><br>
        <input type="submit" value="Add Cake">
    </form>
    """

    # Update Cake Price / Quantity Form
    html += "<br><hr>"
    html += "<h2>3. Update Cake Price / Quantity</h2>"
    html += """
    <form action="/admin/update_cake" method="post">
        Select Cake:
        <select name="cake_id" required>
    """
    for c in cakes:
        html += '<option value="{}">{} (Current Price: ₹{}, Qty: {})</option>'.format(
            c["id"], c["name"], c["price"], c["quantity"]
        )
    html += """
        </select><br><br>
        New Price (₹): <input type="number" step="0.01" name="price" required><br><br>
        New Quantity: <input type="number" name="quantity" required><br><br>
        <input type="submit" value="Update Cake">
    </form>
    """

    # View Orders Table
    html += "<br><hr>"
    html += "<h2>4. Customer Orders</h2>"
    if orders:
        html += "<table border='1' cellpadding='5' cellspacing='0'>"
        html += "<tr><th>Order ID</th><th>Customer</th><th>Phone</th><th>Address</th><th>Cake</th><th>Qty</th><th>Total (₹)</th><th>Shipping Status</th></tr>"
        for o in orders:
            html += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td><b>{}</b></td></tr>".format(
                o["id"], o["customer_name"], o["phone"], o["address"], o["cake_name"], o["quantity"], o["total_price"], o["status"]
            )
        html += "</table>"
    else:
        html += "<p>No orders placed yet.</p>"

    # Update Order Shipping Status Form
    html += "<br><hr>"
    html += "<h2>5. Update Order Shipping Status</h2>"
    if orders:
        html += """
        <form action="/admin/update_status" method="post">
            Select Order:
            <select name="order_id" required>
        """
        for o in orders:
            html += '<option value="{}">Order #{} - {} ({}) - Status: {}</option>'.format(
                o["id"], o["id"], o["customer_name"], o["cake_name"], o["status"]
            )
        html += """
            </select><br><br>
            New Shipping Status:
            <select name="status" required>
                <option value="Ordered">Ordered</option>
                <option value="Packed">Packed</option>
                <option value="Shipped">Shipped</option>
                <option value="Delivered">Delivered</option>
            </select><br><br>
            <input type="submit" value="Update Shipping Status">
        </form>
        """
    else:
        html += "<p>No orders available to update.</p>"

    html += "<br><hr><a href='/'>Go Back to Home</a>"
    return html


@app.route("/admin/add_cake", methods=["POST"])
def add_cake():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO cakes (name, category, description, price, quantity) VALUES (?, ?, ?, ?, ?)",
        (
            request.form["name"].strip(),
            request.form["category"].strip(),
            request.form["description"].strip(),
            float(request.form["price"]),
            int(request.form["quantity"]),
        ),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/update_cake", methods=["POST"])
def update_cake():
    cake_id = int(request.form["cake_id"])
    price = float(request.form["price"])
    quantity = int(request.form["quantity"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE cakes SET price = ?, quantity = ? WHERE id = ?",
        (price, quantity, cake_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/update_status", methods=["POST"])
def update_status():
    order_id = int(request.form["order_id"])
    status = request.form["status"].strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
