from buildhat import Motor
from picamera2 import Picamera2
import RPi.GPIO as GPIO
from time import sleep

class Robot:
    def __init__(self):
        self.motor_left = Motor("B")
        self.motor_right = Motor("A")
        self.camera = Picamera2()
        # Startet den Buzzer
        self.BUZZER_PIN = 6
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)

    #  Setzt die Geschwindigkeit vom linken Motor (Werte von -100 bis 100)
    #  Diese Funktion existiert, da die Geschwindigkeit aufgrund der räumlichen Positionierung des Motors
    #  negativ für eine Bewegung vorwärts sein muss
    def set_left_speed(self, speed):
        self.motor_left.start(speed * -1)
       
    #  Setzt die Geschwindigkeit vom linken Motor (Werte von -100 bis 100)
    def set_right_speed(self, speed):
        self.motor_right.start(speed)
    
    # Setzt die Geschwindigkeit beider Motoren
    def set_speed(self, x):
        self.set_left_speed(x)
        self.set_right_speed(x)
    
    # Dreht den Roboter je nach gegebenem Wert von -100 (links) und 100 (rechts) 
    def turn(self, x):
        speed_left = -50 if x < 0 else x
        speed_right = -50 if x > 0 else -x
        self.set_left_speed(speed_left)
        self.set_right_speed(speed_right)
        
    # Piepst für  x Sekunden
    # NOCH NICHT FERTIG; HÄLT DEN CODE FÜR DIE ZEIT DES PIEPSENS AN!!!!!!!!!!!!
    def beep_for_seconds(self, seconds):
        GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
        print("started beeping")
        sleep(seconds)
        GPIO.output(self.BUZZER_PIN, GPIO.LOW)
        