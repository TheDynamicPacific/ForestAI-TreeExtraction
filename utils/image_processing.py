import os
import uuid
import logging
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2

def process_image(image_path, output_folder):
    """
    Process the input image for geospatial analysis:
    - Convert to grayscale
    - Apply threshold to highlight features
    - Apply noise reduction
    - Apply edge detection
    
    Args:
        image_path (str): Path to the input image
        output_folder (str): Directory to save processed images
        
    Returns:
        str: Path to the processed image
    """
    try:
        logging.info(f"Processing image: {image_path}")
        
        # Open the image
        img = Image.open(image_path)
        
        # Convert to RGB if it's not already
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Convert to numpy array for OpenCV processing
        img_array = np.array(img)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply Gaussian blur for noise reduction
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Edge detection using Canny algorithm
        edges = cv2.Canny(thresh, 50, 150)
        
        # Morphological operations to clean up the result
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to PIL Image
        processed_img = Image.fromarray(cleaned)
        
        # Save the processed image
        processed_filename = f"{uuid.uuid4().hex}_processed.png"
        output_path = os.path.join(output_folder, processed_filename)
        processed_img.save(output_path)
        
        logging.info(f"Image processing complete: {output_path}")
        return output_path
        
    except Exception as e:
        logging.error(f"Error in image processing: {str(e)}")
        raise Exception(f"Image processing failed: {str(e)}")
