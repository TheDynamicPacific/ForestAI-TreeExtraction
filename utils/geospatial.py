"""
Geospatial utilities for image processing and GeoJSON generation.
This module adapts techniques from the geoai library for better polygon generation
with simplified dependencies.
"""

import os
import logging
import uuid
import numpy as np
import cv2
from PIL import Image
import json
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely import ops

def extract_contours(image_path, min_area=50, epsilon_factor=0.002):
    """
    Extract contours from an image and convert them to polygons.
    Uses OpenCV's contour detection with douglas-peucker simplification.
    
    Args:
        image_path (str): Path to the processed image
        min_area (int): Minimum contour area to keep
        epsilon_factor (float): Simplification factor for douglas-peucker algorithm
        
    Returns:
        list: List of polygon objects
    """
    try:
        # Read the image
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            # Try using PIL if OpenCV fails
            pil_img = Image.open(image_path).convert('L')
            img = np.array(pil_img)
            
        # Apply threshold if needed
        _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        polygons = []
        for contour in contours:
            # Filter small contours
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
                
            # Apply Douglas-Peucker algorithm to simplify contours
            epsilon = epsilon_factor * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Convert to polygon
            if len(approx) >= 3:  # At least 3 points needed for a polygon
                polygon_points = []
                for point in approx:
                    x, y = point[0]
                    polygon_points.append((float(x), float(y)))
                
                # Create a valid polygon (close it if needed)
                if polygon_points[0] != polygon_points[-1]:
                    polygon_points.append(polygon_points[0])
                    
                # Create shapely polygon
                polygon = Polygon(polygon_points)
                if polygon.is_valid:
                    polygons.append(polygon)
        
        return polygons
        
    except Exception as e:
        logging.error(f"Error extracting contours: {str(e)}")
        return []

def simplify_polygons(polygons, tolerance=1.0):
    """
    Apply polygon simplification to reduce the number of vertices.
    
    Args:
        polygons (list): List of shapely Polygon objects
        tolerance (float): Simplification tolerance
        
    Returns:
        list: List of simplified polygons
    """
    simplified = []
    for polygon in polygons:
        # Apply simplification
        simp = polygon.simplify(tolerance, preserve_topology=True)
        if simp.is_valid and not simp.is_empty:
            simplified.append(simp)
    
    return simplified

def regularize_polygons(polygons):
    """
    Regularize polygons to make them more rectangular when appropriate.
    
    Args:
        polygons (list): List of shapely Polygon objects
        
    Returns:
        list: List of regularized polygons
    """
    regularized = []
    for polygon in polygons:
        try:
            # Check if the polygon is roughly rectangular using a simple heuristic
            bounds = polygon.bounds
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            area_ratio = polygon.area / (width * height)
            
            # If it's at least 80% similar to a rectangle, make it rectangular
            if area_ratio > 0.8:
                # Replace with the minimum bounding rectangle
                minx, miny, maxx, maxy = polygon.bounds
                regularized.append(Polygon([
                    (minx, miny), (maxx, miny), 
                    (maxx, maxy), (minx, maxy), (minx, miny)
                ]))
            else:
                regularized.append(polygon)
        except Exception as e:
            logging.warning(f"Error regularizing polygon: {str(e)}")
            regularized.append(polygon)
    
    return regularized

def merge_nearby_polygons(polygons, distance_threshold=5.0):
    """
    Merge polygons that are close to each other to reduce the polygon count.
    
    Args:
        polygons (list): List of shapely Polygon objects
        distance_threshold (float): Distance threshold for merging
        
    Returns:
        list: List of merged polygons
    """
    if not polygons:
        return []
        
    # Buffer polygons slightly to create overlaps for nearby polygons
    buffered = [polygon.buffer(distance_threshold) for polygon in polygons]
    
    # Union all buffered polygons
    union = ops.unary_union(buffered)
    
    # Convert the result to a list of polygons
    if isinstance(union, Polygon):
        return [union]
    elif isinstance(union, MultiPolygon):
        return list(union.geoms)
    else:
        return []

def convert_to_geojson_with_transform(polygons, image_height, image_width, 
                                    min_lat=None, min_lon=None, max_lat=None, max_lon=None):
    """
    Convert polygons to GeoJSON with proper geographic transformation.
    
    Args:
        polygons (list): List of shapely Polygon objects
        image_height (int): Height of the source image
        image_width (int): Width of the source image
        min_lat (float, optional): Minimum latitude for geographic bounds
        min_lon (float, optional): Minimum longitude for geographic bounds
        max_lat (float, optional): Maximum latitude for geographic bounds
        max_lon (float, optional): Maximum longitude for geographic bounds
        
    Returns:
        dict: GeoJSON object
    """
    # Set default geographic bounds if not provided
    if None in (min_lon, min_lat, max_lon, max_lat):
        # Default to somewhere neutral (center of Atlantic Ocean)
        min_lon, min_lat = -30.0, 0.0
        max_lon, max_lat = -20.0, 10.0
    
    # Create a GeoJSON feature collection
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Function to transform pixel coordinates to geographic coordinates
    def transform_point(x, y):
        # Linear interpolation
        lon = min_lon + (x / image_width) * (max_lon - min_lon)
        # Invert y-axis for geographic coordinates
        lat = max_lat - (y / image_height) * (max_lat - min_lat)
        return lon, lat
    
    # Convert each polygon to a GeoJSON feature
    for i, polygon in enumerate(polygons):
        # Extract coordinates
        coords = list(polygon.exterior.coords)
        
        # Transform coordinates to geographic space
        geo_coords = [transform_point(x, y) for x, y in coords]
        
        # Create GeoJSON geometry
        geometry = {
            "type": "Polygon",
            "coordinates": [geo_coords]
        }
        
        # Create GeoJSON feature
        feature = {
            "type": "Feature",
            "id": i + 1,
            "properties": {
                "name": f"Feature {i+1}"
            },
            "geometry": geometry
        }
        
        geojson["features"].append(feature)
    
    return geojson

def process_image_to_geojson(image_path):
    """
    Complete pipeline to convert an image to a simplified GeoJSON.
    
    Args:
        image_path (str): Path to the processed image
        
    Returns:
        dict: GeoJSON object
    """
    try:
        # Open image to get dimensions
        img = Image.open(image_path)
        width, height = img.size
        
        # Extract contours from the image
        polygons = extract_contours(image_path)
        logging.info(f"Extracted {len(polygons)} initial polygons")
        
        if not polygons:
            logging.warning("No polygons found in the image")
            return {"type": "FeatureCollection", "features": []}
        
        # Simplify polygons to reduce vertex count
        polygons = simplify_polygons(polygons, tolerance=2.0)
        logging.info(f"After simplification: {len(polygons)} polygons")
        
        # Regularize appropriate polygons
        polygons = regularize_polygons(polygons)
        
        # Merge nearby polygons to reduce count
        polygons = merge_nearby_polygons(polygons)
        logging.info(f"After merging: {len(polygons)} polygons")
        
        # Convert to GeoJSON with proper transformation
        geojson = convert_to_geojson_with_transform(
            polygons, height, width,
            # Use generic bounds as we don't have real georeferencing
            min_lat=40.0, min_lon=-75.0,
            max_lat=42.0, max_lon=-73.0
        )
        
        return geojson
        
    except Exception as e:
        logging.error(f"Error in GeoJSON processing: {str(e)}")
        return {"type": "FeatureCollection", "features": []}