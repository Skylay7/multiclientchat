import numpy as np
import cv2
from PIL import ImageGrab


class ScreenShareManager:

    @staticmethod
    def watch_share_screen(frame_data):
        if not frame_data or len(frame_data) < 10:  # Arbitrary minimum size for a valid frame
            print("Error: Frame data is too small or empty.")
            return
        # Decode the binary frame data
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

        if frame is None or frame.size == 0:
            print("Error: Received invalid frame data.")
            return False

        # Display the frame
        cv2.imshow('Screen_Capture_Window', frame)

        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return False
        return True

    @staticmethod
    def capture_frame():
        # Capture the screen
        screenshot = ImageGrab.grab()

        # Convert the screenshot to a NumPy array
        frame = np.array(screenshot)

        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        _, encoded_frame = cv2.imencode('.jpg', frame)
        encoded_frame_bytes = encoded_frame.tobytes()
        return encoded_frame_bytes
