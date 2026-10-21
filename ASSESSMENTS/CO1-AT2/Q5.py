from http.server import BaseHTTPRequestHandler, HTTPServer

class MyServer(BaseHTTPRequestHandler):

    def do_GET(self):
        print("HTTP Request received from browser")
        print("Path:", self.path)

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        self.wfile.write(b"""
        <html>
        <body>
        <h1>Hello from Server</h1>
        <p>Browser-Server Communication Successful</p>
        </body>
        </html>
        """)

server = HTTPServer(("localhost", 8000), MyServer)

print("Server started at http://localhost:8000")
server.serve_forever()