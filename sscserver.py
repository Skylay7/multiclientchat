import socket
import protocol
import numpy as np
from PIL import ImageGrab
import cv2
import time


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((protocol.SERVER_IP, protocol.SERVER_PORT))
    server_socket.listen()
    connection, client_address = server_socket.accept()

    while True:
        # Capture the screen
        screenshot = ImageGrab.grab()

        # Convert the screenshot to a NumPy array
        frame = np.array(screenshot)

        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        _, encoded_frame = cv2.imencode('.jpg', frame)
        print(encoded_frame)

        connection.sendall(protocol.create_message(encoded_frame))
        time.sleep(0.1)


if __name__ == '__main__':
    main()
