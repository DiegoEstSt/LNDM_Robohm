from robot import Robot
import cv2
import matplotlib.pyplot as plt

robot = Robot()
state_size = 300
bottom_removal_distance = 90

# Konfiguriert die Kamera des Robotes
config = robot.camera.create_still_configuration(main={"size": (700, 700)}, display="main")
robot.camera.configure(config)
robot.camera.start()

pixel_array = cv2.resize(robot.camera.capture_array("main"), dsize = (state_size, state_size))
pixel_array = pixel_array[0:state_size - 1 - bottom_removal_distance]

fig, ax = plt.subplots(1)
ax.imshow(pixel_array)

plt.savefig("test_image.png")
plt.close()

robot.stop_motors()
robot.camera.close()