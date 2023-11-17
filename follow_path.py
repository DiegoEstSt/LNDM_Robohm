from robot import Robot
import numpy as np
from time import sleep
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import picamera2
import matplotlib.pyplot as plt
import sys

# Wandelt einen Farbwert in einen  State (1: Schwarz, 2: Grün, 0: andere Farbe) um 
def color_to_state(color):
    red, green, blue = color
    black_threshold = 75
    green_threshold = 50

    # Falls alle Farb-Channels sehr niedrig sind ist die Farbe wohl schwarz
    if red < black_threshold and green < black_threshold and blue < black_threshold:
        return 1
    # Falls der Grün-Channel deutlich am stärksten ist ist die Farbe wohl grün
    elif green > (red + blue) / 2 + green_threshold:
        return 2
    else:
        return 0

# Berechnet die durchschnittliche Farbe im Quadrat mit Seitenlänge region_size um die angegebene Position herum 
def average_color_around_position(pixel_array, x, y, region_size):
    # Brechnet die positionen der Kanten des Quadrats
    x_start = max(0, x - region_size // 2)
    x_end = min(pixel_array.shape[1], x + region_size // 2 + 1)
    y_start = max(0, y - region_size // 2)
    y_end = min(pixel_array.shape[0], y + region_size // 2 + 1)

    # Extrahiert den Bereich aus dem Bild
    region = pixel_array[y_start:y_end, x_start:x_end, :]

    # Berechnet die durchschnittliche Farbe
    average_color = np.mean(region, axis=(0, 1))

    return average_color


# Berechnet den State (1: Schwarz, 2: Grün, 0: andere Farbe) der durchschnittlichen Farbe des Pixels an der angegebenen Position und der Farbe aller Pixel py darüber und my darunter
def average_vertical_state_around_position(pixel_array, x, y, py, my):
    x = max(0, x)
    x = min(pixel_array.shape[1], x)
    y_start = max(0, y - my)
    y_end = min(pixel_array.shape[0], y + py)
    
    region = pixel_array[y_start:y_end, x]
    
    average_color = np.mean(region, axis=0)
        
    return color_to_state(average_color)
    

    
if __name__ == "__main__":
    robot = Robot()

    # Konfiguriert die Kamera des Robotes
    config = robot.camera.create_still_configuration(main={"size": (400, 200)}, display="main")
    robot.camera.configure(config)
    robot.camera.start()
    #sleep(100)

    GPIO.setmode(GPIO.BCM)

    GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    while GPIO.input(21) != GPIO.HIGH:
        sleep(1)
    print("Starting")
    robot.beep_for_seconds(3)
    
    while True:
        try:
            pixel_array = robot.camera.capture_array("main")
            states = []
            for x in range(0, pixel_array.shape[1] - 1):
                states.append(average_vertical_state_around_position(pixel_array, x, 180, 5, 5))
            
            # Diese drei Zeilen dekommentieren, um eine grafische Übersicht über das State array zu bekommen
            #fig, ax = plt.subplots()
            #ax.stairs(states, linewidth=2.5)
            #plt.show()
            
            # Diese zwei Zeilen dekommentieren, um das aufgenommene Bild zusehen
            #imgplt = plt.imshow(pixel_array)
            #plt.show()
            
            # ----- Startet die Pfad Folgen Logic -------
            
            # Dreht den Roboter
            if any(states[0:50]):
                robot.turn(-100)
                robot.beep_for_seconds(0.5)
            elif any(states[50:150]):
                robot.turn(-100)
            elif any(states[350:400]):
                robot.turn(100)
                robot.beep_for_seconds(0.5)
            elif any(states[250:350]):
                robot.turn(100)
            elif any(states[150:250]):
                robot.set_speed(100)
                
            # Wenn der Roboer nichts sieht, fährt er rückwärts
            if not any(states):
                robot.set_speed(-100)
            
            # Wenn der Knopf gedrückt wird, dann wird das Programm beendet
            if GPIO.input(21) == GPIO.HIGH:
                print("stop")
                robot.motor_left.stop()
                robot.motor_right.stop()
                robot.beep_for_seconds(1)
                sys.exit()
                

        except KeyboardInterrupt:
            robot.motor_left.stop()
            robot.motor_right.stop()
            print("interrupt")
            sys.exit()
                   