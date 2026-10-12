from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
from urllib.parse import urlparse, parse_qs

# create database and tables when server starts
conn = sqlite3.connect("library.db")
c = conn.cursor()

# books table
c.execute("""CREATE TABLE IF NOT EXISTS books (
    book_id TEXT,
    title TEXT,
    author TEXT,
    department TEXT,
    quantity INTEGER
)""")

# students table (separate db table for student details)
c.execute("""CREATE TABLE IF NOT EXISTS students (
    name TEXT,
    roll TEXT,
    email TEXT,
    department TEXT,
    year TEXT
)""")

conn.commit()
conn.close()

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/lab1.html":
            # serve the html page
            f = open("lab1.html", "r")
            content = f.read()
            f.close()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode())

        elif parsed.path == "/get_books":
            # fetch all books from database
            conn = sqlite3.connect("library.db")
            c = conn.cursor()
            c.execute("SELECT * FROM books")
            books = c.fetchall()
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(books).encode())

        elif parsed.path == "/search_book":
            # search book by title
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]

            conn = sqlite3.connect("library.db")
            c = conn.cursor()
            c.execute("SELECT * FROM books WHERE title LIKE ?", ("%" + query + "%",))
            results = c.fetchall()
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # read data from request
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length)
        data = json.loads(body)

        if self.path == "/add_book":
            # insert book into books table
            conn = sqlite3.connect("library.db")
            c = conn.cursor()
            c.execute("INSERT INTO books VALUES (?, ?, ?, ?, ?)",
                (data["book_id"], data["title"], data["author"], data["dept"], data["qty"]))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Book added successfully!"}).encode())

        elif self.path == "/register_student":
            # insert student into students table
            conn = sqlite3.connect("library.db")
            c = conn.cursor()
            c.execute("INSERT INTO students VALUES (?, ?, ?, ?, ?)",
                (data["name"], data["roll"], data["email"], data["dept"], data["year"]))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Student registered successfully!"}).encode())

print("Server running at http://localhost:8000")
print("Open http://localhost:8000/lab1.html")
server = HTTPServer(("localhost", 8000), MyHandler)
server.serve_forever()
