from buildhat import Motor, MotorPair
from picamera2 import Picamera2

class Robot:
    def __init__(self):
        self.motor_left = Motor("B")
        self.motor_right = Motor("A")
        self.camera = Picamera2()
        self.camera.start()

    def get_image(self):
        return self.camera.capture_array("main")
