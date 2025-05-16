import gradio as gr
import cv2
import os
import numpy as np
from pathlib import Path
from PIL import Image
import pandas as pd
import os

# Imports from codebase
from ra.processing import process_image_folder, process_single_image

def save_parameters(image_input, dp, min_dist, param1, param2, min_radius, max_radius, blur_kernel_size, blur_sigma):
    # Make sure output directory exists
    os.makedirs('parameter_logs', exist_ok=True)

    # Get a name for the image
    image_name = getattr(image_input, 'filename', 'unknown_image')

    # Prepare a row
    param_row = {
        "image_name": os.path.basename(image_name),
        "dp": dp,
        "min_dist": min_dist,
        "param1": param1,
        "param2": param2,
        "min_radius": min_radius,
        "max_radius": max_radius,
        "blur_kernel_size": blur_kernel_size,
        "blur_sigma": blur_sigma
    }

    # Create or append to a CSV
    param_file = 'parameter_logs/parameters_log.csv'
    if os.path.exists(param_file):
        df = pd.read_csv(param_file)
        df = pd.concat([df, pd.DataFrame([param_row])], ignore_index=True)
    else:
        df = pd.DataFrame([param_row])

    df.to_csv(param_file, index=False)

import re

def parse_parameter_updates(param_text_input):
    """
    Parse free-text parameter updates from user input.
    Supports sentences like:
    "Change dp to 1.5 and min_dist to 20"
    "Set blur_sigma 2.5"
    "min_radius=8"
    """
    param_map = {
        "dp": float,
        "min_dist": int,
        "param1": int,
        "param2": int,
        "min_radius": int,
        "max_radius": int,
        "blur_kernel_size": int,
        "blur_sigma": float,
    }
    
    updates = {}
    # Find all (parameter name, number) pairs
    pattern = re.compile(r"(\w+)\s*(?:=|to)?\s*([\d.]+)")
    matches = pattern.findall(param_text_input.lower())

    for key, value in matches:
        if key in param_map:
            try:
                updates[key] = param_map[key](value)
            except ValueError:
                print(f"Could not convert {value} for parameter {key}")

    return updates

def handle_chat(user_text, image_input, dp, min_dist, param1, param2, min_radius, max_radius, blur_kernel_size, blur_sigma, param_text_input):
    if "circle" in user_text.lower() and image_input is not None:
        # Initialize parameter dictionary
        param_values = {
            "dp": dp,
            "min_dist": min_dist,
            "param1": param1,
            "param2": param2,
            "min_radius": min_radius,
            "max_radius": max_radius,
            "blur_kernel_size": blur_kernel_size,
            "blur_sigma": blur_sigma
        }

        # Update values from user text
        if param_text_input:
            updates = parse_parameter_updates(param_text_input)
            for key, value in updates.items():
                if key in param_values:
                    param_values[key] = value

        # Process image
        output_image = process_single_image(
            image_input,
            dp=param_values["dp"],
            min_dist=param_values["min_dist"],
            param1=param_values["param1"],
            param2=param_values["param2"],
            min_radius=param_values["min_radius"],
            max_radius=param_values["max_radius"],
            blur_kernel=(param_values["blur_kernel_size"], param_values["blur_kernel_size"]),
            blur_sigma=param_values["blur_sigma"]
        )

        # Save parameters
        save_parameters(
            image_input,
            param_values["dp"],
            param_values["min_dist"],
            param_values["param1"],
            param_values["param2"],
            param_values["min_radius"],
            param_values["max_radius"],
            param_values["blur_kernel_size"],
            param_values["blur_sigma"]
        )

        # Create a summary string
        summary = f"""Processed with:
        dp={param_values["dp"]}, min_dist={param_values["min_dist"]},
        param1={param_values["param1"]}, param2={param_values["param2"]},
        min_radius={param_values["min_radius"]}, max_radius={param_values["max_radius"]},
        blur_kernel_size={param_values["blur_kernel_size"]}, blur_sigma={param_values["blur_sigma"]}
        """

        return output_image, summary

    else:
        return None, "No image processed. Please upload an image and type 'circle'."

demo = gr.Interface(
    fn=handle_chat,
    inputs=[
        gr.Textbox(lines=2, placeholder="Type your command here..."),
        gr.Image(type="pil"),
        gr.Slider(1.0, 2.0, value=1.2, label="DP"),
        gr.Slider(10, 100, value=20, step=1, label="Min Distance Between Centers"),
        gr.Slider(10, 200, value=50, step=1, label="Param1"),
        gr.Slider(10, 100, value=30, step=1, label="Param2"),
        gr.Slider(1, 100, value=5, step=1, label="Min Radius"),
        gr.Slider(1, 100, value=50, step=1, label="Max Radius"),
        gr.Slider(1, 21, value=9, step=2, label="Blur Kernel Size"),
        gr.Slider(0.1, 5.0, value=2.0, step=0.1, label="Blur Sigma"),
        gr.Textbox(lines=4, placeholder="Type parameter updates (e.g., dp=1.5, min_radius=8)")
    ],
    outputs=[
        gr.Image(type="pil"),
        gr.Textbox(label="Summary of Parameters Used")
    ],
    title="Image Circler: Chat + Sliders + Typing!",
    description="Upload an image, type your command, adjust parameters, and get both processed image and parameters summary."
)

if __name__ == "__main__":
    #iface.launch()
    demo.launch()