from INA219 import INA219
import time
import bluetooth
time.sleep(5)

#Initialisieren der Klasse zum Auslesen des Akkus
ina219 = INA219(addr=0x42) 
#str click auf das import-statement, in line 195 sind die Funktionen zum Auslesen der Daten beschrieben




hostMACAddress = '7c:b2:7d:59:96:10' # The MAC address of a Bluetooth adapter on the server. The server might have multiple Bluetooth adapters.
port = 3
backlog = 1
size = 1024
s = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
s.bind((hostMACAddress, port))
s.listen(backlog)
try:
    client, clientInfo = s.accept()
    while 1:
        data = client.recv(size)
        if data:
            print(data)
            client.send(data) # Echo back to client
except:
    print("Closing socket")
    client.close()
    s.close()