"""
Segmentation utilities for image processing inspired by CLIPSeg techniques.
This is a simplified version that does not require the full transformers library.
"""

import os
import logging
import numpy as np
import cv2
from PIL import Image
from utils.geospatial import extract_contours, simplify_polygons, regularize_polygons, merge_nearby_polygons

def segment_by_color_threshold(image_path, output_path=None, 
                              threshold=127, color_channel=1, 
                              smoothing_sigma=1.0):
    """
    Segment an image based on color thresholding.
    This is a simple segmentation inspired by more complex models like CLIPSeg.
    
    Args:
        image_path (str): Path to the input image
        output_path (str, optional): Path to save the segmentation mask
        threshold (int): Pixel intensity threshold (0-255)
        color_channel (int): Color channel to use for thresholding (0=R, 1=G, 2=B)
        smoothing_sigma (float): Gaussian smoothing sigma
        
    Returns:
        numpy.ndarray: Segmentation mask
    """
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            # Try using PIL if OpenCV fails
            pil_img = Image.open(image_path).convert('RGB')
            img = np.array(pil_img)
            img = img[:, :, ::-1]  # RGB to BGR for OpenCV compatibility
        
        # Split channels and use the specified channel for segmentation
        b, g, r = cv2.split(img)
        channels = [r, g, b]
        
        if 0 <= color_channel < 3:
            channel = channels[color_channel]
        else:
            # Use grayscale if invalid channel specified
            channel = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        if smoothing_sigma > 0:
            channel = cv2.GaussianBlur(channel, (0, 0), smoothing_sigma)
        
        # Apply thresholding to create binary mask
        _, mask = cv2.threshold(channel, threshold, 255, cv2.THRESH_BINARY)
        
        # Save the mask if output path is provided
        if output_path:
            cv2.imwrite(output_path, mask)
            logging.info(f"Saved segmentation mask to {output_path}")
            
        return mask
        
    except Exception as e:
        logging.error(f"Error in segmentation: {str(e)}")
        return None

def segment_by_adaptive_threshold(image_path, output_path=None, 
                                 block_size=11, c=2, 
                                 smoothing_sigma=1.0):
    """
    Segment an image using adaptive thresholding for better handling of
    lighting variations.
    
    Args:
        image_path (str): Path to the input image
        output_path (str, optional): Path to save the segmentation mask
        block_size (int): Size of the pixel neighborhood for threshold calculation
        c (int): Constant subtracted from the mean
        smoothing_sigma (float): Gaussian smoothing sigma
        
    Returns:
        numpy.ndarray: Segmentation mask
    """
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            # Try using PIL if OpenCV fails
            pil_img = Image.open(image_path).convert('RGB')
            img = np.array(pil_img)
            img = img[:, :, ::-1]  # RGB to BGR for OpenCV compatibility
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        if smoothing_sigma > 0:
            gray = cv2.GaussianBlur(gray, (0, 0), smoothing_sigma)
        
        # Apply adaptive thresholding
        mask = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, block_size, c
        )
        
        # Save the mask if output path is provided
        if output_path:
            cv2.imwrite(output_path, mask)
            logging.info(f"Saved segmentation mask to {output_path}")
            
        return mask
        
    except Exception as e:
        logging.error(f"Error in segmentation: {str(e)}")
        return None

def segment_by_otsu(image_path, output_path=None, smoothing_sigma=1.0):
    """
    Segment an image using Otsu's automatic thresholding method.
    
    Args:
        image_path (str): Path to the input image
        output_path (str, optional): Path to save the segmentation mask
        smoothing_sigma (float): Gaussian smoothing sigma
        
    Returns:
        numpy.ndarray: Segmentation mask
    """
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            # Try using PIL if OpenCV fails
            pil_img = Image.open(image_path).convert('RGB')
            img = np.array(pil_img)
            img = img[:, :, ::-1]  # RGB to BGR for OpenCV compatibility
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        if smoothing_sigma > 0:
            gray = cv2.GaussianBlur(gray, (0, 0), smoothing_sigma)
        
        # Apply Otsu's thresholding
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Save the mask if output path is provided
        if output_path:
            cv2.imwrite(output_path, mask)
            logging.info(f"Saved segmentation mask to {output_path}")
            
        return mask
        
    except Exception as e:
        logging.error(f"Error in segmentation: {str(e)}")
        return None

def segment_and_extract_features(image_path, output_mask_path=None, 
                                feature_type="buildings", 
                                min_area=50, simplify_tolerance=2.0,
                                merge_distance=5.0):
    """
    Complete pipeline for segmentation and feature extraction.
    
    Args:
        image_path (str): Path to the input image
        output_mask_path (str, optional): Path to save the segmentation mask
        feature_type (str): Type of features to extract ("buildings", "trees", "water", "roads")
        min_area (int): Minimum feature area to keep
        simplify_tolerance (float): Tolerance for polygon simplification
        merge_distance (float): Distance for merging nearby polygons
        
    Returns:
        tuple: (mask, polygons) - Segmentation mask and list of simplified Shapely polygons
    """
    # Choose segmentation method based on feature type
    if feature_type.lower() == "buildings":
        # Buildings typically have clean edges and good contrast
        mask = segment_by_adaptive_threshold(
            image_path, output_mask_path, 
            block_size=15, c=2, smoothing_sigma=1.0
        )
    elif feature_type.lower() == "trees" or feature_type.lower() == "vegetation":
        # Trees typically strong in green channel
        mask = segment_by_color_threshold(
            image_path, output_mask_path,
            threshold=140, color_channel=1, smoothing_sigma=1.5
        )
    elif feature_type.lower() == "water":
        # Water typically has distinct spectral properties
        mask = segment_by_color_threshold(
            image_path, output_mask_path,
            threshold=120, color_channel=0, smoothing_sigma=2.0
        )
    else:
        # Default to Otsu for unknown feature types
        mask = segment_by_otsu(
            image_path, output_mask_path, smoothing_sigma=1.0
        )
    
    if mask is None:
        logging.error("Segmentation failed")
        return None, []
    
    # Save mask temporarily if needed for contour extraction
    temp_mask_path = None
    if not output_mask_path:
        temp_mask_path = os.path.join(
            os.path.dirname(image_path),
            f"{os.path.splitext(os.path.basename(image_path))[0]}_mask.png"
        )
        cv2.imwrite(temp_mask_path, mask)
        mask_path = temp_mask_path
    else:
        mask_path = output_mask_path
    
    # Extract contours from the mask
    polygons = extract_contours(mask_path, min_area=min_area)
    logging.info(f"Extracted {len(polygons)} initial polygons")
    
    # Clean up temporary file if created
    if temp_mask_path and os.path.exists(temp_mask_path):
        os.remove(temp_mask_path)
    
    # Simplify polygons
    polygons = simplify_polygons(polygons, tolerance=simplify_tolerance)
    
    # If buildings, regularize them to make more rectangular
    if feature_type.lower() == "buildings":
        polygons = regularize_polygons(polygons)
    
    # Merge nearby polygons to reduce count
    polygons = merge_nearby_polygons(polygons, distance_threshold=merge_distance)
    logging.info(f"After processing: {len(polygons)} polygons")
    
    return mask, polygons