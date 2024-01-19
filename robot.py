from buildhat import MotorPair, Motor
from picamera2 import Picamera2
import RPi.GPIO as GPIO
from time import sleep
import threading

class Robot:
    def __init__(self):
        # MotorPair hat bei unseren Testst dazu geführt, dass der eine Motor viel langsamer war
        self.motor_left_1 = Motor("A")
        self.motor_left_2 = Motor("B")
        self.motor_right_1 = Motor("C")
        self.motor_right_2 = Motor("D")

        #self.steering = Motor("C")
        self.camera = Picamera2()
        self.speed = 0
        # Startet den Buzzer
        self.LED_PIN = 21
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.LED_PIN, GPIO.OUT, initial=GPIO.LOW)

    #  Setzt die Geschwindigkeit vom linken Motor (Werte von -100 bis 100)
    #  Diese Funktion existiert, da die Geschwindigkeit aufgrund der räumlichen Positionierung des Motors
    #  negativ für eine Bewegung vorwärts sein muss
    def set_left_speed(self, speed):
        self.motor_left_1.start(speed * (-1))
        self.motor_left_2.start(speed * (-1))


    #  Setzt die Geschwindigkeit vom linken Motor (Werte von -100 bis 100)
    def set_right_speed(self, speed):
        self.motor_right_1.start(speed)
        self.motor_right_2.start(speed)

    # Setzt die Geschwindigkeit beider Motoren und merk sich die eingestellte Geschwindigkeit
    def set_speed(self, x):
        self.speed = x
        self.set_left_speed(x)
        self.set_right_speed(x)
        
    # Dreht den Roboter je nach gegebenem Wert von -100 (links) und 100 (rechts) 
    def turn(self, x):
        speed_left = x
        speed_right = -x
        if x == 0:
            speed_left, speed_right = self.speed, self.speed
        self.set_left_speed(speed_left)
        self.set_right_speed(speed_right)
    
    # Lenkt den Roboter indem es den entsprechenden Motor um 1 - x Protzent verlangsamt
    def steer(self, x):
        percentage = -30 #self.speed * (1 - abs(x/100))
        if x < 0:
            self.set_left_speed(percentage)
            self.set_right_speed(self.speed)
        else:
            self.set_left_speed(self.speed)
            self.set_right_speed(percentage)
        
    def stop_motors(self):
        self.motor_left_1.stop()
        self.motor_left_2.stop()
        self.motor_right_1.stop()
        self.motor_right_2.stop()


    
    # Dreht die Lenkung je nach gegebenem Wert von -100 (links) bis 100(rechts)
    """def steer(self, x):
        degrees = round(-0.5*x)
        self.steering.run_to_position(degrees)
        
        #erster Test, Prozent Geschwindigkeitunterschied aus Gradzahl
        percentage = x*2.0                 
        
        limit_low = 30 if self.speed >= 0 else -100
        limit_high = 100 if self.speed >= 0 else -30
        
        # es fehlt min und max
        wheel_left_speed = min(max(limit_low, self.speed * (1+percentage/100)), limit_high)
        wheel_right_speed = min(max(limit_low, self.speed * (1-percentage/100)), limit_high)
        
        self.set_left_speed(wheel_left_speed)
        self.set_right_speed(wheel_right_speed)"""

    # Die Funktion, die die light_for_seconds Funktion als Thread startet
    def _light_for_seconds(self, seconds):
        print("Led on")
        GPIO.output(self.LED_PIN, GPIO.HIGH)
        sleep(seconds)
        GPIO.output(self.LED_PIN, GPIO.LOW)

    # Piepst für  x Sekunden
    def light_for_seconds(self, seconds):
        beep_thread = threading.Thread(target = self._light_for_seconds, args = (seconds, ))
        beep_thread.start()
        
    def test_motors(self):
        for x in range(-100, 100, 10):
            print(f"speed = {x}")
            self.set_speed(x)
            sleep(5)
            
if __name__ == "__main__":
    print("Remote Controller: Steuerung nach links und rechts, gebe Werte von -100 bis 100 ein")
    robot = Robot()
    robot.light_for_seconds(10)
    robot.set_speed(50)
    #robot.test_motors()
    #steering_target = 0
    #steering_thread = threading.Thread(target = lambda robot: (robot.steer(steering_target)), daemon=True, args=(robot,))
    #steering_thread.start()
    try:
       while True:
        try:        
            a = int(input())
        except ValueError:
            print("Ungültige Nummer, gebe eine Nummer von -100 bis 100 ein")
            continue
        robot.steer(a)
        #robot.steering.run_to_position(int(input()), speed = 100)
    except KeyboardInterrupt:
        #steering_thread.join()
        robot.stop_motors()
        
