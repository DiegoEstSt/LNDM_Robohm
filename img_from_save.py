import pickle
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import os
import sys
import numpy as np

y_check_distance = 50
gy_check_distance = 200
x_check_distance = 30
state_size = 300


# Wandelt einen Farbwert in einen  State (1: Schwarz, 2: Grün, 0: andere Farbe) um 
def color_to_state(color):
    red, green, blue = color
    black_threshold = 85
    green_threshold = 50

    # Falls der Grün-Channel deutlich am stärksten ist ist die Farbe wohl grün
    if green > (red + blue) / 2 + green_threshold:
        return 2
    # Falls alle Farb-Channels sehr niedrig sind ist die Farbe wohl schwarz
    if red < black_threshold and green < black_threshold and blue < black_threshold:
        return 1
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
            return "right"
        elif state == 2:
            break
    
    for rx in range(min(pixel_array.shape[1] - 1, x + check_region), x, -3):
        state = color_to_state(pixel_array[y][rx])
        if state == 1:
            return "left"
        elif state == 2:
            break
    
    return False




def generate_save():
    if len(sys.argv) != 4 and len(sys.argv) != 2:
        print("Gebe bitte drei Argumente beim Start dieses Programmes ein.")
        print("Das Programm generiert nur Diagramme für die Frames in einem bestimmten Bereich")
        print("Das erste Argument soll der relative Pfad zum Ordner sein, in dem die Dateien gespeichert sind")
        print("Das zweite Argument sollte das untere Ende des Bereiches der umzuwandelnden Frames sein")
        print("Das dritte Argument sollte das oberen Ende des Bereiches der umzuwandlenden Frames sein")
        print("Beispiel: python3 img_from_save.py saves/beispiel 50 100")
        print("Dies würde Diagramme zu den Frames vom 50. bis zum 100., die in saves/beispiel liegen, generieren")
        print("")
        sys.exit()


    if not os.path.exists("imgs/" + sys.argv[1]):
        if len(sys.argv) != 2:
            os.makedirs("imgs/" + sys.argv[1])

    if len(sys.argv) != 2:
        files = os.listdir(sys.argv[1])
    else:
        files = os.listdir("saves")
        print(files)
    count = 0
    if len(sys.argv) == 4:
        for file in files:
            if file[-4:] == ".txt" and int(file[:-4]) in range(int(sys.argv[2]), int(sys.argv[3])):
                count += 1
                with open(f"{sys.argv[1]}/{file}", "rb") as f:
                    print(f"{count} / {int(sys.argv[3]) - int(sys.argv[2])}")
                    (pixel_array, h_line_position, vl_line_position, vr_line_position, green_points, green_points_validity, relative_green_points_positions, steering) = pickle.load(f)
                    fig, ax = plt.subplots(1)
                    ax.imshow(pixel_array)

                    # Noch nicht implementiert, falls man neue Algorithmen testen will
                    if True:
                        h_states = []
                        gh_states = []
                        vl_states = []
                        vr_states = []
                        averaged_horizontal_states(pixel_array, y_check_distance, h_states)
                        averaged_horizontal_states(pixel_array, gy_check_distance, gh_states)
                        averaged_vertical_states(pixel_array, x_check_distance, vl_states)
                        averaged_vertical_states(pixel_array, state_size - 1 - x_check_distance, vr_states)
                        points = get_green_points_positions(gh_states)
                        line_position = get_line_position(h_states)
                        vl_line_position = get_line_position(vl_states)
                        vr_line_position = get_line_position(vr_states)
                        if line_position:
                            ax.add_patch(Circle((line_position, y_check_distance), radius=1, color="green"))
                        if vl_line_position:
                            ax.add_patch(Circle((x_check_distance, vl_line_position), radius=1, color="red"))
                        if vr_line_position:
                            ax.add_patch(Circle((state_size - 1 - x_check_distance, vr_line_position), radius=1, color="red"))

                        for point in points:
                            print(point)
                            ax.add_patch(Circle((point, gy_check_distance), radius=1, color="yellow"))
                            if check_green_point_validity(pixel_array, point, gy_check_distance):
                                ax.add_patch(Circle((point, gy_check_distance), radius=6, color="purple"))
                            if get_relative_green_point_position(pixel_array, point, gy_check_distance) == "left":
                                ax.add_patch(Circle((point, gy_check_distance), radius=3, color="orange"))
                            if get_relative_green_point_position(pixel_array, point, gy_check_distance) == "right":
                                ax.add_patch(Circle((point, gy_check_distance), radius=3, color="blue"))
                    else:
                        if h_line_position:
                            ax.add_patch(Circle((h_line_position, y_check_distance), radius=1, color="green"))
                        if vl_line_position:
                            ax.add_patch(Circle((x_check_distance, vl_line_position), radius=1, color="red"))
                        if vr_line_position:
                            ax.add_patch(Circle((state_size - 1 - x_check_distance, vr_line_position), radius=1, color="red"))
                        print(green_points)
                        for (point, validity, relative_position) in zip(green_points, green_points_validity, relative_green_points_positions):
                            ax.add_patch(Circle((point, gy_check_distance), radius=1, color="yellow"))
                            if validity:
                                ax.add_patch(Circle((point, gy_check_distance), radius=5, color="purple"))
                            if relative_position == "left":
                                ax.add_patch(Circle((point, gy_check_distance), radius=3, color="orange"))
                            if relative_position == "right":
                                ax.add_patch(Circle((point, gy_check_distance), radius=3, color="blue"))
                    
                    plt.savefig(f"imgs/{sys.argv[1]}/{file}.png")
                    plt.close()
    







    elif len(sys.argv) == 2:
        for file in files:
            if file[-4:] == ".txt" and int(file[:-4]) in range(int(sys.argv[2]), int(sys.argv[3])):
                count += 1
                with open(f"{sys.argv[1]}/{file}", "rb") as f:
                    print(f"{count} / {int(sys.argv[3]) - int(sys.argv[2])}")
                    (pixel_array, h_line_position, vl_line_position, vr_line_position, green_points, green_points_validity, relative_green_points_positions, steering) = pickle.load(f)
                    fig, ax = plt.subplots(1)
                    ax.imshow(pixel_array)
                        
                    if h_line_position:
                        ax.add_patch(Circle((h_line_position, y_check_distance), radius=1, color="green"))
                    if vl_line_position:
                        ax.add_patch(Circle((x_check_distance, vl_line_position), radius=1, color="red"))
                    if vr_line_position:
                        ax.add_patch(Circle((state_size - 1 - x_check_distance, vr_line_position), radius=1, color="red"))

                    # Noch nicht implementiert, falls man neue Algorithmen testen will
                    if False:
                        h_states = []
                        gh_states = []
                        averaged_horizontal_states(pixel_array, y_check_distance, h_states)
                        averaged_horizontal_states(pixel_array, gy_check_distance, gh_states)
                        points = get_green_points_positions(h_states)
                        line_position = get_line_position(h_states)
                        if line_position:
                            ax.add_patch(Circle((line_position, y_check_distance), radius=1, color="green"))
                        for point in points:
                                ax.add_patch(Circle((point, gy_check_distance), radius=1, color="yellow"))
                                if check_green_point_validity(pixel_array, point, gy_check_distance):
                                    ax.add_patch(Circle((point, gy_check_distance), radius=3, color="purple"))
                                    if get_relative_green_point_position(pixel_array, point, gy_check_distance) == "left":
                                        ax.add_patch(Circle((point, gy_check_distance), radius=3, color="orange"))
                                    if get_relative_green_point_position(pixel_array, point, gy_check_distance) == "right":
                                        ax.add_patch(Circle((point, gy_check_distance), radius=3, color="blue"))
                    else:
                        print("Greem Points:", green_points)
                        for (point, validity, relative_position) in zip(green_points, green_points_validity, relative_green_points_positions):
                            ax.add_patch(Circle((point, gy_check_distance), radius=1, color="yellow"))
                            if validity:
                                ax.add_patch(Circle((point, gy_check_distance), radius=5, color="purple"))
                            if relative_position == "left":
                                ax.add_patch(Circle((point, gy_check_distance), radius=3, color="orange"))
                            if relative_position == "right":
                                ax.add_patch(Circle((point, gy_check_distance), radius=3, color="blue"))
                    
                    plt.savefig(f"imgs/{sys.argv[1]}/{file}.png")
                    plt.close()


if __name__ == "__main__":
    generate_save()

