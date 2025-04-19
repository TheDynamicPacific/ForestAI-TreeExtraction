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

# Custom HTML template for split map with Google Satellite imagery
SPLIT_MAP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Split Map Comparison</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            height: 100%;
            width: 100%;
        }}
        .map-container {{
            position: relative;
            height: 600px;
            width: 100%;
            overflow: hidden;
        }}
        .map {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }}
        .divider {{
            position: absolute;
            top: 0;
            bottom: 0;
            left: 50%;
            width: 4px;
            background-color: #fff;
            cursor: ew-resize;
            z-index: 1000;
        }}
        .handle {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: #fff;
            border: 2px solid #333;
            cursor: ew-resize;
            z-index: 1001;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .handle::before,
        .handle::after {{
            content: "";
            position: absolute;
            width: 2px;
            height: 20px;
            background-color: #333;
        }}
        .handle::before {{
            transform: translateX(-5px);
        }}
        .handle::after {{
            transform: translateX(5px);
        }}
        .map-label {{
            position: absolute;
            bottom: 10px;
            padding: 5px 10px;
            background-color: rgba(255, 255, 255, 0.8);
            border-radius: 4px;
            font-weight: bold;
            z-index: 1000;
        }}
        .left-label {{
            left: 10px;
        }}
        .right-label {{
            right: 10px;
        }}
        .clip {{
            position: absolute;
            top: 0;
            bottom: 0;
            width: 50%;
            overflow: hidden;
        }}
        .clip-left {{
            left: 0;
        }}
        .clip-right {{
            right: 0;
        }}
    </style>
</head>
<body>
    <div class="map-container">
        <!-- Base map (visible on both sides) -->
        <div id="base-map" class="map"></div>
        
        <!-- Left side (Google Satellite only) -->
        <div class="clip clip-left">
            <div id="left-map" class="map"></div>
        </div>
        
        <!-- Right side (Features only) -->
        <div class="clip clip-right">
            <div id="right-map" class="map"></div>
        </div>
        
        <!-- Divider -->
        <div class="divider">
            <div class="handle"></div>
        </div>
        
        <!-- Labels -->
        <div class="map-label left-label">Satellite Imagery</div>
        <div class="map-label right-label">Extracted {feature_type}</div>
    </div>

    <script>
        // Initialize maps
        var baseMap = L.map('base-map', {{
            center: [{center_lat}, {center_lng}],
            zoom: {zoom_level},
            zoomControl: false,
            attributionControl: false
        }});
        
        var leftMap = L.map('left-map', {{
            center: [{center_lat}, {center_lng}],
            zoom: {zoom_level},
            zoomControl: false,
            attributionControl: false
        }});
        
        var rightMap = L.map('right-map', {{
            center: [{center_lat}, {center_lng}],
            zoom: {zoom_level},
            zoomControl: true,
            attributionControl: true
        }});
        
        // Add Google Satellite layer to base map and left map
        var googleSat = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20,
            attribution: '&copy; Google'
        }});
        
        googleSat.addTo(baseMap);
        googleSat.addTo(leftMap);
        
        // Add OpenStreetMap as base layer for right map
        var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }});
        
        osm.addTo(rightMap);
        
        // Add GeoJSON to right map only
        var geojsonData = {geojson_data};
        var featureStyle = {feature_style};
        
        var geojsonLayer = L.geoJSON(geojsonData, {{
            style: featureStyle,
            onEachFeature: function(feature, layer) {{
                if (feature.properties && feature.properties.name) {{
                    layer.bindPopup(feature.properties.name);
                }}
            }}
        }}).addTo(rightMap);
        
        // Set bounds
        var bounds = L.latLngBounds(
            [{south}, {west}],
            [{north}, {east}]
        );
        
        baseMap.fitBounds(bounds);
        leftMap.fitBounds(bounds);
        rightMap.fitBounds(bounds);
        
        // Sync maps
        baseMap.sync(leftMap);
        baseMap.sync(rightMap);
        leftMap.sync(baseMap);
        leftMap.sync(rightMap);
        rightMap.sync(baseMap);
        rightMap.sync(leftMap);
        
        // Handle divider dragging
        var isDragging = false;
        var container = document.querySelector('.map-container');
        var divider = document.querySelector('.divider');
        var clipLeft = document.querySelector('.clip-left');
        var clipRight = document.querySelector('.clip-right');
        
        divider.addEventListener('mousedown', function() {{
            isDragging = true;
        }});
        
        document.addEventListener('mousemove', function(e) {{
            if (!isDragging) return;
            
            var containerRect = container.getBoundingClientRect();
            var x = e.clientX - containerRect.left;
            var percent = (x / containerRect.width) * 100;
            
            // Constrain to 10-90%
            percent = Math.max(10, Math.min(90, percent));
            
            divider.style.left = percent + '%';
            clipLeft.style.width = percent + '%';
            clipRight.style.width = (100 - percent) + '%';
            
            // Trigger resize on maps to update their size
            leftMap.invalidateSize();
            rightMap.invalidateSize();
            baseMap.invalidateSize();
        }});
        
        document.addEventListener('mouseup', function() {{
            isDragging = false;
        }});
        
        // Add Leaflet.Sync
        L.Map.include({{
            sync: function(map) {{
                this.on('move', function() {{
                    map.setView(this.getCenter(), this.getZoom(), {{
                        animate: false,
                        reset: false
                    }});
                }}, this);
                return this;
            }}
        }});
    </script>
</body>
</html>
"""

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

def create_google_split_map(geojson_path, geotiff_path, feature_type):
    """Create a split map with Google Satellite imagery and extracted features."""
    try:
        logger.info(f"Creating Google split map with {geojson_path} and {geotiff_path}")
        
        # Get bounds from GeoTIFF
        bounds = get_bounds_from_geotiff(geotiff_path)
        if not bounds:
            logger.warning("No bounds found, using default bounds")
            bounds = (-51.2565, -22.1777, -51.2512, -22.175)
        
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
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        
        # Get the style for the feature type
        style = FEATURE_STYLES.get(feature_type, {"color": "yellow", "fillOpacity": 0.4})
        
        # Generate a unique filename for the HTML
        unique_id = str(uuid.uuid4().hex)
        html_path = os.path.join('static', f"google_split_{unique_id}.html")
        
        # Create the HTML content
        html_content = SPLIT_MAP_TEMPLATE.format(
            feature_type=feature_type.capitalize(),
            center_lat=center_lat,
            center_lng=center_lng,
            zoom_level=zoom_level,
            geojson_data=json.dumps(geojson_data),
            feature_style=json.dumps(style),
            south=south,
            west=west,
            north=north,
            east=east
        )
        
        # Save the HTML to a file
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Google split map saved to {html_path}")
        
        return html_path
    except Exception as e:
        logger.error(f"Error creating Google split map: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def upload_and_process(geotiff_file, feature_type):
    """Upload and process a GeoTIFF file."""
    if geotiff_file is None:
        logger.warning("No file uploaded")
        return None, "Please upload a GeoTIFF file"
    
    try:
        # Log file information
        logger.info(f"Received file: {geotiff_file}")
        
        # Create a temporary file with a proper extension
        os.makedirs('uploads', exist_ok=True)
        unique_id = str(uuid.uuid4().hex)
        
        # Handle different types of file objects that Gradio might return
        if hasattr(geotiff_file, 'name'):
            # It's a file-like object
            filename = os.path.basename(geotiff_file.name)
            logger.debug(f"Original filename from file object: {filename}")
        else:
            # It's a path string
            filename = os.path.basename(geotiff_file)
            logger.debug(f"Original filename from path: {filename}")
        
        # Create a clean path for the uploaded file
        geotiff_path = os.path.join('uploads', f"{unique_id}_{filename}")
        logger.debug(f"Saving file to: {geotiff_path}")
        
        # Copy the file to our uploads directory
        if hasattr(geotiff_file, 'read'):
            # It's a file-like object
            file_content = geotiff_file.read()
            logger.debug(f"Read {len(file_content)} bytes from uploaded file")
            with open(geotiff_path, "wb") as f:
                f.write(file_content)
        else:
            # It's a path string
            shutil.copy(geotiff_file, geotiff_path)
            logger.debug(f"Copied file from {geotiff_file} to {geotiff_path}")
        
        logger.info(f"File saved to {geotiff_path}")
        
        # Process the GeoTIFF
        logger.info(f"Processing GeoTIFF for {feature_type} extraction")
        geojson_path, error = process_geotiff(geotiff_path, feature_type)
        
        if error:
            logger.error(f"Error during processing: {error}")
            return None, error
        
        # Create a Google split map
        logger.info(f"Creating Google split map with {geojson_path} and {geotiff_path}")
        html_path = create_google_split_map(geojson_path, geotiff_path, feature_type)
        
        if html_path:
            logger.info(f"Google split map created at {html_path}")
            
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
            logger.error("Failed to create Google split map")
            return None, "Failed to create Google split map"
    except Exception as e:
        logger.error(f"Error in upload_and_process: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error: {str(e)}"

def create_interface():
    """Create the Gradio interface."""
    with gr.Blocks(title="ForestAI - Feature Extraction with Split Map") as app:
        gr.Markdown("# ForestAI - Feature Extraction with Split Map")
        gr.Markdown("Upload a GeoTIFF file and select a feature type to extract. The result will be displayed as a split map.")
        
        with gr.Row():
            with gr.Column(scale=1):
                geotiff_file = gr.File(label="Upload GeoTIFF File")
                feature_type = gr.Dropdown(
                    choices=["buildings", "trees", "water", "roads"],
                    label="Feature Type",
                    value="buildings"
                )
                process_btn = gr.Button("Process GeoTIFF", variant="primary")
                status_output = gr.Textbox(label="Status", interactive=False)
            
            with gr.Column(scale=2):
                # Use an HTML component to display the map
                map_output = gr.HTML(
                    label="Split Map",
                    value='<div style="text-align:center; padding:20px;">Upload a GeoTIFF file and click "Process GeoTIFF" to see the split map</div>',
                    elem_id="map-container"
                )
        
        process_btn.click(
            fn=upload_and_process,
            inputs=[geotiff_file, feature_type],
            outputs=[map_output, status_output]
        )
        
        gr.Markdown("""
        ## How to use the split map:
        1. Upload a GeoTIFF file
        2. Select the feature type to extract
        3. Click "Process GeoTIFF"
        4. Use the slider in the middle of the map to compare:
           - Left side: Google Satellite imagery
           - Right side: Extracted features
        5. You can zoom in/out and pan the map to explore the results
        """)
    
    return app

if __name__ == "__main__":
    logger.info("Starting ForestAI Gradio application")
    app = create_interface()
    app.launch(share=False)
