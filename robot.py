from buildhat import MotorPair, Motor
from picamera2 import Picamera2
import RPi.GPIO as GPIO
from time import sleep
import threading
import sys
import time

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
        self.LED_PIN = 18
        
        self.DIST_SENSOR_FRONT_ECHO_PIN = 23
        self.DIST_SENSOR_FRONT_TRIGGER_PIN = 24

        self.DIST_SENSOR_RIGHT_ECHO_PIN = 20
        self.DIST_SENSOR_RIGHT_TRIGGER_PIN = 21

        self.DIST_SENSOR_LEFT_ECHO_PIN = 25
        self.DIST_SENSOR_LEFT_TRIGGER_PIN = 8

        self.dist_left = 0
        self.dist_front = 0
        self.dist_right = 0
        self.dist_measuring = False
        #self.dist_sensors = threading.Thread(target=self.measure_dists)

         # Speichert, ob die LED gerade an oder aus geschalten ist
        self.led_status = 1
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.LED_PIN, GPIO.OUT, initial=GPIO.LOW)

    # Initialisiert die Ultraschall Sensoren
    def start_dist_sensors(self):
        GPIO.setup(self.DIST_SENSOR_FRONT_TRIGGER_PIN , GPIO.OUT)
        GPIO.setup(self.DIST_SENSOR_FRONT_ECHO_PIN, GPIO.IN)
        GPIO.setup(self.DIST_SENSOR_LEFT_TRIGGER_PIN , GPIO.OUT)
        GPIO.setup(self.DIST_SENSOR_LEFT_ECHO_PIN, GPIO.IN)
        GPIO.setup(self.DIST_SENSOR_RIGHT_TRIGGER_PIN , GPIO.OUT)
        GPIO.setup(self.DIST_SENSOR_RIGHT_ECHO_PIN, GPIO.IN)
        self.dist_measuring = True
        #self.dist_sensors.start()

    def measure_dist_left(self):
        distance = self.measure_dist(self.DIST_SENSOR_LEFT_ECHO_PIN, self.DIST_SENSOR_LEFT_TRIGGER_PIN)
        self.dist_left = distance
        return distance

    def measure_dist_front(self):
        distance = self.measure_dist(self.DIST_SENSOR_FRONT_ECHO_PIN, self.DIST_SENSOR_FRONT_TRIGGER_PIN)
        self.dist_front = distance
        return distance
    
    def measure_dist_right(self):
        distance = self.measure_dist(self.DIST_SENSOR_RIGHT_ECHO_PIN, self.DIST_SENSOR_RIGHT_TRIGGER_PIN)
        self.dist_right = distance
        return distance
    
    def measure_dist(self, echo, trigger):
        # set Trigger to HIGH
        GPIO.output(trigger, True)
        
        # set Trigger after 0.01ms to LOW
        time.sleep(0.00001)
        GPIO.output(trigger, False)
        
        start_time = time.time()
        stop_time = time.time()
        
        # save start_time
        while GPIO.input(echo) == 0  or not self.dist_measuring:
            if time.time() - start_time > 1:
                return None 

        start_time = time.time()
        
        # save time of arrival
        while GPIO.input(echo) == 1  or not self.dist_measuring:
            if time.time() - start_time > 1:
                return None 
            
        stop_time = time.time()
        
        # time difference between start and arrival
        TimeElapsed = stop_time - start_time
        # multiply with the sonic speed (34300 cm/s)
        # and divide by 2, because there and back
        distance = (TimeElapsed * 34300) / 2
        return distance



    """def measure_dists(self):
        print("started")
        while self.dist_measuring:
            print("measuring")

             # set Trigger to HIGH
            GPIO.output(self.DIST_SENSOR_FRONT_TRIGGER_PIN, True)
        
            # set Trigger after 0.01ms to LOW
            time.sleep(0.00001)
            GPIO.output(self.DIST_SENSOR_FRONT_TRIGGER_PIN, False)
        
            start_time = time.time()
            stop_time = time.time()
        
            # save start_time
            while GPIO.input(self.DIST_SENSOR_FRONT_ECHO_PIN) == 0  or not self.measure_dists:
                print("waiting for start")
                start_time = time.time()
        
            # save time of arrival
            while GPIO.input(self.DIST_SENSOR_FRONT_ECHO_PIN) == 1  or not self.measure_dists:
                print("Still waiting")
                stop_time = time.time()
        
            # time difference between start and arrival
            TimeElapsed = stop_time - start_time
            # multiply with the sonic speed (34300 cm/s)
            # and divide by 2, because there and back
            distance = (TimeElapsed * 34300) / 2
            print(distance)
            sleep(1)"""
    
    def stop_dist_sensors(self):
        self.measure_dists = False
        #self.dist_sensors.join()

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
        percentage = self.speed * (1 - abs(x/100))
        if x < 0:
            if percentage < 1:
                self.stop_left_motors()
            else:
                self.set_left_speed(percentage)
            self.set_right_speed(self.speed)

        elif x > 0:
            if percentage < 1:
                self.stop_right_motors()
            else:
                self.set_right_speed(percentage)
            self.set_left_speed(self.speed)
        else:
            self.set_speed(self.speed)

    # Dreht den Roboter im Zweifelsfall um weniger als 90°
    def turn_90_degrees(self, direction):
        self.stop_motors()
        if direction == "left":
            self.set_left_speed(-100)
            self.set_right_speed(100)
        if direction == "right":
            self.set_left_speed(100)
            self.set_right_speed(-100)
        sleep(2)
        self.stop_motors()


    # Dreht den Roboter im Zweifelsfall um mehr als 90°
    def turn_90_degrees_hard(self, direction):
        self.stop_motors()
        if direction == "left":
            self.set_left_speed(-100)
            self.set_right_speed(100)
        if direction == "right":
            self.set_left_speed(100)
            self.set_right_speed(-100)
        sleep(2.1)
        self.stop_motors()

    def drive_around_edge(self):
        self.set_speed(100)
        sleep(2)
        self.turn_90_degrees_hard("left")
        self.stop_motors()
        self.set_speed(100)
        sleep(1)
        self.stop_motors()

    def stop_left_motors(self):
        self.motor_left_1.stop()
        self.motor_left_2.stop()
    
    def stop_right_motors(self):
        self.motor_right_1.stop()
        self.motor_right_2.stop()

    def stop_motors(self):
        self.stop_left_motors()
        self.stop_right_motors()




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
        self.led_status = True
        sleep(seconds)
        GPIO.output(self.LED_PIN, GPIO.LOW)
        self.led_status = False

    # Piepst für  x Sekunden
    def light_for_seconds(self, seconds):
        beep_thread = threading.Thread(target = self._light_for_seconds, args = (seconds, ))
        beep_thread.start()
        
    def test_motors(self):
        for x in range(-100, 100, 10):
            print(f"speed = {x}")
            self.set_speed(x)
            sleep(5)
    
    # Ändert die Led in den jeweils anderen Stand
    def toggle_led(self):
        GPIO.output(self.LED_PIN, not self.led_status)
        self.led_status = not self.led_status

            
if __name__ == "__main__":
    print("Remote Controller: Steuerung nach links und rechts, gebe Werte von -100 bis 100 ein")
    robot = Robot()
    robot.start_dist_sensors()
    sleep(1)
    robot.set_speed(100)
    for i in range(100):
        print("front:", robot.measure_dist_front())
        print("left:", robot.measure_dist_left())
        print("right:", robot.measure_dist_right())
        sleep(0.1)

    robot.stop_motors()
    sys.exit()
    #robot.test_motors()
    #steering_target = 0
    #steering_thread = threading.Thread(target = lambda robot: (robot.steer(steering_target)), daemon=True, args=(robot,))
    #steering_thread.start()
    #robot.turn_90_degrees("left")
    #robot.stop_motors()
    try:
        a = 0
        while True:
            try:
                a = int(input())
            except ValueError:
                print("Ungültige Nummer, gebe eine Nummer von -100 bis 100 ein")
            robot.steer(a)
            #robot.steering.run_to_position(int(input()), speed = 100)
    except KeyboardInterrupt:
        print("Interrupt")
        #steering_thread.join()
        robot.stop_motors()
        robot.stop_dist_sensors()