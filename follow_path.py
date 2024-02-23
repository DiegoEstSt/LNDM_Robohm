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
import pickle
from datetime import datetime
import os

# Speichert die Laenge des states array
state_size = 300

# Stelle im Bildarray an der das horizontale States Array entnommen wird, Abstand vom oberen Bildrand
y_check_distance = 50

# Stelle im Bildarray an der das horizontale G-States Array entnommen wird, Abstand vom oberen Bildrand
gy_check_distance = 200
    
# Distanz vom seitlichem Rand des Bildes, in dem die vertikalen States entnommen werden sollen
x_check_distance = 30
    
# Bereich, der im unten im Bild entfernt wird. Bezieht sich auf den Abstand der Pixel im Originalbild (also nicht geresized). M
# Momentan nötig, da unten schwarzes Lego und der Schatten des Roboters zu sehen ist und wir auch vertikal im Bild überprüfen,
# sollten wir dies nicht mehr tun, kann darauf verzichtet werden den unteren Bereich zu entfernen
bottom_removal_distance = 90

save_dir = "saves/" + datetime.fromtimestamp(time.time()).strftime("%d.%m.%Y,%H:%M:%S") 

obstacle_corners = 0

frames = 0

running = False


# Die Robot Variable wurde hierher verschoben, damit die stop und is_running Funktionen funktionieren
# Das Ganze ist nicht so clean, aber es musste noch schnell vorm Wettbewerb gemacht werden
robot = 0


# Wandelt einen Farbwert in einen  State (1: Schwarz, 2: Grün, 3: Rot, 0: andere Farbe) um 
def color_to_state(color):
    red, green, blue = color
    black_threshold = 85
    green_threshold = 40
    red_threshold = 80

    # Falls der Grün-Channel deutlich am stärksten ist ist die Farbe wohl grün
    if green > (red + blue) / 2 + green_threshold:
        return 2
    # Falls alle Farb-Channels sehr niedrig sind ist die Farbe wohl schwarz
    elif red < black_threshold and green < black_threshold and blue < black_threshold:
        return 1
    if red > (green + blue) / 2 + red_threshold:
        return 3
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
    y = min(pixel_array.shape[0], y)
    x_start = max(0, x - mx)
    x_end = min(pixel_array.shape[1], x + px)

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
            else:    
                points_positions.append(round((i + j) / 2)) 
        if found:
            if line[i] == 1:
                found = False

    return points_positions

# Überprüft ob oberhalb des gegeben Punktes die schwarze Linie ist
def check_green_point_validity(pixel_array, x, y):
    check_region = 120
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
            print("links:", lx)
            return "right"
        elif state == 2:
            break
    
    for rx in range(min(pixel_array.shape[1] - 1, x + check_region), x, -3):
        print(rx)
        state = color_to_state(pixel_array[y][rx])
        if state == 1:
            return "left"
        elif state == 2:
            break
    
    return False

def stop():
    global running
    global robot
    if robot == 0:
        print("Kann nicht stoppen, Roboter ist nicht initialisiert")
        return
    robot.light_for_seconds(1)
    running = False
    print(save_dir)
    print(frames)
    robot.stop_motors()

def is_running():
    global running
    return running

def check_for_line():
    global obstacle_corners
    pixel_array = cv2.resize(robot.camera.capture_array("main"), dsize = (state_size, state_size))
    pixel_array = pixel_array[0:state_size - 1 - bottom_removal_distance]
    v_states = []
    v_states_thread = Thread(target = averaged_vertical_states, args = (pixel_array, 50, v_states))
    v_states_thread.start()
    v_states_thread.join()

    v_line_position = get_line_position(v_states)
    robot.toggle_led()
    fig, ax = plt.subplots(1)
    ax.imshow(pixel_array)
    if v_line_position:
        ax.add_patch(Circle((50, v_line_position), radius=1, color="red"))
    plt.savefig(save_dir + '/%d.png' % obstacle_corners)
    obstacle_corners += 1
    plt.close()

    ax.imshow(pixel_array)

    return v_line_position

def bypass_obstacle():
    robot.set_speed(-100)
    sleep(1)
    robot.stop_motors()
    sleep(0.75)
    robot.turn_90_degrees_hard("right")
    # Die Motoren sind träge und funktionieren nicht perfekt, diese Zeile verhindert, dass der Roboter beim Losfahren 
    # Mit dem linken Motor schneller los fährt als mit dem Rechten
    robot.speed = 100
    robot.steer(-100)
    sleep(1)
    robot.set_speed(100)
    sleep(1.4)
    
    robot.stop_motors()
    sleep(0.5)
    robot.turn_90_degrees_hard("left")
    robot.set_speed(100)
    start_time = time.time()
    while time.time() - start_time < 3.5:
        dist = check_for_line()
        print("dist = " + str(dist))
        if dist is not None and dist > 30:
            robot.turn_90_degrees_hard("right")
            robot.set_speed(-100)
            sleep(1.3)
            robot.stop_motors()
            robot.set_speed(100)
            print("ending obstacle routine after part 1")
            return
        
    robot.turn_90_degrees_hard("left")
    robot.set_speed(100)
    start_time = time.time()
    while time.time() - start_time < 3.2:
        dist = check_for_line()
        print("dist = " + str(dist))
        if dist is not None and dist > 30:
            robot.turn_90_degrees_hard("right")
            robot.set_speed(-100)
            sleep(1.2)
            robot.stop_motors()
            robot.set_speed(100)
            print("ending obstacle routine after part 2")
            return
    robot.stop_motors()
    
    robot.turn_90_degrees_hard("left")
    robot.set_speed(100)
    start_time = time.time()
    while time.time() - start_time < 4:
        dist = check_for_line()
        print("dist = " + str(dist))
        if dist is not None and dist > 30:
            robot.turn_90_degrees_hard("right")
            robot.set_speed(-100)
            sleep(1.3)
            robot.stop_motors()
            robot.set_speed(100)
            print("ending obstacle routine after part 3")
            return


# Die Funktion, die die Logik zum Folgen der Linie beinhaltet, aufrufen um den Robotor die Linie folgen zu lassen
def follow_path():
    global frames
    global robot
    global running
    robot = Robot()

    # Konfiguriert die Kamera des Robotes
    config = robot.camera.create_still_configuration(main={"size": (700, 700)}, display="main")
    robot.camera.configure(config)
    robot.camera.start()

    GPIO.setmode(GPIO.BCM)

    GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    robot._light_for_seconds(3)
    
    start_time = time.time()
    
    

    # Die folgenden Werte werden genutzt, um zu entscheiden, wie der Roboter fahren soll, wenn er die Linie bei 90° Kurven verliert
    # Speichert die letze Position der Linie im vl Array, wert ist None wenn keine Linie gesehen wird
    last_vl_position = 0
    # Speichert die letzte Position der Linie im vr Array
    last_vr_position = 0
    
    """Variablen der Pfad-Folge-Logik"""
    # Für genauere Erklärung der Faktoren Benutzung während des Pfad-Folgens ansehen, ca. ab Zeile 220
    correction_factor = 200
    activation_threshold = 20
    marker_turn_time = 0.3
    speed = 60

    while True:
        sleep(1)

        robot.stop_motors()
        while GPIO.input(22) != GPIO.HIGH:
            sleep(1)

        if not (os.path.exists(save_dir)):
            os.makedirs(save_dir)
            
        robot._light_for_seconds(3)
        running = True
            
        robot.set_speed(speed)
        robot.start_dist_sensors()
        while running:
            try:
                pixel_array = cv2.resize(robot.camera.capture_array("main"), dsize = (state_size, state_size))
                pixel_array = pixel_array[0:state_size - 1 - bottom_removal_distance]
                
                # Ein Array, das ein horizontalen Ausschnitt aus dem Bild beinhaltet, der genutzt wird um den Roboter auf Kurs zu halten
                h_states = []

                # Ein Array, das ein horizontalen Ausschnitt aus dem Bild beinhaltet, der genutzt wird um die grünen Punkte zu erkenen
                # Wir verwenden nicht h_states, da es für das Linie-Folgen besser ist weiter oben im Bild zu schauen
                # und für das erkennen der grünen Punkte es besser ist, eher mittiger zu überprüfen
                gh_states = []
                
                # Zwei Arrays, die vertikale Ausschnitte aus dem Bild beinhalten, vl links, vr rechts
                vl_states = []
                vr_states = []
                
                h_states_thread = Thread(target = averaged_horizontal_states, args = (pixel_array, y_check_distance, h_states))
                gh_states_thread = Thread(target = averaged_horizontal_states, args = (pixel_array, gy_check_distance, gh_states))
                vl_states_thread = Thread(target = averaged_vertical_states, args = (pixel_array, x_check_distance, vl_states))
                vr_states_thread = Thread(target = averaged_vertical_states, args = (pixel_array, state_size - 1 - x_check_distance, vr_states))
                
                h_states_thread.start()
                gh_states_thread.start()
                vl_states_thread.start()
                vr_states_thread.start()

                
                h_states_thread.join()
                gh_states_thread.join()
                vl_states_thread.join()
                vr_states_thread.join()
                            
                
                h_line_position = get_line_position(h_states)

                vl_line_position = get_line_position(vl_states)
                vr_line_position = get_line_position(vr_states)

                # Speichert die x-Koordinate aller grüner Punkte in einem Array bzw. Liste
                green_points = get_green_points_positions(gh_states)
                # Speichert, ob die grnen Punkte gültig sind, kann einfach per zip(green_points, green_points_validity) zusammen genutzt werden
                green_points_validity = [check_green_point_validity(pixel_array, point, gy_check_distance) for point in green_points]
                
                relative_green_points_positions = [get_relative_green_point_position(pixel_array, point, gy_check_distance) for point in green_points]
               
                last_dist_front = robot.dist_front
                robot.measure_dist_front()

                # Diese drei Zeilen dekommentieren, um eine grafische Übersicht über das State array zu bekommen
                #fig, ax = plt.subplots()
                #ax.stairs(h_states, linewidth=2.5)
                #plt.show()

                # Diese Zeilen dekommentieren, um das aufgenommene Bild zusehen                
                #fig, ax = plt.subplots(1)
                #ax.imshow(pixel_array)
            
                #if h_line_position:
                #    ax.add_patch(Circle((h_line_position, y_check_distance), radius=1, color="green"))
                #if vl_line_position:
                #    ax.add_patch(Circle((x_check_distance, vl_line_position), radius=1, color="red"))
                #if vr_line_position:
                #    ax.add_patch(Circle((state_size - 1 - x_check_distance, vr_line_position), radius=1, color="red"))
                
                #for point in green_points:
                #    ax.add_patch(Circle((point, y_check_distance), radius=1, color="yellow"))
                #    if check_green_point_validity(pixel_array, point, y_check_distance):
                #       ax.add_patch(Circle((point, y_check_distance), radius=3, color="purple"))
                #        if get_relative_green_point_position(pixel_array, point, y_check_distance) == "left":
                #            ax.add_patch(Circle((point, y_check_distance), radius=3, color="orange"))
                #        if get_relative_green_point_position(pixel_array, point, y_check_distance) == "right":
                #            ax.add_patch(Circle((point, y_check_distance), radius=3, color="blue"))
                

                # Das Bild zu generien und zu speichern dauert zu lange. Nach meinen Tests erreicht das Programm mit
                # dieser Zeile 1 Durchlauf pro Sekunde und ohne der Zeile 5 - 8 
                
                #plt.savefig(save_dir + '/%d.png' % frames)
                #plt.close()
                #continue


                # ----- Startet die Pfad Folgen Logic -------
                #print("Vertikale Linienposition: ", h_line_position)
                #print("Horizontale linke Linienposition", vl_line_position)
                #print("Horizontale rechte Linienposition", vl_line_position)
                #print("")

                print("last vl position", last_vl_position)
                print("last vr position", last_vr_position)

                for i in range(0, state_size - 1, 3):
                    if h_states[i] == 3:
                        print("Stoppen weil Rot")
                        robot.stop_motors()
                        sleep(10)
                        robot.set_speed(speed)
                        sleep(1)
                        break

                if last_dist_front and robot.dist_front:
                    if last_dist_front < 7 and robot.dist_front < 7:
                        print("Hindernis erkannt")
                        bypass_obstacle()
                        print("Hindernis bewältigt")
   

                steering = 0
                if h_line_position:
                    # Falls links und rechts schwarz gesehen wird, muss geradeaus gefahren werden
                    if vl_line_position and vr_line_position:
                        robot.steer(0)
                    else:
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
                else:
                    if last_vl_position:
                        robot.steer(-100)
                    elif last_vr_position:
                        robot.steer(100)
                    else:
                        robot.set_speed(100)

                if green_points:
                    print("Green Points", green_points)
                    print("Validity", green_points_validity)
                    print("Relative Position", relative_green_points_positions)
                    if any(green_points_validity):
                        robot.stop_motors()
                    if len(green_points) >= 2 and all(green_points_validity):
                        robot.turn_90_degrees("left")
                        robot.turn_90_degrees("left")
                    else:
                        for (green_point, validity, relative_position) in zip(green_points, green_points_validity, relative_green_points_positions):
                            if relative_position and validity: 
                                print("drehen nach", relative_position)
                                robot.set_speed(100)
                                sleep(0.5)
                                if relative_position == "left":
                                    last_vl_position = 200
                                    last_vr_position = None
                                elif relative_position == "right":
                                    last_vl_position = None
                                    last_vr_position = 200
                                robot.turn_90_degrees(relative_position)
                                robot.speed = 100

                with open(f"{save_dir}/{frames}.txt", "wb") as f:
                    pickle.dump([pixel_array, h_line_position, vl_line_position, vr_line_position, green_points, green_points_validity, relative_green_points_positions, steering], f)

                # Updated die letzte Position der vertikalen Linien falls er die horizontale Linie noch sieht
                # Dies steht nicht in der oberen if-Abfrage, da es bei zukünftigen Änderungen zu Problemen führen könnte, falls die Werte zu früh geupdated werden
                if h_line_position:
                    last_vl_position = vl_line_position
                    last_vr_position = vr_line_position

                

                # Wenn der Knopf gedrückt wird, dann wird das Programm beendet
                if GPIO.input(22) == GPIO.HIGH:
                    stop()
                    running = False
                

                frames += 1
                if (frames % 10 == 0):
                    print(f"fps: {frames / (time.time() - start_time)}")
                robot.toggle_led()


            except KeyboardInterrupt:
                stop()
                sys.exit()
    robot.stop_motors()


if __name__ == "__main__":
    # Wenn das Programm vom User gestartet wird, wird es vermutlich crashen, da es bereits automatisch gestartet wurde
    # Das automatisch gestartete Programm kann beendet werden, indem als erstes die PID ermittelt wird
    # Hierzu einfach "systemctl status follow_path.service" oder "ps aux | grep -i follow_path" eingeben
    # Die PID merken und dann "kill -9 PID" eingeben und PID durch die entsprechende PID ersetzen
    follow_path()
    
