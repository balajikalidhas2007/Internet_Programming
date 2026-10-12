import socket

server = socket.socket()

server.bind(("localhost", 9999))
server.listen(1)

print("Server waiting...")

client, address = server.accept()
print("Client connected")

data = client.recv(1024).decode()
a, b, op = data.split("|")
a = int(a)
b = int(b)

if op == '+':
    result = a + b
elif op == '-':
    result = a - b
elif op == '*':
    result = a * b
elif op == '/':
    result = a / b
else:
    result = "Invalid operator"

client.send(str(result).encode())

client.close()
server.close()