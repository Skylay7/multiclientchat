import numpy as np
import cv2
from mss import mss
from PIL import Image

mon = {'left': 0, 'top': 00, 'width': 2560, 'height': 1440}

with mss() as sct:
    while True:
        screenShot = sct.grab(mon)
        img = Image.frombytes(
            'RGB',
            (screenShot.width, screenShot.height),
            screenShot.rgb,
        )
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imshow('Screen_Capture_Window', frame)
        if cv2.waitKey(33) & 0xFF in (
            ord('q'),
            27,
        ):
            break