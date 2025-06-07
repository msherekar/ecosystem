# utils.py
import cv2
import numpy as np
import pandas as pd

# Globals
start_point = None
cropping = False
roi_count = 0
roi_features = []

def click_and_crop(event, x, y, flags, param):
    global start_point, cropping, roi_count, roi_features

    img = param['image']

    if event == cv2.EVENT_LBUTTONDOWN:
        start_point = (x, y)
        cropping = True

    elif event == cv2.EVENT_LBUTTONUP:
        end_point = (x, y)
        cropping = False

        # Draw rectangle
        cv2.rectangle(img, start_point, end_point, (0, 255, 0), 2)

        x1, y1 = start_point
        x2, y2 = end_point

        # Ensure correct ordering (top-left to bottom-right)
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        roi = img[y1:y2, x1:x2]

        # Save cropped ROI
        roi_filename = f"output/roi_{roi_count}.png"
        cv2.imwrite(roi_filename, roi)
        print(f"[INFO] Saved ROI to {roi_filename}")

        # Extract Features
        width = x2 - x1
        height = y2 - y1
        center_x = x1 + width / 2
        center_y = y1 + height / 2
        aspect_ratio = width / height if height != 0 else 0
        mean_intensity = np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY))

        # Store features
        roi_features.append({
            'roi_filename': roi_filename,
            'center_x': center_x,
            'center_y': center_y,
            'width': width,
            'height': height,
            'aspect_ratio': aspect_ratio,
            'mean_intensity': mean_intensity
        })

        roi_count += 1

def save_features():
    # Save features to a CSV
    df = pd.DataFrame(roi_features)
    df.to_csv('output/roi_features.csv', index=False)
    print("[INFO] Saved features to output/roi_features.csv")
