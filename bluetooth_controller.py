"""import bluetooth

server_mac_address = "7c:b2:7d:59:96:10"
port = 3
s = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
s.connect((server_mac_address, port))
while 1:
    text = input()
    if text == "quit":
        break
    s.send(text)
s.close()"""

import socket

serverMACAddress = 'DC:A6:32:E7:50:1F'
port = 5
s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
s.connect((serverMACAddress, port))
while 1:
    text = input()
    if text == "quit":
        break
    s.send(bytes(text, 'UTF-8'))
s.close()
