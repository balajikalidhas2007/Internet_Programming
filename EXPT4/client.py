import socket

client = socket.socket()

client.connect(("localhost", 9999))

a = input("Enter first number: ")
b = input("Enter second number: ")
op = input("Enter operator (+, -, *, /): ")

message = a + "|" + b + "|" + op
client.send(message.encode())

result = client.recv(1024).decode()

print("Result =", result)

client.close()