from http.server import BaseHTTPRequestHandler, HTTPServer

class MyServer(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", "-150")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        self.wfile.write(b"<html><body>Hello</body></html>")

server = HTTPServer(("localhost", 8000), MyServer)

print("Server running at http://localhost:8000")
server.serve_forever()