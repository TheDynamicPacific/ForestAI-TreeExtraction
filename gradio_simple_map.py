import os
import gradio as gr
import geopandas as gpd
import rasterio
from rasterio.warp import transform_bounds
import json
import shutil
import uuid
import logging
import traceback
import PIL.Image
import PIL.ExifTags
import numpy as np
from utils.advanced_extraction import extract_features_from_geotiff

# Create directories if they don't exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('processed', exist_ok=True)
os.makedirs('static', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('forestai_gradio.log')
    ]
)

logger = logging.getLogger('forestai_gradio')

# Define feature styles
FEATURE_STYLES = {
    'buildings': {"color": "yellow", "fillColor": "yellow", "fillOpacity": 0.4, "weight": 2},
    'trees': {"color": "green", "fillColor": "green", "fillOpacity": 0.4, "weight": 2},
    'water': {"color": "blue", "fillColor": "blue", "fillOpacity": 0.4, "weight": 2},
    'roads': {"color": "red", "fillColor": "red", "fillOpacity": 0.4, "weight": 3}
}

def get_coordinates_from_jpg(jpg_path):
    """Extract GPS coordinates from a JPG file's EXIF data."""
    try:
        logger.debug(f"Getting coordinates from JPG: {jpg_path}")
        img = PIL.Image.open(jpg_path)

        # Check if image has EXIF data
        if not hasattr(img, '_getexif') or img._getexif() is None:
            logger.warning(f"No EXIF data found in {jpg_path}")
            return None

        # Get EXIF data
        exif_data = {PIL.ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in PIL.ExifTags.TAGS}

        # Check if GPS info exists
        if 'GPSInfo' not in exif_data:
            logger.warning(f"No GPS data found in {jpg_path}")
            return None

        # Get GPS data
        gps_info = {PIL.ExifTags.GPSTAGS.get(k, k): v for k, v in exif_data['GPSInfo'].items()}

        # Check if we have latitude and longitude
        if 'GPSLatitude' not in gps_info or 'GPSLongitude' not in gps_info:
            logger.warning(f"Incomplete GPS data in {jpg_path}")
            return None

        # Convert GPS coordinates to decimal degrees
        def convert_to_degrees(value):
            d, m, s = value
            return d + (m / 60.0) + (s / 3600.0)

        lat = convert_to_degrees(gps_info['GPSLatitude'])
        lon = convert_to_degrees(gps_info['GPSLongitude'])

        # Apply reference direction
        if gps_info.get('GPSLatitudeRef', 'N') == 'S':
            lat = -lat
        if gps_info.get('GPSLongitudeRef', 'E') == 'W':
            lon = -lon

        logger.debug(f"Extracted coordinates: Lat: {lat}, Lon: {lon}")

        # Create a small bounding box around the point (approximately 100m in each direction)
        # This is a rough approximation - 0.001 degrees is about 111 meters at the equator
        buffer = 0.001
        west = lon - buffer
        east = lon + buffer
        south = lat - buffer
        north = lat + buffer

        logger.debug(f"Created bounds: W:{west}, S:{south}, E:{east}, N:{north}")
        return west, south, east, north
    except Exception as e:
        logger.error(f"Error extracting coordinates from JPG: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def get_bounds_from_geotiff(geotiff_path):
    """Extract the bounds from a GeoTIFF file and convert to WGS84."""
    try:
        logger.debug(f"Getting bounds from GeoTIFF: {geotiff_path}")
        with rasterio.open(geotiff_path) as src:
            # Get the bounds in the original CRS
            bounds = src.bounds
            logger.debug(f"Original bounds: {bounds}")

            # Transform bounds to WGS84 (EPSG:4326)
            if src.crs:
                logger.debug(f"Original CRS: {src.crs}")
                west, south, east, north = transform_bounds(
                    src.crs, 'EPSG:4326',
                    bounds.left, bounds.bottom, bounds.right, bounds.top
                )
                logger.debug(f"Transformed bounds: W:{west}, S:{south}, E:{east}, N:{north}")
                return west, south, east, north
            else:
                logger.warning(f"No CRS found in {geotiff_path}")
                return None
    except Exception as e:
        logger.error(f"Error extracting bounds: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def get_bounds_from_file(file_path):
    """Extract bounds from either a GeoTIFF or JPG file."""
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext in ['.tif', '.tiff']:
        return get_bounds_from_geotiff(file_path)
    elif file_ext in ['.jpg', '.jpeg']:
        return get_coordinates_from_jpg(file_path)
    else:
        logger.warning(f"Unsupported file extension: {file_ext}")
        return None

def process_geotiff(geotiff_path, feature_type):
    """Process a GeoTIFF file to extract features."""
    try:
        # Use the extract_features_from_geotiff function from advanced_extraction.py
        logger.info(f"Extracting {feature_type} from {geotiff_path}")

        # Extract features
        geojson_data = extract_features_from_geotiff(geotiff_path, 'processed', feature_type=feature_type)

        # Save the GeoJSON to a file
        base_name = os.path.splitext(os.path.basename(geotiff_path))[0]
        geojson_path = os.path.join('processed', f"{base_name}_{feature_type}.geojson")

        with open(geojson_path, 'w') as f:
            json.dump(geojson_data, f)

        logger.info(f"Saved GeoJSON to {geojson_path}")

        return geojson_path, None
    except Exception as e:
        logger.error(f"Error processing GeoTIFF: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error processing GeoTIFF: {str(e)}"

def create_simple_map(geojson_path, input_file_path, feature_type):
    """Create a simple HTML map with the GeoJSON and Google Satellite layers."""
    try:
        logger.info(f"Creating simple map with {geojson_path} and {input_file_path}")

        # Verify the GeoJSON file exists
        if not os.path.exists(geojson_path):
            logger.error(f"GeoJSON file not found: {geojson_path}")
            return None, "GeoJSON file not found"

        # Get bounds from input file (GeoTIFF or JPG)
        bounds = get_bounds_from_file(input_file_path)
        if not bounds:
            logger.warning("No bounds found, using default bounds")
            bounds = (-51.2565, -22.1777, -51.2512, -22.175)  # Default bounds

        west, south, east, north = bounds
        center_lat = (north + south) / 2
        center_lng = (east + west) / 2

        # Calculate appropriate zoom level
        # Simple heuristic: smaller area = higher zoom
        lat_diff = abs(north - south)
        lng_diff = abs(east - west)
        if lat_diff < 0.01 and lng_diff < 0.01:
            zoom_level = 18
        elif lat_diff < 0.05 and lng_diff < 0.05:
            zoom_level = 16
        elif lat_diff < 0.1 and lng_diff < 0.1:
            zoom_level = 14
        else:
            zoom_level = 12

        # Read GeoJSON data
        try:
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
        except Exception as e:
            logger.error(f"Error reading GeoJSON: {str(e)}")
            return None, f"Error reading GeoJSON: {str(e)}"

        # Get the style for the feature type
        style = FEATURE_STYLES.get(feature_type, {"color": "yellow", "fillOpacity": 0.4})

        # Generate a unique filename for the HTML
        unique_id = str(uuid.uuid4().hex)
        html_path = os.path.join('static', f"simple_map_{unique_id}.html")

        # Create the HTML content with Leaflet and side-by-side plugin
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ForestAI Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script src="https://unpkg.com/leaflet-side-by-side@2.2.0/leaflet-side-by-side.min.js"></script>
            <style>
                body, html {{
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    width: 100%;
                    font-family: Arial, sans-serif;
                }}
                #map {{
                    height: 600px;
                    width: 100%;
                }}
                .info {{
                    padding: 6px 8px;
                    font: 14px/16px Arial, Helvetica, sans-serif;
                    background: white;
                    background: rgba(255,255,255,0.8);
                    box-shadow: 0 0 15px rgba(0,0,0,0.2);
                    border-radius: 5px;
                }}
                .info h4 {{
                    margin: 0 0 5px;
                    color: #777;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                // Initialize the map
                var map = L.map('map').setView([{center_lat}, {center_lng}], {zoom_level});

                // Add Google Satellite layer (left side)
                var googleSat = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={{x}}&y={{y}}&z={{z}}', {{
                    maxZoom: 20,
                    attribution: '&copy; Google'
                }}).addTo(map);

                // Add OpenStreetMap as base layer for right side
                var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 19,
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }}).addTo(map);

                // Add GeoJSON layer (right side)
                var geojsonData = {json.dumps(geojson_data)};
                var style = {json.dumps(style)};

                var geojsonLayer = L.geoJSON(geojsonData, {{
                    style: style,
                    onEachFeature: function(feature, layer) {{
                        if (feature.properties && feature.properties.name) {{
                            layer.bindPopup(feature.properties.name);
                        }}
                    }}
                }}).addTo(map);

                // Set bounds
                var bounds = L.latLngBounds(
                    [{south}, {west}],
                    [{north}, {east}]
                );

                map.fitBounds(bounds);

                // Initialize split map with leaflet-side-by-side
                var sideBySide = L.control.sideBySide(
                    googleSat,
                    L.layerGroup([osm, geojsonLayer])
                ).addTo(map);

                // Add info box
                var info = L.control({{position: 'topright'}});
                info.onAdd = function (map) {{
                    var div = L.DomUtil.create('div', 'info');
                    div.innerHTML = '<h4>Map Comparison</h4>' +
                        'Left: Satellite Imagery<br>' +
                        'Right: Extracted {feature_type.capitalize()}<br>' +
                        'Drag the divider to compare';
                    return div;
                }};
                info.addTo(map);
            </script>
        </body>
        </html>
        """

        # Save the HTML content to a file
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"Simple map saved to {html_path}")

        return html_path, None
    except Exception as e:
        logger.error(f"Error creating simple map: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error creating map: {str(e)}"

def upload_and_process(input_file, feature_type):
    """Upload and process a GeoTIFF or JPG file."""
    if input_file is None:
        logger.warning("No file uploaded")
        return None, "Please upload a GeoTIFF or JPG file"

    try:
        # Log file information
        logger.info(f"Received file: {input_file}")

        # Create a temporary file with a proper extension
        os.makedirs('uploads', exist_ok=True)
        unique_id = str(uuid.uuid4().hex)

        # Handle different types of file objects that Gradio might return
        if hasattr(input_file, 'name'):
            # It's a file-like object
            filename = os.path.basename(input_file.name)
            logger.debug(f"Original filename from file object: {filename}")
        else:
            # It's a path string
            filename = os.path.basename(input_file)
            logger.debug(f"Original filename from path: {filename}")

        # Check if the file is a supported format by extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in ['.tif', '.tiff', '.jpg', '.jpeg']:
            logger.error(f"Uploaded file is not supported: {filename} (extension: {file_ext})")
            return None, f"Please upload a GeoTIFF (.tif/.tiff) or JPG (.jpg/.jpeg) file. Received: {file_ext}"

        # Create a clean path for the uploaded file
        input_path = os.path.join('uploads', f"{unique_id}_{filename}")
        logger.debug(f"Saving file to: {input_path}")

        # Copy the file to our uploads directory
        try:
            if hasattr(input_file, 'read'):
                # It's a file-like object
                file_content = input_file.read()
                logger.debug(f"Read {len(file_content)} bytes from uploaded file")
                with open(input_path, "wb") as f:
                    f.write(file_content)
            else:
                # It's a path string
                shutil.copy(input_file, input_path)
                logger.debug(f"Copied file from {input_file} to {input_path}")
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            logger.error(traceback.format_exc())
            return None, f"Error saving file: {str(e)}"

        logger.info(f"File saved to {input_path}")

        # Validate the file based on its type
        is_geotiff = file_ext in ['.tif', '.tiff']
        is_jpg = file_ext in ['.jpg', '.jpeg']

        if is_geotiff:
            # Verify the file is a valid GeoTIFF by trying to open it with rasterio
            try:
                with rasterio.open(input_path) as src:
                    if not src.crs:
                        logger.error(f"File is not a valid GeoTIFF (no CRS): {input_path}")
                        return None, "The uploaded file is not a valid GeoTIFF (no coordinate reference system found)"
            except Exception as e:
                logger.error(f"Error validating GeoTIFF: {str(e)}")
                logger.error(traceback.format_exc())
                return None, f"The uploaded file is not a valid GeoTIFF: {str(e)}"
        elif is_jpg:
            # Verify the JPG has GPS coordinates
            coords = get_coordinates_from_jpg(input_path)
            if not coords:
                logger.error(f"JPG file does not contain GPS coordinates: {input_path}")
                return None, "The uploaded JPG file does not contain GPS coordinates"

        # Process the file for feature extraction
        logger.info(f"Processing file for {feature_type} extraction")
        geojson_path, error = process_geotiff(input_path, feature_type)

        if error:
            logger.error(f"Error during processing: {error}")
            return None, error

        # Create a map
        logger.info(f"Creating map with {geojson_path} and {input_path}")
        html_path, error = create_simple_map(geojson_path, input_path, feature_type)

        if error:
            logger.error(f"Error creating map: {error}")
            return None, error

        if html_path:
            logger.info(f"Map created at {html_path}")

            # Read the HTML content
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Create an iframe with the map content directly embedded
            iframe_html = f'''
            <div style="width:100%; height:600px; border:none; overflow:hidden;">
                <iframe srcdoc="{html_content.replace('"', '&quot;')}"
                        width="100%" height="600px" style="border:none;"></iframe>
            </div>
            '''

            # Return the iframe HTML and a success message
            return iframe_html, f"Successfully extracted {feature_type} from {filename}"
        else:
            logger.error("Failed to create map")
            return None, "Failed to create map"
    except Exception as e:
        logger.error(f"Error in upload_and_process: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error: {str(e)}"

def create_interface():
    """Create the Gradio interface."""
    # Close any existing Gradio instances
    gr.close_all()

    with gr.Blocks(
        title="ForestAI - Feature Extraction with Split Map",
        css="""
        @font-face {
            font-family: 'ui-sans-serif';
            src: local('Arial'), local('Helvetica'), local('sans-serif');
        }
        @font-face {
            font-family: 'system-ui';
            src: local('Arial'), local('Helvetica'), local('sans-serif');
        }
        """
    ) as app:
        gr.Markdown("# ForestAI - Feature Extraction with Split Map")
        gr.Markdown("Upload a GeoTIFF or JPG file (with GPS coordinates) and select a feature type to extract. The result will be displayed as a split map.")

        with gr.Row():
            with gr.Column(scale=1):
                input_file = gr.File(label="Upload GeoTIFF or JPG File")
                feature_type = gr.Dropdown(
                    choices=["buildings", "trees", "water", "roads"],
                    label="Feature Type",
                    value="buildings"
                )
                process_btn = gr.Button("Process File", variant="primary")
                status_output = gr.Textbox(label="Status", interactive=False)

            with gr.Column(scale=2):
                # Use an HTML component to display the map
                map_output = gr.HTML(
                    label="Split Map",
                    value='<div style="text-align:center; padding:20px;">Upload a GeoTIFF or JPG file and click "Process File" to see the split map</div>',
                    elem_id="map-container"
                )

        # Add error handling to the process button
        def safe_process(input_file, feature_type):
            try:
                if input_file is None:
                    return None, "Please upload a GeoTIFF or JPG file"
                return upload_and_process(input_file, feature_type)
            except Exception as e:
                logger.error(f"Error in safe_process: {str(e)}")
                logger.error(traceback.format_exc())
                return None, f"Error: {str(e)}"

        process_btn.click(
            fn=safe_process,
            inputs=[input_file, feature_type],
            outputs=[map_output, status_output]
        )

        gr.Markdown("""
        ## How to use the split map:
        1. Upload a GeoTIFF or JPG file (JPG must contain GPS coordinates)
        2. Select the feature type to extract
        3. Click "Process File"
        4. The map will display with a slider to compare:
           - Left side: Satellite imagery
           - Right side: Extracted features
        5. Move the slider to compare the layers
        6. Zoom in/out and pan to explore the results

        ## Supported file types:
        - GeoTIFF (.tif, .tiff): Must contain geospatial information
        - JPG/JPEG (.jpg, .jpeg): Must contain GPS coordinates in EXIF data
        """)

    return app

if __name__ == "__main__":
    logger.info("Starting ForestAI Gradio application")
    app = create_interface()
    app.launch(share=False)
