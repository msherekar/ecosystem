# gradio_app.py

import gradio as gr
import cv2
import os
import numpy as np
from train_model import train_knn_model
from predict_rois import slide_and_predict

# Create folders if needed
os.makedirs('images', exist_ok=True)
os.makedirs('output', exist_ok=True)

def process_image(image):
    if image is None:
        raise ValueError("No image uploaded.")
    
    # Save uploaded image with any sketches/drawings
    image_path = os.path.join('images', 'uploaded_image.png')
    cv2.imwrite(image_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    print(f"[INFO] Image saved at {image_path}")

    # Train model
    train_knn_model()

    # Predict ROIs
    predicted_image_path = slide_and_predict(image_path)

    # Load predicted image
    result_image = cv2.imread(predicted_image_path)
    result_image = cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB)

    if result_image is None:
        raise ValueError("Error loading result image.")
    
    return result_image

with gr.Blocks() as demo:
    gr.Markdown("# ROI Prediction System")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("""
            ## Instructions:
            1. Upload an image
            2. Use the sketch tool to draw rectangles around ROIs
            3. Click 'Submit and Predict'
            """)
            
            # Use Image with sketch tool
            input_image = gr.Image(
                type="numpy", 
                label="Upload and Draw", 
                tool="sketch", 
                brush_radius=3,
                height=512,
                width=512
            )
            
            submit_btn = gr.Button("Submit and Predict")
        
        with gr.Column():
            output_image = gr.Image(
                type="numpy", 
                label="Predicted ROIs",
                height=512,
                width=512
            )
    
    submit_btn.click(
        fn=process_image,
        inputs=input_image,
        outputs=output_image
    )

if __name__ == "__main__":
    demo.launch(share=True)
