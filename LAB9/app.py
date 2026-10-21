import os
import sqlite3
from datetime import datetime
from flask import Flask, request, send_file, redirect, url_for, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_CSS = os.path.join(BASE_DIR, "global.css")
DB_PATH = os.path.join(os.path.dirname(__file__), "electronics.db")
HTML_PATH = os.path.join(os.path.dirname(__file__), "electronics.html")

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
        CREATE TABLE IF NOT EXISTS products (
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
            total_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Ordered',
            order_date TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        sample_products = [
            ("Wireless Bluetooth Headphones", "Audio", "Over-ear noise cancelling headphones with deep bass", 2499.0, 15),
            ("Smart LED TV 43 Inch", "Television", "4K Ultra HD Smart Android TV with HDR10", 28999.0, 8),
            ("Gaming Laptop 16GB RAM", "Computers", "High performance Intel Core i7 laptop with RTX Graphics", 64999.0, 5),
            ("Optical Wireless Mouse", "Accessories", "Ergonomic 2.4GHz wireless optical mouse with USB receiver", 499.0, 30),
            ("Fast Charging Power Bank 20000mAh", "Mobile", "22.5W high speed Type-C charging power bank", 1499.0, 20),
            ("Smartwatch Fitness Tracker", "Wearables", "Heart rate and SpO2 monitor waterproof sports watch", 1999.0, 12)
        ]
        cur.executemany(
            "INSERT INTO products (name, category, description, price, quantity) VALUES (?, ?, ?, ?, ?)",
            sample_products
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


@app.route("/api/products")
def api_products():
    category = request.args.get("category", "").strip()
    conn = get_db()
    cur = conn.cursor()
    if category and category != "All":
        cur.execute("SELECT * FROM products WHERE category = ? ORDER BY id", (category,))
    else:
        cur.execute("SELECT * FROM products ORDER BY id")
    products = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(products)


@app.route("/place_order", methods=["POST"])
def place_order():
    product_id = int(request.form["product_id"])
    quantity = int(request.form["quantity"])
    customer_name = request.form["customer_name"].strip()
    phone = request.form["phone"].strip()
    address = request.form["address"].strip()

    if quantity <= 0:
        return f"""
        <!DOCTYPE html><html><head><title>Invalid Quantity</title>{COMMON_STYLE}</head><body>
            <h2>Invalid Order Quantity</h2>
            <p>Quantity must be 1 or more.</p>
            <p><a href="/" class="btn">&laquo; Go Back</a></p>
        </body></html>
        """

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cur.fetchone()

    if not product:
        conn.close()
        return f"""
        <!DOCTYPE html><html><head><title>Error</title>{COMMON_STYLE}</head><body>
            <h2>Error: Product not found!</h2>
            <p><a href="/" class="btn">&laquo; Go Back</a></p>
        </body></html>
        """

    # ORDER LOGIC: Check availability, do not allow orders exceeding stock
    if product["quantity"] < quantity:
        avail = product["quantity"]
        conn.close()
        return f"""
        <!DOCTYPE html><html><head><title>Insufficient Stock</title>{COMMON_STYLE}</head><body>
            <h2>Order Cannot Be Processed</h2>
            <div class="section" style="border-left: 4px solid #c0392b;">
                <p><b>Insufficient Stock:</b> You requested <b>{quantity}</b> units of <b>{product['name']}</b>, but only <b>{avail}</b> units are available.</p>
            </div>
            <p><a href="/" class="btn">&laquo; Go Back and Adjust Quantity</a></p>
        </body></html>
        """

    # Calculate total price
    total_price = round(product["price"] * quantity, 2)
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert order
    cur.execute("""
        INSERT INTO orders (customer_name, phone, address, total_price, status, order_date)
        VALUES (?, ?, ?, ?, 'Ordered', ?)
    """, (customer_name, phone, address, total_price, order_date))
    order_id = cur.lastrowid

    # Insert order_items
    cur.execute("""
        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (?, ?, ?, ?)
    """, (order_id, product_id, quantity, product["price"]))

    # Reduce product stock
    cur.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (quantity, product_id))

    conn.commit()
    conn.close()

    return f"""
    <!DOCTYPE html><html><head><title>Order Confirmed</title>{COMMON_STYLE}</head><body>
        <h2>Electronics Order Confirmed!</h2>
        <div class="section">
            <p style="color: green; font-weight: bold;">Thank you! Your order has been placed successfully.</p>
            <table>
                <tr><th style="width: 200px;">Order ID</th><td><b>#{order_id}</b></td></tr>
                <tr><th>Customer Name</th><td>{customer_name}</td></tr>
                <tr><th>Phone</th><td>{phone}</td></tr>
                <tr><th>Delivery Address</th><td>{address}</td></tr>
                <tr><th>Product</th><td>{product['name']} ({product['category']})</td></tr>
                <tr><th>Unit Price</th><td>₹{product['price']:.2f}</td></tr>
                <tr><th>Ordered Quantity</th><td>{quantity}</td></tr>
                <tr><th>Total Amount</th><td><b>₹{total_price:.2f}</b></td></tr>
                <tr><th>Order Date</th><td>{order_date}</td></tr>
                <tr><th>Status</th><td><span style="color: green; font-weight: bold;">Ordered</span></td></tr>
            </table>
        </div>
        <p><a href="/" class="btn">&laquo; Go Back to Store</a></p>
    </body></html>
    """


@app.route("/view_order_status", methods=["GET", "POST"])
def view_order_status():
    search = request.form.get("search", "").strip() if request.method == "POST" else request.args.get("search", "").strip()

    conn = get_db()
    cur = conn.cursor()

    query = """
        SELECT o.id, o.customer_name, o.phone, o.address, o.total_price, o.status, o.order_date,
               p.name AS product_name, p.category, oi.quantity, oi.price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
    """
    params = []

    if search:
        # Search by order ID or phone
        if search.isdigit() and len(search) < 6:
            query += " WHERE o.id = ? OR o.phone = ?"
            params = [int(search), search]
        else:
            query += " WHERE o.phone LIKE ?"
            params = [f"%{search}%"]

    query += " ORDER BY o.id DESC"
    cur.execute(query, params)
    orders = cur.fetchall()
    conn.close()

    rows = ""
    if orders:
        for o in orders:
            status_color = "green" if o['status'] == 'Ordered' else ("#d35400" if o['status'] == 'Shipped' else "#2980b9")
            rows += f"""
            <tr>
                <td><b>#{o['id']}</b></td>
                <td>{o['customer_name']}</td>
                <td>{o['phone']}</td>
                <td>{o['product_name']} (Qty: {o['quantity']})</td>
                <td>₹{o['total_price']:.2f}</td>
                <td>{o['order_date']}</td>
                <td style="color: {status_color}; font-weight: bold;">{o['status']}</td>
            </tr>
            """
    else:
        rows = "<tr><td colspan='7' style='text-align:center;'>No orders found.</td></tr>"

    return f"""
    <!DOCTYPE html><html><head><title>Order Status</title>{COMMON_STYLE}</head><body>
        <h2>Electronics Order Status</h2>
        <p>Showing search results {f'for: <b>{search}</b>' if search else '(All Orders)'}</p>
        <table>
            <tr><th>Order ID</th><th>Customer</th><th>Phone</th><th>Product</th><th>Total Amount</th><th>Date</th><th>Status</th></tr>
            {rows}
        </table>
        <br>
        <p><a href="/" class="btn">&laquo; Go Back to Store</a></p>
    </body></html>
    """


# ==========================================
# ADMIN ROUTES
# ==========================================

@app.route("/admin")
def admin():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products ORDER BY id")
    products = cur.fetchall()

    cur.execute("""
        SELECT o.id, o.customer_name, o.phone, o.address, o.total_price, o.status, o.order_date,
               p.name AS product_name, oi.quantity
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        ORDER BY o.id DESC
    """)
    orders = cur.fetchall()
    conn.close()

    # Product table rows
    prod_rows = "".join([
        f"<tr><td>{p['id']}</td><td><b>{p['name']}</b></td><td>{p['category']}</td><td>{p['description']}</td><td>₹{p['price']:.2f}</td><td>{p['quantity']}</td></tr>"
        for p in products
    ])

    # Options for update & delete
    prod_opts = "".join([f'<option value="{p["id"]}">#{p["id"]} - {p["name"]} (₹{p["price"]:.2f}, Stock: {p["quantity"]})</option>' for p in products])
    order_opts = "".join([f'<option value="{o["id"]}">Order #{o["id"]} - {o["customer_name"]} ({o["product_name"]}) - Status: {o["status"]}</option>' for o in orders])

    # Orders table rows
    if orders:
        order_rows = "".join([
            f"<tr><td>#{o['id']}</td><td>{o['customer_name']}</td><td>{o['phone']}</td><td>{o['address']}</td><td>{o['product_name']} (Qty: {o['quantity']})</td><td>₹{o['total_price']:.2f}</td><td>{o['order_date']}</td><td><b>{o['status']}</b></td></tr>"
            for o in orders
        ])
    else:
        order_rows = "<tr><td colspan='8'>No customer orders yet.</td></tr>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Electronics Admin Panel</title>
        {COMMON_STYLE}
    </head>
    <body>
        <h1>ELECTRONICS STORE ADMIN PANEL</h1>
        <p><a href="/" class="btn">&laquo; Back to Storefront</a></p>
        <hr>

        <!-- 1. View All Products -->
        <h2>1. Electronic Products Inventory</h2>
        <div class="section">
            <table>
                <tr><th>ID</th><th>Product Name</th><th>Category</th><th>Description</th><th>Price (₹)</th><th>Stock Qty</th></tr>
                {prod_rows}
            </table>
        </div>

        <!-- 2. Add New Product -->
        <h2>2. Add a New Product</h2>
        <div class="section">
            <form action="/admin/add_product" method="post">
                <label>Product Name:</label>
                <input type="text" name="name" required><br>
                <label>Category:</label>
                <input type="text" name="category" placeholder="e.g. Audio, Mobile, Television" required><br>
                <label>Description:</label>
                <textarea name="description" rows="2" style="width: 280px;" required></textarea><br>
                <label>Price (₹):</label>
                <input type="number" step="0.01" name="price" required><br>
                <label>Stock Quantity:</label>
                <input type="number" name="quantity" min="0" required><br>
                <input type="submit" value="Add Product">
            </form>
        </div>

        <!-- 3. Update Product Price and Quantity -->
        <h2>3. Update Product Price and Stock Quantity</h2>
        <div class="section">
            <form action="/admin/update_product" method="post">
                <label>Select Product:</label>
                <select name="product_id" style="width: 380px;" required>
                    <option value="">-- Select Product to Update --</option>
                    {prod_opts}
                </select><br>
                <label>New Price (₹):</label>
                <input type="number" step="0.01" name="price" required><br>
                <label>New Stock Quantity:</label>
                <input type="number" name="quantity" min="0" required><br>
                <input type="submit" value="Update Product">
            </form>
        </div>

        <!-- 4. Delete Product -->
        <h2>4. Delete a Product</h2>
        <div class="section">
            <form action="/admin/delete_product" method="post" onsubmit="return confirm('Are you sure you want to delete this product?');">
                <label>Select Product:</label>
                <select name="product_id" style="width: 380px;" required>
                    <option value="">-- Select Product to Delete --</option>
                    {prod_opts}
                </select><br>
                <input type="submit" value="Delete Product" style="background-color: #c0392b; border-color: #a93226;">
            </form>
        </div>

        <!-- 5. View Customer Orders -->
        <h2>5. Customer Orders</h2>
        <div class="section">
            <table>
                <tr><th>ID</th><th>Customer</th><th>Phone</th><th>Address</th><th>Item</th><th>Total</th><th>Date</th><th>Status</th></tr>
                {order_rows}
            </table>
        </div>

        <!-- 6. Update Order Status -->
        <h2>6. Update Order Status</h2>
        <div class="section">
            <form action="/admin/update_order_status" method="post">
                <label>Select Order:</label>
                <select name="order_id" style="width: 380px;" required>
                    <option value="">-- Select Order --</option>
                    {order_opts}
                </select><br>
                <label>Fulfillment Status:</label>
                <select name="status" required>
                    <option value="Ordered">Ordered</option>
                    <option value="Shipped">Shipped</option>
                    <option value="Delivered">Delivered</option>
                </select><br>
                <input type="submit" value="Update Order Status">
            </form>
        </div>
    </body>
    </html>
    """


@app.route("/admin/add_product", methods=["POST"])
def admin_add_product():
    name = request.form["name"].strip()
    category = request.form["category"].strip()
    description = request.form["description"].strip()
    price = float(request.form["price"])
    quantity = int(request.form["quantity"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products (name, category, description, price, quantity) VALUES (?, ?, ?, ?, ?)",
        (name, category, description, price, quantity)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/update_product", methods=["POST"])
def admin_update_product():
    product_id = int(request.form["product_id"])
    price = float(request.form["price"])
    quantity = int(request.form["quantity"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE products SET price = ?, quantity = ? WHERE id = ?", (price, quantity, product_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/delete_product", methods=["POST"])
def admin_delete_product():
    product_id = int(request.form["product_id"])

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/update_order_status", methods=["POST"])
def admin_update_order_status():
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
