from robot import Robot
import numpy as np
from time import sleep
import time
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import picamera2
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import sys
import cv2

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
def average_horizontal_state_around_position(pixel_array, x, y, py, my):
    x = max(0, x)
    x = min(pixel_array.shape[1], x)
    y_start = max(0, y - my)
    y_end = min(pixel_array.shape[0], y + py)

    region = pixel_array[y_start:y_end, x]

    average_color = np.mean(region, axis=0)

    return color_to_state(average_color)


# Berechnet den State (1: Schwarz, 2: Grün, 0: andere Farbe) der durchschnittlichen Farbe des Pixels an der angegebenen Position und der Farbe aller Pixel px links und mx rechts
def average_vertical_state_around_position(pixel_array, x, y, px, mx):
    y = max(0, y)
    y = min(pixel_array.shape[1], y)
    x_start = max(0, x - mx)
    x_end = min(pixel_array.shape[0], x + px)

    region = pixel_array[y, x_start:x_end]

    average_color = np.mean(region, axis=0)

    return color_to_state(average_color)



# Gibt die Position der Mitte der ersten linken schwarzen Linie in einem Array wieder. die Funktion funktioniert nicht mit einer 100% Genauigkeit, da sie ueber die Pixel in einem bestimmten Abstand iteriert um Zeit zu sparen. Wenn nichts gefunden wird, gibt die Funktion None zurueck
def get_line_position(line):
    # Iteriert als erstes in 10 Schritten ueber das Arrat, die Linie spannt sich ja ueber mindestens 10 pixel und es geht so schneller
    for i in range(0, len(line), 10):
        if line[i] == 1:
            for j in range(i, len(line)):
                if line[j] != 1:
                    return round((i + j) / 2)
            return round((i + len(line) - 1) / 2)

    # Falls beim ersten Durchlauf nichts rauskam, ueberpruefen wir das Array nochmals mit einer hoeheren Genauigkeit
    for i in range(3, len(line), 5):
        if line[i] == 1:
            for j in range(i, len(line)):
                if line[j] != 1:
                    return round((i + j) / 2)
            return round((i + len(line) - 1) / 2)

    print("Keine Linie gesehen")

    return None

def stop():
    print("stop")
    robot.stop_motors()
    robot.light_for_seconds(1)
    sys.exit()



if __name__ == "__main__":

    robot = Robot()

    # Konfiguriert die Kamera des Robotes
    config = robot.camera.create_still_configuration(main={"size": (700, 700)}, display="main")
    robot.camera.configure(config)
    robot.camera.start()

    GPIO.setmode(GPIO.BCM)

    GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    robot.light_for_seconds(3)

    while GPIO.input(20) != GPIO.HIGH:
        sleep(1)
    
    print("Starting")
    robot.light_for_seconds(3)
    sleep(3)
    #robot.turn(100)
    #sleep(100)
    
    
    frames = 0
    start_time = time.time()
    
    # Speichert die Laenge des states array
    state_size = 300

    # Speichert die letze Position der Linie. kann entweder "left" oder "right" sein
    last_line_position = ""
    
    # Stelle im Bildarray an der das horizontale States Array entnommen wird, Abstand vom oberen Bildrand
    y_check_distance = 200
    
    # Distanz vom seitlichem Rand des Bildes, in dem die vertikalen States entnommen werden sollen
    x_check_distance = 30
    
    # Bereich, der im unten im Bild entfernt wird. Bezieht sich auf den Abstand der Pixel im Originalbild (also nicht geresized). M
    # Momentan nötig, da unten schwarzes Lego und der Schatten des Roboters zu sehen ist und wir auch vertikal im Bild überprüfen,
    # sollten wir dies nicht mehr tun, kann darauf verzichtet werden den unteren Bereich zu entfernen
    bottom_removal_distance = 30
    


    while True:
        try:
            pixel_array = cv2.resize(robot.camera.capture_array("main"), dsize= (state_size, state_size))
            pixel_array = pixel_array[0:state_size - 1 - bottom_removal_distance]
            # Ein Array, das ein horizontalen Ausschnitt aus dem Bild beinhaltet, der genutzt wird um den Roboter auf Kurs zu halten
            states = []
            for x in range(0, pixel_array.shape[1] - 1):
                states.append(average_horizontal_state_around_position(pixel_array, x, y_check_distance, 5, 5))
                
            vl_states = []
            vr_states = []
            for y in range(0, pixel_array.shape[0] - 1):
                vl_states.append(average_vertical_state_around_position(pixel_array, x_check_distance, y, 5, 5))
                vr_states.append(average_vertical_state_around_position(pixel_array, state_size - x_check_distance - 1, y, 5, 5))
                
            line_position = get_line_position(states)
            
            vl_line_position = get_line_position(vl_states)
            vr_line_position = get_line_position(vr_states)
            
            # Diese drei Zeilen dekommentieren, um eine grafische Übersicht über das State array zu bekommen
            #fig, ax = plt.subplots()
            #ax.stairs(states, linewidth=2.5)
            #plt.show()

            # Diese Zeilen dekommentieren, um das aufgenommene Bild zusehen
            fig, ax = plt.subplots(1)
            ax.imshow(pixel_array)
        
            if line_position:
                ax.add_patch(Circle((line_position, y_check_distance), radius=1, color="green"))
            if vl_line_position:
                ax.add_patch(Circle((x_check_distance, vl_line_position), radius=1, color="red"))
            if vr_line_position:
                ax.add_patch(Circle((state_size - 1 - x_check_distance, vr_line_position), radius=1, color="red"))
            
            plt.show()
            continue

            # ----- Startet die Pfad Folgen Logic -------

            # Dreht den Roboter
            robot.set_speed(65)
            """
            if any(states[0:30]):
                robot.steer(-25)
                #robot.light_for_seconds(0.5)
                last_line_position = "left"
            elif any(states[30:120]):
                print("left")
                robot.steer(-25)
                last_line_position = "left"
            elif any(states[270:300]):
                robot.steer(25)
                robot.light_for_seconds(0.5)
                last_line_position = "right"
            elif any(states[140:270]):
                print("right")
                robot.steer(25)
                last_line_position = "right"
            elif any(states[150:250]):
                robot.set_speed(50)
                print("gerade")
            else:
                robot.set_speed(-30 if last_line_position == "left" else (30 if last_line_position == "right" else 0))"""
            
            line_position = get_line_position(states)
            print("Line position: ", line_position)
            
            if line_position != None:
                if False:
                    if line_position < ((state_size / 2) - 30):
                        robot.steer(-100)
                    elif line_position > ((state_size / 2) + 30):
                        robot.steer(100)
                    else:
                        robot.steer(0)
                else:
                    if abs(line_position - (state_size / 2)) > 100:
                        steering = int(max(-100, min( 100, (0.5 - (line_position / state_size)) * (-0.2))))
                        print("Lenken mit dem Wert: " + str(steering))
                        robot.steer(steering)
                    else:
                        robot.steer(0)

            if 2 in states[0:130]:
                print("left")
               # robot.turn(-100)
                #sleep(5)

            if 2 in states[170:300]:
                print("right")
               # robot.turn(100)
                #sleep(5)


            # Wenn der Knopf gedrückt wird, dann wird das Programm beendet
            if GPIO.input(20) == GPIO.HIGH:
                stop()
            
            frames += 1
            #print(frames / (time.time() - start_time))
    

        except KeyboardInterrupt:
            stop()
