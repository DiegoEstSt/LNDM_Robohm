from robot import Robot
from threading import Thread
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
    green_threshold = 30

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

# Erzeugt ein Array, welches einen horizontalen Ausschnitt aus dem gegebenen Pixelarray beinhaltet, y _check_distance gibt den Abstand des Arrays vom oberern Rand des Pixelarrays an
def averaged_horizontal_states(pixel_array, y_check_distance, states):
    for x in range(0, pixel_array.shape[1] - 1):
        states.append(average_horizontal_state_around_position(pixel_array, x, y_check_distance, 5, 5))

# Erzeugt ein Array, welches einen vertikalen Ausschnitt aus dem gegebenen Pixelarray beinhaltet, x_check_distance gibt den Abstand des Arrays vom linken Rand des Pixelarrays an
def averaged_vertical_states(pixel_array, x_check_distance, states):
    for y in range(0, pixel_array.shape[0] - 1):
        states.append(average_vertical_state_around_position(pixel_array, x_check_distance, y, 5, 5))

# Gibt die Position der Mitte der ersten linken schwarzen Linie in einem Array wieder. die Funktion funktioniert nicht mit einer 100% Genauigkeit, da sie ueber die Pixel in einem bestimmten Abstand iteriert um Zeit zu sparen. Wenn nichts gefunden wird, gibt die Funktion None zurueck
def get_line_position(line, debug=False):
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
    
    if debug:
        print("Keine Linie gesehen")

# Gibt ein Array allen gefundenen grünen Punkten zurück
def get_green_points_positions(line, debug=False):
    points_positions = []
    found = False
    for i in range(0, len(line), 10):
        if line[i] == 2 and not found:
            found = True
            for j in range(i, len(line)):
                if line[j] != 2:
                    points_positions.append(round((i + j) / 2))
                    print("Found end")
                    break
        
        if found:
            if line[i] == 1:
                found = False

    return points_positions

# Überprüft ob oberhalb des gegeben Punktes die schwarze Linie ist
def check_green_point_validity(pixel_array, x, y):
    check_region = 50
    upper_line_detected = False
    for y in range(max(0, y - check_region), y, 3):
        state = color_to_state(pixel_array[y][x])
        if state == 1:
            upper_line_detected = True
        
        elif state == 2 and upper_line_detected:
            return True
    
    return False

# Gibt die Position des Punktes relativ zu der schwarzen Linie zurück Entweder "left" (Der Punkt liegt links neben der schwarzen Linie), "right" oder False 
def get_relative_green_point_position(pixel_array, x, y):
    check_region = 70
    for lx in range(max(0, x - check_region), x, 3):
        state = color_to_state(pixel_array[y][lx])
        if state == 1:
            return "right"
        elif state == 2:
            break
    
    for rx in range(min(pixel_array.shape[1], x + check_region), x, -3):
        print(rx)
        state = color_to_state(pixel_array[y][rx])
        if state == 1:
            return "left"
        elif state == 2:
            break
    
    return False

def stop(robot):
    robot.stop_motors()
    robot._light_for_seconds(1)

# Die Funktion, die die Logik zum Folgen der Linie beinhaltet, aufrufen um den Robotor die Linie folgen zu lassen
# Es muss noch der Knopf betätigt werden, damit der Roboter startet, mit dem Knopf lässt sich der Roboter wieder anhalten und auch wieder starten
def follow_path():
    robot = Robot()

    # Konfiguriert die Kamera des Robotes
    config = robot.camera.create_still_configuration(main={"size": (700, 700)}, display="main")
    robot.camera.configure(config)
    robot.camera.start()

    GPIO.setmode(GPIO.BCM)

    GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    robot._light_for_seconds(3)
    
    
    frames = 0
    start_time = time.time()
    
    # Speichert die Laenge des states array
    state_size = 300

    # Speichert die letze Position der Linie. kann entweder "left" oder "right" sein
    last_line_position = ""
    
    # Stelle im Bildarray an der das horizontale States Array entnommen wird, Abstand vom oberen Bildrand
    y_check_distance = 50
    
    # Distanz vom seitlichem Rand des Bildes, in dem die vertikalen States entnommen werden sollen
    x_check_distance = 30
    
    # Bereich, der im unten im Bild entfernt wird. Bezieht sich auf den Abstand der Pixel im Originalbild (also nicht geresized). M
    # Momentan nötig, da unten schwarzes Lego und der Schatten des Roboters zu sehen ist und wir auch vertikal im Bild überprüfen,
    # sollten wir dies nicht mehr tun, kann darauf verzichtet werden den unteren Bereich zu entfernen
    bottom_removal_distance = 30
    
    """Variablen der Pfad-Folge-Logik"""
    # Für genauere Erklärung der Faktoren Benutzung während des Pfad-Folgens ansehen, ca. ab Zeile 220
    correction_factor = 200
    activation_threshold = 40
    marker_turn_time = 0.3

    while True:
        while GPIO.input(23) != GPIO.HIGH:
            sleep(1)
            
        robot._light_for_seconds(3)
        running = True
            
        robot.set_speed(70)
        while running:
            try:
                pixel_array = cv2.resize(robot.camera.capture_array("main"), dsize = (state_size, state_size))
                pixel_array = pixel_array[0:state_size - 1 - bottom_removal_distance]
                
                # Ein Array, das ein horizontalen Ausschnitt aus dem Bild beinhaltet, der genutzt wird um den Roboter auf Kurs zu halten
                h_states = []
                
                # Zwei Arrays, die vertikale Ausschnitte aus dem Bild beinhalten, vl links, vr rechts
                vl_states = []
                vr_states = []
                
                h_states_thread = Thread(target = averaged_horizontal_states, args = (pixel_array, y_check_distance, h_states))
                vl_states_thread = Thread(target = averaged_vertical_states, args = (pixel_array, x_check_distance, vl_states))
                vr_states_thread = Thread(target = averaged_vertical_states, args = (pixel_array, state_size - 1 - x_check_distance, vr_states))
                
                h_states_thread.start()
                vl_states_thread.start()
                vr_states_thread.start()

                
                h_states_thread.join()
                vl_states_thread.join()
                vr_states_thread.join()
                            
                
                h_line_position = get_line_position(h_states)

                vl_line_position = get_line_position(vl_states)
                vr_line_position = get_line_position(vr_states)

                # Speichert die x-Koordinate aller grüner Punkte in einem Array bzw. Liste
                green_points = get_green_points_positions(h_states)
                # Speichert, ob die grnen Punkte gültig sind, kann einfach per zip(green_points, green_points_validity) zusammen genutzt werden
                green_points_validity = [check_green_point_validity(pixel_array, point, y_check_distance) for point in green_points]
                
                relative_green_points_positions = [get_relative_green_point_position(pixel_array, point, y_check_distance) for point in green_points]
                
                """# Diese drei Zeilen dekommentieren, um eine grafische Übersicht über das State array zu bekommen
                fig, ax = plt.subplots()
                ax.stairs(h_states, linewidth=2.5)
                plt.show()

                # Diese Zeilen dekommentieren, um das aufgenommene Bild zusehen
                fig, ax = plt.subplots(1)
                ax.imshow(pixel_array)
            
                if h_line_position:
                    ax.add_patch(Circle((h_line_position, y_check_distance), radius=1, color="green"))
                if vl_line_position:
                    ax.add_patch(Circle((x_check_distance, vl_line_position), radius=1, color="red"))
                if vr_line_position:
                    ax.add_patch(Circle((state_size - 1 - x_check_distance, vr_line_position), radius=1, color="red"))
                
                for point in green_points:
                    ax.add_patch(Circle((point, y_check_distance), radius=1, color="yellow"))
                    if check_green_point_validity(pixel_array, point, y_check_distance):
                        ax.add_patch(Circle((point, y_check_distance), radius=3, color="purple"))
                        if get_relative_green_point_position(pixel_array, point, y_check_distance) == "left":
                            ax.add_patch(Circle((point, y_check_distance), radius=3, color="orange"))
                        if get_relative_green_point_position(pixel_array, point, y_check_distance) == "right":
                            ax.add_patch(Circle((point, y_check_distance), radius=3, color="blue"))


                        

                plt.show()
                continue"""


                # ----- Startet die Pfad Folgen Logic -------
                #print("Vertikale Linienposition: ", h_line_position)
                #print("Horizontale linke Linienposition", vl_line_position)
                #print("Horizontale rechte Linienposition", vl_line_position)
                #print("")
   

                if h_line_position:
                    # Falls die Linie weiter als der activation_threshold von der Mitte entfernt ist
                    if abs(h_line_position - (state_size / 2)) > activation_threshold:
                        percentage = (1 - ((h_line_position / state_size) * 2))
                        steering = (max(-100, min(100, percentage * -correction_factor)))
                        #print("Percentage:" + str(percentage))
                        #print("Lenken mit dem Wert: " + str(steering))
                        robot.steer(int(steering))
                        if vl_line_position or vr_line_position:
                            robot.turn(int(steering))
                    else:
                        robot.steer(0)
                    
                    if green_points:
                        print("Green Points", green_points)
                        print("Validity", green_points_validity)
                        print("Relative Position", relative_green_points_positions)
                        if len(green_points) >= 2 and all(green_points_validity):
                            pass
                        for (green_point, validity, relative_position) in zip(green_points, green_points_validity, relative_green_points_positions):
                            if relative_position and validity and relative_position != 0: 
                                print("drehen nach", relative_position)
                                robot.turn(-100 if relative_position == "left" else 100)
                                sleep(1)

                # Wenn der Knopf gedrückt wird, dann wird das Programm beendet
                if GPIO.input(23) == GPIO.HIGH:
                    stop(robot)
                    running = False
                

                frames += 1
                if (frames % 10 == 0):
                    print(f"fps: {frames / (time.time() - start_time)}")
                robot.toggle_led()

            except KeyboardInterrupt:
                stop(robot)
                sys.exit()


if __name__ == "__main__":
    # Wenn das Programm vom User gestartet wird, wird es vermutlich crashen, da es bereits automatisch gestartet wurde
    # Das automatisch gestartete Programm kann beendet werden, indem als erstes die PID ermittelt wird
    # Hierzu einfach "systemctl status follow_path.service" eingeben
    # Die PID merken und dann "kill -9 PID" eingeben und PID durch die entsprechende PID ersetzen
    follow_path()
    