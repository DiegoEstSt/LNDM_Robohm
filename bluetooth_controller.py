import socket
import tkinter as tk


class CONTROLLER:
    def __init__(self, root):
        self.window = root
        self.color = "white"
        self.window.configure(bg=self.color)
        self.window.geometry("100x100")

    def run(self):
        self.window.title("Controller")

        self.button_frame = tk.Frame(self.window, bg=self.color, width=10)
        self.button_frame.pack(expand=True, fill=tk.BOTH, side=tk.RIGHT)

        self.connect_button = tk.Button(self.button_frame, text="connect", command=self.connect)
        self.connect_button.pack(expand=True, padx=20, side=tk.TOP)

    def build_controlls(self):
        self.speed_frame = tk.Frame(self.window, bg=self.color)
        self.speed_frame.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)

        self.speed_left = tk.Scale(self.speed_frame, from_=100, to=-100, bg=self.color, highlightthickness=0)
        self.speed_left.bind("<ButtonRelease-1>", self.update_left_speed)
        self.speed_left.pack(side=tk.LEFT, fill=tk.Y, expand=True)

        self.speed_right = tk.Scale(self.speed_frame, from_=100, to=-100, bg=self.color, highlightthickness=0)
        self.speed_right.bind("<ButtonRelease-1>", self.update_right_speed)
        self.speed_right.pack(fill=tk.Y, expand=True, side=tk.RIGHT)

    def connect(self):
        try:
            serverMACAddress = 'DC:A6:32:E7:50:1F'
            port = 5
            self.s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.s.connect((serverMACAddress, port))
            self.button_frame.destroy()
            self.build_controlls()
        except:
            self.error_label = tk.Label(self.window, text="Etwas beim Aufbauen der Verbindung ist schiefgelaufen", bg=self.color)
            self.error_label.pack()

    def update_left_speed(self, speed):
        print(self.speed_left.get())
        self.s.send(bytes(f"l{speed}", "utf-8"))

    def update_right_speed(self, speed):
        print(self.speed_right.get())
        self.s.send(bytes(f"r{speed}", "utf-8"))

window = tk.Tk()
gui = CONTROLLER(window)
gui.run()
window.mainloop()



"""

while 0:
    text = input()
    if text == "quit":
        break
    s.send(bytes(text, 'UTF-8'))
s.close()
"""
