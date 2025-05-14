#!/usr/bin/env python
"""
Runner script for the image processing module
"""
from ra.processing import process_image_folder

if __name__ == "__main__":
    input_directory = '/Users/mukulsherekar/pythonProject/RA-Project/images/'
    process_image_folder(input_directory) 