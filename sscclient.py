import socket
import protocol
import numpy as np
import cv2


def main():
    print("trying")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((protocol.SERVER_IP, protocol.SERVER_PORT))
    print(f"Connected to {protocol.SERVER_IP} on port {protocol.SERVER_PORT}...")

    cv2.namedWindow('Screen_Capture_Window', cv2.WINDOW_NORMAL)
    try:
        while True:
            frame_data = protocol.get_analyzed_data(client_socket)
            if frame_data is None:
                continue
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

            # Display the frame
            cv2.imshow('Screen_Capture_Window', frame)

            # Exit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
