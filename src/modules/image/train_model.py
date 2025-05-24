# train_model.py

import pandas as pd
from sklearn.neighbors import KNeighborsRegressor
import joblib
import pandas as pd
import cv2
import os
import numpy as np

def train_local_knn_model(csv_path='output/roi_features.csv', model_path='output/knn_model.pkl'):
    # Load extracted features
    df = pd.read_csv(csv_path)

    # Define input (X) and target (Y)
    X = df[['width', 'height', 'aspect_ratio', 'mean_intensity']]
    y = df[['center_x', 'center_y']]

    # Train simple kNN model
    knn = KNeighborsRegressor(n_neighbors=1)  # 1 neighbor for very simple memorization
    knn.fit(X, y)

    # Save model
    joblib.dump(knn, model_path)
    print(f"[INFO] Model saved to {model_path}")

def train_knn_model(roi_csv_path='images/saved_rois.csv'):
    try:
        # Check if the CSV file exists
        if not os.path.exists(roi_csv_path):
            print(f"[WARNING] ROI CSV file {roi_csv_path} not found.")
            return
        
        # Load ROI info
        roi_df = pd.read_csv(roi_csv_path)
        
        print(f"[INFO] Training KNN with {len(roi_df)} ROIs...")
        
        # Create features dataframe
        features = []
        
        for idx, row in roi_df.iterrows():
            # Load image
            img_path = os.path.join('images', row['filename'])
            if not os.path.exists(img_path):
                print(f"[WARNING] Image {img_path} not found, skipping ROI.")
                continue
                
            img = cv2.imread(img_path)
            if img is None:
                print(f"[WARNING] Could not load {img_path}, skipping ROI.")
                continue
                
            # Extract ROI
            x, y, w, h = int(row['x']), int(row['y']), int(row['width']), int(row['height'])
            roi = img[y:y+h, x:x+w]
            
            # Skip if ROI is invalid
            if roi.size == 0:
                print(f"[WARNING] Invalid ROI at [{x},{y},{w},{h}], skipping.")
                continue
            
            # Extract features
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            aspect_ratio = w / h
            mean_intensity = np.mean(roi_gray)
            
            # Compute center coordinates (relative to the whole image)
            center_x = x + w/2
            center_y = y + h/2
            
            # Add to features list
            features.append({
                'width': w,
                'height': h,
                'aspect_ratio': aspect_ratio,
                'mean_intensity': mean_intensity,
                'center_x': center_x,
                'center_y': center_y
            })
            
            print(f"[INFO] Processed ROI {idx+1} from {row['filename']} at [{x},{y},{w},{h}]")
        
        # If we have features, train and save the model
        if features:
            features_df = pd.DataFrame(features)
            
            # Create output directory if it doesn't exist
            os.makedirs('output', exist_ok=True)
            
            # Save features for reference
            features_path = 'output/roi_features.csv'
            features_df.to_csv(features_path, index=False)
            
            # Train a KNN model
            X = features_df[['width', 'height', 'aspect_ratio', 'mean_intensity']]
            y = features_df[['center_x', 'center_y']]
            
            knn = KNeighborsRegressor(n_neighbors=1)  # 1 neighbor for very simple model
            knn.fit(X, y)
            
            # Save model
            model_path = 'output/knn_model.pkl'
            joblib.dump(knn, model_path)
            print(f"[INFO] KNN model trained and saved to {model_path}")
        else:
            print("[WARNING] No valid ROIs to train on.")
        
        print("[INFO] KNN training complete!")
        
    except Exception as e:
        print(f"[ERROR] Exception during training: {str(e)}")

if __name__ == "__main__":
    train_knn_model()
