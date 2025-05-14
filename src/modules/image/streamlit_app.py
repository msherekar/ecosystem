# streamlit_app.py

import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import cv2
import numpy as np
import pandas as pd
from PIL import Image
from train_model import train_knn_model
from predict_rois import slide_and_predict

# Ensure directories
os.makedirs("images", exist_ok=True)
os.makedirs("output", exist_ok=True)

st.set_page_config(layout="wide")  # Use wide layout for more space

st.title("ROI Prediction System")

st.markdown("""
### Instructions:
1. Upload an image
2. Draw **rectangles** around regions of interest
3. Click **Submit and Predict**
""")

# Upload
uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    # Load image and get dimensions
    image = Image.open(uploaded_file).convert("RGB")
    img_width, img_height = image.size
    image_np = np.array(image)
    
    st.subheader("Draw Rectangles (ROIs)")
    
    # Display original image info
    st.info(f"Original image dimensions: {img_width}x{img_height} pixels")
    
    # Calculate appropriate display size while maintaining aspect ratio
    max_display_width = 800  # Limit max width for UI
    max_display_height = 600  # Limit max height for UI
    
    # Calculate scale factor based on both dimensions
    width_scale = max_display_width / img_width if img_width > max_display_width else 1
    height_scale = max_display_height / img_height if img_height > max_display_height else 1
    
    # Use the smaller scale factor to ensure the image fits
    scale_factor = min(width_scale, height_scale)
    
    display_width = int(img_width * scale_factor)
    display_height = int(img_height * scale_factor)
    
    # Canvas for drawing
    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.3)",
        stroke_width=2,
        stroke_color="red",
        background_image=image,
        update_streamlit=True,
        height=display_height,
        width=display_width,
        drawing_mode="rect",
        key="canvas",
        display_toolbar=True
    )
    
    # If image size was changed for display, show a note
    if scale_factor < 1.0:
        st.caption(f"Note: Image is displayed at {int(scale_factor * 100)}% scale for better viewing. ROIs will be scaled back to original dimensions.")

    if st.button("Submit and Predict"):
        # Save uploaded image
        image_path = os.path.join("images", "uploaded_image.png")
        image.save(image_path)
        st.success(f"Saved input image to {image_path}")

        # Create a copy of the image with ROIs for visualization
        annotated_image = image_np.copy()
        
        # Create ROI CSV file for training
        roi_data = []
        if canvas_result.json_data is not None:
            for obj in canvas_result.json_data["objects"]:
                if obj["type"] == "rect":
                    # Get coordinates and adjust if needed
                    x, y = int(obj["left"]), int(obj["top"])
                    w, h = int(obj["width"]), int(obj["height"])
                    
                    # If image was scaled for display, convert coordinates back to original scale
                    if scale_factor < 1.0:
                        x = int(x / scale_factor)
                        y = int(y / scale_factor)
                        w = int(w / scale_factor)
                        h = int(h / scale_factor)
                    
                    # Save each rectangle as a row in the ROI dataframe
                    roi_data.append({
                        'filename': 'uploaded_image.png',
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h
                    })
                    
                    # Draw rectangle on the annotated image
                    cv2.rectangle(annotated_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
            # Create and save the CSV file needed for training
            if roi_data:
                roi_df = pd.DataFrame(roi_data)
                csv_path = os.path.join("images", "saved_rois.csv")
                roi_df.to_csv(csv_path, index=False)
                st.success(f"Saved {len(roi_data)} ROIs to {csv_path}")
                
                # Display average ROI dimensions
                avg_width = int(roi_df['width'].mean())
                avg_height = int(roi_df['height'].mean())
                st.info(f"Average ROI dimensions from your annotations: {avg_width}x{avg_height} pixels")
            else:
                st.warning("No ROIs were drawn. Please draw at least one ROI.")
                st.stop()

        # Run training and prediction
        train_knn_model()
        predicted_path = slide_and_predict(image_path)

        # Show images side by side
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Your Annotations")
            st.image(annotated_image, caption="Original with ROIs", use_column_width=True)
            
        with col2:
            st.subheader("Predicted ROIs")
            result = cv2.imread(predicted_path)
            if result is not None:
                result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
                st.image(result, caption="Model predictions", use_column_width=True)
            else:
                st.error("Failed to load predicted image.")
