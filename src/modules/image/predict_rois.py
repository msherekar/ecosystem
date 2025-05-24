# predict_rois.py

import cv2
import numpy as np
import pandas as pd
import joblib
import os
from sklearn.neighbors import KNeighborsRegressor

# Parameters
PATCH_WIDTH = 50
PATCH_HEIGHT = 50
STRIDE = 30  # Slide step

# Default rectangle dimensions if no model available
DEFAULT_RECT_WIDTH = 60
DEFAULT_RECT_HEIGHT = 60

def slide_and_predict(image_path, model_path='output/knn_model.pkl', features_path='output/roi_features.csv'):
    # Load image
    image = cv2.imread(image_path)
    clone = image.copy()

    # Set default dimensions for predictions
    rect_width = DEFAULT_RECT_WIDTH
    rect_height = DEFAULT_RECT_HEIGHT
    
    # Try to get average dimensions from training data
    if os.path.exists(features_path):
        try:
            features_df = pd.read_csv(features_path)
            if not features_df.empty:
                # Use average dimensions from training data
                rect_width = int(features_df['width'].mean())
                rect_height = int(features_df['height'].mean())
                print(f"[INFO] Using average ROI dimensions: {rect_width}x{rect_height}")
        except Exception as e:
            print(f"[WARNING] Could not read features file: {str(e)}")

    # Check if model exists, if not create a dummy model
    if not os.path.exists(model_path):
        print(f"[INFO] Model {model_path} not found. Creating a dummy model.")
        # Create a dummy model that predicts center of the image
        knn = KNeighborsRegressor(n_neighbors=1)
        # Dummy training with a single sample
        h, w = image.shape[:2]
        X = [[PATCH_WIDTH, PATCH_HEIGHT, PATCH_WIDTH/PATCH_HEIGHT, 128]]  # Dummy features
        y = [[w//2, h//2]]  # Center of image
        knn.fit(X, y)
        # Save the dummy model
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(knn, model_path)
    else:
        # Load trained model
        knn = joblib.load(model_path)

    h, w = image.shape[:2]

    # If we're using a trained model, we need to know what features it expects
    expected_features = ['width', 'height', 'aspect_ratio', 'mean_intensity']

    # Slide window across image
    for y in range(0, h - PATCH_HEIGHT, STRIDE):
        for x in range(0, w - PATCH_WIDTH, STRIDE):
            patch = image[y:y+PATCH_HEIGHT, x:x+PATCH_WIDTH]

            # Extract features
            patch_gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            width = PATCH_WIDTH
            height = PATCH_HEIGHT
            aspect_ratio = width / height
            mean_intensity = np.mean(patch_gray)
            
            # Force column order during prediction
            features = pd.DataFrame([[
                width,
                height,
                aspect_ratio,
                mean_intensity
            ]], columns=expected_features)

            # Predict center
            predicted_center = knn.predict(features)[0]
            cx, cy = map(int, predicted_center)

            # Draw a rectangle centered at (cx, cy)
            half_width = rect_width // 2
            half_height = rect_height // 2
            top_left = (cx - half_width, cy - half_height)
            bottom_right = (cx + half_width, cy + half_height)

            # Ensure rectangle is inside image bounds
            top_left = (max(0, top_left[0]), max(0, top_left[1]))
            bottom_right = (min(w, bottom_right[0]), min(h, bottom_right[1]))

            cv2.rectangle(clone, top_left, bottom_right, (0, 0, 255), 2)  # Red rectangle

    # Save the result
    os.makedirs('output/predicted', exist_ok=True)
    output_path = 'output/predicted/predicted_image_rects.png'
    cv2.imwrite(output_path, clone)
    print(f"[INFO] Predicted ROI rectangles drawn and saved to {output_path}")

    # Display
    # cv2.imshow('Predicted Rectangles', clone)
    
    # cv2.destroyAllWindows()
    return output_path

# if __name__ == "__main__":
    # slide_and_predict('/Users/mukulsherekar/pythonProject/RA-Project/src/roi_selector/images/Image_01.tif')
