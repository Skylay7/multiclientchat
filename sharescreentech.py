import cv2
import numpy as np
from PIL import ImageGrab


def main():
    # Create a named OpenCV window
    cv2.namedWindow('Screen_Capture_Window', cv2.WINDOW_NORMAL)

    while True:
        # Capture the screen
        screenshot = ImageGrab.grab()

        # Convert the screenshot to a NumPy array
        frame = np.array(screenshot)

        # Convert the color from RGB (Pillow) to BGR (OpenCV format)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Display the frame in the same OpenCV window
        cv2.imshow('Screen_Capture_Window', frame)

        # Refresh the window and check for 'q' key press to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources and close the window
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
