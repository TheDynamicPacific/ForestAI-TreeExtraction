"""
Advanced feature extraction using geoai-py package.
This module provides integration with the geoai-py package for more accurate
feature extraction from geospatial imagery.
"""

import os
import logging
import geoai
import json
from shapely.geometry import shape

def extract_buildings_from_geotiff(image_path, output_folder, confidence_threshold=0.5, mask_threshold=0.5):
    """
    Extract building footprints from a GeoTIFF image using geoai-py.

    Args:
        image_path (str): Path to the input GeoTIFF image
        output_folder (str): Directory to save output files
        confidence_threshold (float): Confidence threshold for detection (0.0-1.0)
        mask_threshold (float): Mask threshold for segmentation (0.0-1.0)

    Returns:
        str: Path to the generated GeoJSON file
    """
    try:
        logging.info(f"Extracting buildings from {image_path} using geoai-py")

        # Initialize the building footprint extractor
        extractor = geoai.BuildingFootprintExtractor()

        # Generate a unique output path for the GeoJSON
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        geojson_path = os.path.join(output_folder, f"{base_name}_buildings.geojson")

        # Process the raster to extract building footprints
        gdf = extractor.process_raster(
            image_path,
            output_path=geojson_path,
            batch_size=4,
            confidence_threshold=confidence_threshold,
            overlap=0.25,
            nms_iou_threshold=0.5,
            min_object_area=100,
            max_object_area=None,
            mask_threshold=mask_threshold,
            simplify_tolerance=1.0,
        )

        # Regularize the building footprints for more rectangular shapes
        gdf_regularized = extractor.regularize_buildings(
            gdf=gdf,
            min_area=100,
            angle_threshold=15,
            orthogonality_threshold=0.3,
            rectangularity_threshold=0.7,
        )

        # Ensure the GeoDataFrame is in WGS84 (EPSG:4326) for web mapping
        try:
            # Check if the GeoDataFrame has a CRS
            if gdf_regularized.crs is not None and gdf_regularized.crs != 'EPSG:4326':
                logging.info(f"Converting GeoDataFrame from {gdf_regularized.crs} to WGS84 (EPSG:4326)")
                # Reproject to WGS84
                gdf_regularized = gdf_regularized.to_crs('EPSG:4326')
            elif gdf_regularized.crs is None:
                # Try to get CRS from the original image
                import rasterio
                with rasterio.open(image_path) as src:
                    if src.crs is not None:
                        logging.info(f"Setting CRS from image: {src.crs}")
                        gdf_regularized.crs = src.crs
                        # Reproject to WGS84
                        gdf_regularized = gdf_regularized.to_crs('EPSG:4326')
        except Exception as e:
            logging.warning(f"Error reprojecting to WGS84: {str(e)}")

        # Save the regularized buildings to GeoJSON
        regularized_geojson_path = os.path.join(output_folder, f"{base_name}_buildings_regularized.geojson")
        gdf_regularized.to_file(regularized_geojson_path, driver="GeoJSON")

        logging.info(f"Successfully extracted {len(gdf_regularized)} buildings")

        # Return the path to the regularized GeoJSON
        return regularized_geojson_path

    except Exception as e:
        logging.error(f"Error extracting buildings with geoai-py: {str(e)}")
        raise

def extract_trees_from_geotiff(image_path, output_folder, confidence_threshold=0.5, mask_threshold=0.5):
    """
    Extract tree/vegetation cover from a GeoTIFF image.
    This is a placeholder for future implementation.

    Args:
        image_path (str): Path to the input GeoTIFF image
        output_folder (str): Directory to save output files
        confidence_threshold (float): Confidence threshold for detection (0.0-1.0)
        mask_threshold (float): Mask threshold for segmentation (0.0-1.0)

    Returns:
        str: Path to the generated GeoJSON file
    """
    # This would be implemented in the future
    # For now, we'll use our existing segmentation approach
    from utils.geospatial import process_image_to_geojson
    from utils.image_processing import process_image

    processed_image_path = process_image(image_path, output_folder)
    geojson_data = process_image_to_geojson(processed_image_path, feature_type="trees", original_file_path=image_path)

    # Save the GeoJSON to a file
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    geojson_path = os.path.join(output_folder, f"{base_name}_trees.geojson")

    with open(geojson_path, 'w') as f:
        json.dump(geojson_data, f)

    return geojson_path

def geojson_to_app_format(geojson_path):
    """
    Convert a GeoJSON file from geoai-py to the format expected by our application.

    Args:
        geojson_path (str): Path to the GeoJSON file

    Returns:
        dict: GeoJSON data in the format expected by our application
    """
    try:
        # Read the GeoJSON file
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)

        # Log the GeoJSON data for debugging
        logging.info(f"GeoJSON data loaded from {geojson_path}")
        if geojson_data and 'features' in geojson_data and geojson_data['features']:
            first_feature = geojson_data['features'][0]
            if 'geometry' in first_feature and 'coordinates' in first_feature['geometry']:
                try:
                    if first_feature['geometry']['type'] == 'Polygon':
                        coords = first_feature['geometry']['coordinates'][0][0]
                    else:  # MultiPolygon
                        coords = first_feature['geometry']['coordinates'][0][0][0]
                    logging.info(f"First feature coordinates: {coords}")
                except Exception as e:
                    logging.warning(f"Error extracting coordinates from first feature: {str(e)}")

        # Our application expects a specific format, so we'll convert if needed
        if 'features' not in geojson_data:
            # Create a new GeoJSON FeatureCollection
            converted_geojson = {
                "type": "FeatureCollection",
                "features": []
            }

            # Add each feature to the collection
            for i, feature in enumerate(geojson_data):
                converted_geojson["features"].append({
                    "type": "Feature",
                    "geometry": feature["geometry"],
                    "properties": feature.get("properties", {"id": i})
                })

            logging.info(f"Converted GeoJSON to FeatureCollection with {len(converted_geojson['features'])} features")
            return converted_geojson

        # If it's already in the right format, return as is
        logging.info(f"GeoJSON already in FeatureCollection format with {len(geojson_data['features'])} features")
        return geojson_data

    except Exception as e:
        logging.error(f"Error converting GeoJSON format: {str(e)}")
        # Return an empty GeoJSON if there's an error
        return {"type": "FeatureCollection", "features": []}

def extract_features_from_geotiff(image_path, output_folder, feature_type="buildings"):
    """
    Extract features from a GeoTIFF image based on the feature type.

    Args:
        image_path (str): Path to the input GeoTIFF image
        output_folder (str): Directory to save output files
        feature_type (str): Type of features to extract ("buildings", "trees", "water", "roads")

    Returns:
        dict: GeoJSON data in the format expected by our application
    """
    try:
        if feature_type.lower() == "buildings":
            # Use the advanced building extraction
            geojson_path = extract_buildings_from_geotiff(image_path, output_folder)
        elif feature_type.lower() == "trees" or feature_type.lower() == "vegetation":
            # Use the tree extraction (placeholder for now)
            geojson_path = extract_trees_from_geotiff(image_path, output_folder)
        else:
            # For other feature types, use our existing approach
            from utils.geospatial import process_image_to_geojson
            from utils.image_processing import process_image

            processed_image_path = process_image(image_path, output_folder)
            geojson_data = process_image_to_geojson(processed_image_path, feature_type=feature_type, original_file_path=image_path)

            # Save the GeoJSON to a file
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            geojson_path = os.path.join(output_folder, f"{base_name}_{feature_type}.geojson")

            with open(geojson_path, 'w') as f:
                json.dump(geojson_data, f)

            # Add feature type to the GeoJSON data
            geojson_data['feature_type'] = feature_type

            # Return the data directly since it's already in our format
            return geojson_data

        # Convert the GeoJSON to our application format
        result = geojson_to_app_format(geojson_path)

        # Add feature type to the GeoJSON data
        result['feature_type'] = feature_type

        return result

    except Exception as e:
        logging.error(f"Error extracting features: {str(e)}")
        # Return an empty GeoJSON if there's an error
        return {"type": "FeatureCollection", "features": []}
