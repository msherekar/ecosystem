# main.py
import cv2
import os
from utils import click_and_crop
# After exiting the while loop
from utils import save_features



# Create output directory if not exists
os.makedirs('output', exist_ok=True)

# Load image
image_path = '/Users/mukulsherekar/pythonProject/RA-Project/src/roi_selector/images/Image_01.tif'   # <-- put your image here
image = cv2.imread(image_path)
clone = image.copy()

# Set up window
cv2.namedWindow("Image")
cv2.setMouseCallback("Image", click_and_crop, {'image': image})

print("[INFO] Instructions:")
print("- Left click and drag: Select ROI")
print("- Press 'r' to reset")
print("- Press 'c' to confirm and continue")

while True:
    cv2.imshow("Image", image)
    key = cv2.waitKey(1) & 0xFF

    # Reset the selection
    if key == ord("r"):
        image = clone.copy()

    # Confirm and exit
    elif key == ord("c"):
        save_features()
        break


cv2.destroyAllWindows()
