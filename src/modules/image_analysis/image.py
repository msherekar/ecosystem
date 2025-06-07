import streamlit as st
import pandas as pd
import numpy as np
from chat.chatbot import ask_chatbot
import plotly.express as px
import cv2
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import io

# Initialize session state
st.session_state.setdefault("clicked_button", None)
st.session_state.setdefault("original_image", {})
st.session_state.setdefault("processed_image", {})
st.session_state.setdefault("roi_boxes", {})

# CSS for scrollable container
st.markdown("""
    <style>
    .scrollable-image-container {
        height: 600px;
        overflow-y: auto;
        border: 1px solid #ddd;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)


def control_panel():
    functions = st.columns([0.6, 0.5, 0.6, 0.6, 0.8, 0.8, 0.8, 0.8, 0.8])
    labels = ["Edit", "B/C", "Crop", "ROI", "Rotate", "Filters", "Threshold", "Counter", "Tracking"]

    for col, label in zip(functions, labels):
        with col:
            if col.button(label, key=f'key_{label}', use_container_width=True):
                st.session_state.clicked_button = label


def open_image(file_path):
    file_name = os.path.basename(file_path)
    if file_name in st.session_state.original_image.keys():
        st.warning("Image with the same name already exists.")
        return None
    try:
        # Read image using OpenCV
        image = cv2.imread(file_path)
        if image is None:
            st.error("Failed to load image")
            return None
            
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Store original image
        st.session_state.original_image[file_name] = image
        st.session_state.processed_image[file_name] = image.copy()
        
        return image
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None


def adjust_brightness_contrast(image, brightness=0, contrast=0):
    img = image.astype(np.float32)
    img = img + brightness
    img = img * (1 + contrast)
    img = np.clip(img, 0, 255)
    return img.astype(np.uint8)


def apply_filter(image, filter_type):
    try:
        if filter_type == "Blur":
            return cv2.GaussianBlur(image, (5, 5), 0)
        elif filter_type == "Sharpen":
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            return cv2.filter2D(image, -1, kernel)
        elif filter_type == "Edge":
            return cv2.Canny(image, 100, 200)
        else:
            return image
    except Exception as e:
        st.error(f"Error applying filter: {e}")
        return image


def threshold_image(image, threshold_value=127):
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        return thresh
    except Exception as e:
        st.error(f"Error applying threshold: {e}")
        return image


def rotate_image(image, angle):
    try:
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, matrix, (width, height))
    except Exception as e:
        st.error(f"Error rotating image: {e}")
        return image

def reset_image(key):
    st.session_state.processed_image[key] = st.session_state.original_image[key].copy()


def draw_roi(image, key):

    height, width = image.shape[:2]

    # Sliders for new ROI
    col1, col2 = st.columns(2)
    with col1:
        x1 = st.slider("Left (x1)", 0, width - 1, 0, key=f"x1_{key}")
        y1 = st.slider("Top (y1)", 0, height - 1, 0, key=f"y1_{key}")
    with col2:
        x2 = st.slider("Right (x2)", x1 + 1, width, key=f"x2_{key}")
        y2 = st.slider("Bottom (y2)", y1 + 1, height, key=f"y2_{key}")

    # Create preview image with all ROIs (stored + live)
    img_copy = image.copy()
    image_pil = Image.fromarray(img_copy)
    draw = ImageDraw.Draw(image_pil)

    # Draw stored ROIs in red
    for i, (rx1, ry1, rx2, ry2) in enumerate(st.session_state.roi_boxes[key]):
        draw.rectangle([rx1, ry1, rx2, ry2], outline="red", width=3)
        draw.text((rx1 + 5, ry1 + 5), f"{i+1}", fill="red")

    # Draw current ROI in yellow
    draw.rectangle([x1, y1, x2, y2], outline="yellow", width=2)
    draw.text((x1 + 5, y1 + 5), "New", fill="yellow")

    st.image(image_pil, caption="ROI Preview (Red = Saved, Yellow = Current)", use_container_width=True)

    # Add new ROI
    if st.button("➕ Add ROI", key=f"add_roi_{key}"):
        st.session_state.roi_boxes[key].append((x1, y1, x2, y2))
        st.success(f"ROI {len(st.session_state.roi_boxes[key])} added.")

    # Show all ROI crops
    for i, (rx1, ry1, rx2, ry2) in enumerate(st.session_state.roi_boxes[key]):
        roi = image[ry1:ry2, rx1:rx2]
        st.image(roi, caption=f"ROI {i+1}", use_container_width=True)

    # Apply last ROI
    if st.button("✅ Apply Last ROI as Crop", key=f"apply_last_roi_{key}"):
        rx1, ry1, rx2, ry2 = st.session_state.roi_boxes[key][-1]
        roi = image[ry1:ry2, rx1:rx2]
        st.session_state.processed_image[key] = roi
        st.session_state.clicked_button = None
        st.rerun()

    # Clear ROIs
    if st.button("🗑️ Clear ROIs", key=f"clear_rois_{key}"):
        st.session_state.roi_boxes[key] = []
        st.rerun()




def image_main():
    control_panel()

    processed_keys = list(st.session_state.processed_image.keys())
    if not processed_keys:
        st.warning("No images loaded. Please load an image first.")
        return

    # Handle different operations
    clicked = st.session_state.clicked_button
    if clicked in ["B/C", "Filters", "Threshold", "Rotate", "ROI"]:
        if len(processed_keys) == 1:
            key = processed_keys[0]
        else:
            key = st.selectbox("Select Image", processed_keys, key=f"selector_{clicked}")

        image = st.session_state.processed_image[key]

        if clicked == "B/C":
            with st.expander("Brightness and Contrast"):
                brightness = st.slider("Brightness", -100, 100, 0, key="brightness_slider")
                contrast = st.slider("Contrast", -100, 100, 0, key="contrast_slider")
                if st.button("Apply", key="apply_bc"):
                    adjusted = adjust_brightness_contrast(image, brightness, contrast / 100)
                    st.session_state.processed_image[key] = adjusted
                    st.session_state.clicked_button = None
                    st.rerun()

        elif clicked == "Filters":
            with st.expander("Image Filters"):
                filter_type = st.selectbox("Select Filter", ["Blur", "Sharpen", "Edge"])
                if st.button("Apply Filter"):
                    filtered = apply_filter(image, filter_type)
                    st.session_state.processed_image[key] = filtered
                    st.session_state.clicked_button = None
                    st.rerun()

        elif clicked == "Threshold":
            with st.expander("Threshold"):
                threshold = st.slider("Threshold Value", 0, 255, 127)
                if st.button("Apply Threshold"):
                    thresh = threshold_image(image, threshold)
                    st.session_state.processed_image[key] = thresh
                    st.session_state.clicked_button = None
                    st.rerun()

        elif clicked == "Rotate":
            with st.expander("Rotate Image"):
                angle = st.slider("Rotation Angle", -180, 180, 0)
                if st.button("Rotate"):
                    rotated = rotate_image(image, angle)
                    st.session_state.processed_image[key] = rotated
                    st.session_state.clicked_button = None
                    st.rerun()
                    
        elif clicked == "ROI":
            with st.expander("Region of Interest"):
                draw_roi(image, key)

    # Display all processed images in scrollable container
    st.markdown('<div class="scrollable-image-container">', unsafe_allow_html=True)
    for key in st.session_state.processed_image.keys():
        img = st.session_state.processed_image[key]
        if img is not None:
            st.image(img, caption=key, use_container_width=True)
        else:
            st.warning(f"Image for key '{key}' is None and cannot be displayed.")
    st.markdown('</div>', unsafe_allow_html=True)
