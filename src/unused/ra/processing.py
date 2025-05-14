import cv2
import numpy as np
from matplotlib import pyplot as plt
from scipy import ndimage
from skimage import segmentation
from skimage import restoration
from skimage.feature import peak_local_max
from skimage import measure
import pandas as pd
import readlif
from readlif.reader import LifFile
from matplotlib import pyplot as plt
from PIL import Image
import os
from pathlib import Path
# CONSTANTS
DP            = 1.2     # Inverse ratio of accumulator resolution to image resolution
MIN_DIST      = 20      # Minimum distance between detected circle centers
PARAM1        = 50      # Upper threshold for Canny edge detector (lower is half of this)
PARAM2        = 30      # Accumulator threshold for circle detection (smaller -> more false circles)
MIN_RADIUS    = 5       # Minimum circle radius
MAX_RADIUS    = 50      # Maximum circle radius
BLUR_KERNEL   = (9, 9)  # Gaussian blur kernel size
BLUR_SIGMA    = 2       # Gaussian blur sigma

# Initialize data frame and set working directory
data_frame_All = pd.DataFrame()

# path to the image files
path = '/Users/mukulsherekar/pythonProject/RA-Project/images/'
# create output directory at same level as images if it doesn't exist
output_path = os.path.join('/Users/mukulsherekar/pythonProject/RA-Project/', 'output_images')

def process_single_image(image, dp, min_dist, param1, param2, min_radius, max_radius, blur_kernel, blur_sigma):
    # Convert PIL to OpenCV
    img = np.array(image)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, blur_kernel, blur_sigma)

    # Detect circles
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=dp,
        minDist=min_dist,
        param1=param1,
        param2=param2,
        minRadius=min_radius,
        maxRadius=max_radius
    )

    # Draw circles
    if circles is not None:
        circles = np.uint16(np.around(circles[0, :]))
        for (x, y, r) in circles:
            cv2.circle(img, (x, y), r, (0, 255, 0), 2)
            cv2.circle(img, (x, y), 2, (0, 0, 255), 3)

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img)


def process_image_folder(input_path):
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    # Read the image files from the input path
    images = [f for f in os.listdir(input_path) if f.endswith('.tif')]

    # Print the number of images
    print(f"Number of images found: {len(images)}")

    # Loop over the images
    for image in images:
        # Read the image
        img = cv2.imread(os.path.join(input_path, image))
        if img is None:
            print(f"Error reading image: {image}")
            continue

        # Convert the image to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Reduce noise to improve circle detection
        blurred = cv2.GaussianBlur(gray, BLUR_KERNEL, BLUR_SIGMA)

        # Detect circles using Hough transform
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=DP,
            minDist=MIN_DIST,
            param1=PARAM1,
            param2=PARAM2,
            minRadius=MIN_RADIUS,
            maxRadius=MAX_RADIUS
        )

        # If circles are found, round and draw them
        if circles is not None:
            circles = np.uint16(np.around(circles[0, :]))
            for (x, y, r) in circles:
                # Draw the outer circle
                cv2.circle(img, (x, y), r, (0, 255, 0), 2)
                # Draw the circle center
                cv2.circle(img, (x, y), 2, (0, 0, 255), 3)

        # Save the image with circles in the output directory
        output_filename = f'detected_circles_{os.path.splitext(image)[0]}.png'
        cv2.imwrite(os.path.join(output_path, output_filename), img)

    print(f"Processed images saved in: {output_path}")


if __name__ == "__main__":
    process_image_folder(path)





