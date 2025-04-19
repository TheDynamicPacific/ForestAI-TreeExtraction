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

# Custom HTML template for swipe map with Google Satellite imagery
SWIPE_MAP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Swipe Map Comparison</title>
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
        #map {{
            height: 600px;
            width: 100%;
            position: relative;
        }}
        .swipe-control {{
            position: absolute;
            top: 0;
            bottom: 0;
            left: 50%;
            width: 4px;
            background-color: #fff;
            cursor: ew-resize;
            z-index: 1000;
        }}
        .swipe-handle {{
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
        .swipe-handle::before,
        .swipe-handle::after {{
            content: "";
            position: absolute;
            width: 2px;
            height: 20px;
            background-color: #333;
        }}
        .swipe-handle::before {{
            transform: translateX(-5px);
        }}
        .swipe-handle::after {{
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
        .leaflet-sbs-divider {{
            position: absolute;
            top: 0;
            bottom: 0;
            left: 50%;
            margin-left: -2px;
            width: 4px;
            background-color: #fff;
            pointer-events: none;
            z-index: 999;
        }}
        /* Ensure map containers remain visible */
        .leaflet-container {{
            background: #f8f8f8 !important;
        }}
        /* Make sure panes remain visible */
        .leaflet-tile-pane,
        .leaflet-overlay-pane {{
            visibility: visible !important;
            opacity: 1 !important;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="map-label left-label">Satellite Imagery</div>
    <div class="map-label right-label">Extracted {feature_type}</div>

    <script>
        // Debug function to help troubleshoot issues
        function debug(message) {{
            console.log("DEBUG: " + message);
        }}

        debug("Initializing map");

        // Initialize the map
        var map = L.map('map').setView([{center_lat}, {center_lng}], {zoom_level});

        // Create a reference object to track map state
        var mapState = {{
            initialized: false,
            layersLoaded: false,
            satelliteLoaded: false,
            featuresLoaded: false
        }};

        // Add Google Satellite layer (this will be shown on the left side)
        debug("Adding satellite layer");
        var satelliteLayer = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20,
            attribution: '&copy; Google'
        }});

        // Listen for when the satellite layer loads
        satelliteLayer.on('load', function() {{
            debug("Satellite layer loaded");
            mapState.satelliteLoaded = true;
            checkAllLayersLoaded();
        }});

        // Add the satellite layer to the map
        satelliteLayer.addTo(map);

        // Add GeoJSON layer (this will be shown on the right side)
        debug("Adding feature layer");
        var geojsonData = {geojson_data};
        var featureStyle = {feature_style};

        var featureLayer = L.geoJSON(geojsonData, {{
            style: featureStyle,
            onEachFeature: function(feature, layer) {{
                if (feature.properties && feature.properties.name) {{
                    layer.bindPopup(feature.properties.name);
                }}
            }}
        }});

        // Mark features as loaded (no load event for GeoJSON)
        mapState.featuresLoaded = true;

        // Add the feature layer to the map
        featureLayer.addTo(map);

        // Set bounds
        var bounds = L.latLngBounds(
            [{south}, {west}],
            [{north}, {east}]
        );

        debug("Setting map bounds");
        map.fitBounds(bounds);

        // Create swipe control
        var swipeControl = document.createElement('div');
        swipeControl.className = 'swipe-control';
        var swipeHandle = document.createElement('div');
        swipeHandle.className = 'swipe-handle';
        swipeControl.appendChild(swipeHandle);
        document.getElementById('map').appendChild(swipeControl);

        // Create clip paths for layers
        var clipDivider = document.createElement('div');
        clipDivider.className = 'leaflet-sbs-divider';
        document.getElementById('map').appendChild(clipDivider);

        // Swipe functionality
        var isDragging = false;
        var mapContainer = document.getElementById('map');

        // Check if all layers are loaded
        function checkAllLayersLoaded() {{
            if (mapState.satelliteLoaded && mapState.featuresLoaded && !mapState.layersLoaded) {{
                debug("All layers loaded, initializing swipe");
                mapState.layersLoaded = true;
                initializeSwipe();
            }}
        }}

        // Initialize swipe only after map and layers are ready
        function initializeSwipe() {{
            debug("Initializing swipe control");
            // Set initial position
            swipeControl.style.left = '50%';

            // Initial update
            try {{
                updateClip();
                debug("Initial clip applied");
            }} catch (e) {{
                console.error("Error applying initial clip:", e);
            }}

            mapState.initialized = true;
        }}

        function updateClip() {{
            try {{
                var mapWidth = mapContainer.offsetWidth;
                var swipePosition = (parseFloat(swipeControl.style.left) / mapWidth) * 100;

                debug("Updating clip at position: " + swipePosition + "%");

                // Define clip paths for left and right sides
                var leftClip = 'polygon(0 0, ' + swipePosition + '% 0, ' + swipePosition + '% 100%, 0 100%)';
                var rightClip = 'polygon(' + swipePosition + '% 0, 100% 0, 100% 100%, ' + swipePosition + '% 100%)';

                // Apply clip paths more carefully

                // SATELLITE LAYER (LEFT SIDE)
                debug("Applying left clip to tile pane");
                var mapPanes = document.getElementsByClassName('leaflet-tile-pane');
                if (mapPanes && mapPanes.length > 0) {{
                    var tilePaneElement = mapPanes[0];

                    // Instead of clipping individual tile containers, clip the whole pane
                    tilePaneElement.style.clipPath = leftClip;
                    tilePaneElement.style.webkitClipPath = leftClip; // For Safari compatibility
                }}

                // FEATURE LAYER (RIGHT SIDE)
                debug("Applying right clip to overlay pane");
                var overlayPanes = document.getElementsByClassName('leaflet-overlay-pane');
                if (overlayPanes && overlayPanes.length > 0) {{
                    var overlayPaneElement = overlayPanes[0];
                    overlayPaneElement.style.clipPath = rightClip;
                    overlayPaneElement.style.webkitClipPath = rightClip; // For Safari compatibility
                }}

                // Update divider position
                clipDivider.style.left = swipePosition + '%';

                debug("Clip updated successfully");
            }} catch (e) {{
                console.error("Error in updateClip:", e);
            }}
        }}

        // Event listeners for dragging
        swipeControl.addEventListener('mousedown', function(e) {{
            isDragging = true;
            e.preventDefault();
        }});

        document.addEventListener('mousemove', function(e) {{
            if (!isDragging) return;

            try {{
                var mapRect = mapContainer.getBoundingClientRect();
                var x = e.clientX - mapRect.left;
                var mapWidth = mapContainer.offsetWidth;

                // Constrain to map bounds
                x = Math.max(0, Math.min(x, mapWidth));

                // Update swipe control position
                swipeControl.style.left = x + 'px';

                // Update clip paths
                updateClip();
            }} catch (e) {{
                console.error("Error in mousemove:", e);
            }}
        }});

        document.addEventListener('mouseup', function() {{
            isDragging = false;
        }});

        // Handle touch events for mobile
        swipeControl.addEventListener('touchstart', function(e) {{
            isDragging = true;
            e.preventDefault();
        }});

        document.addEventListener('touchmove', function(e) {{
            if (!isDragging) return;

            try {{
                var touch = e.touches[0];
                var mapRect = mapContainer.getBoundingClientRect();
                var x = touch.clientX - mapRect.left;
                var mapWidth = mapContainer.offsetWidth;

                // Constrain to map bounds
                x = Math.max(0, Math.min(x, mapWidth));

                // Update swipe control position
                swipeControl.style.left = x + 'px';

                // Update clip paths
                updateClip();
            }} catch (e) {{
                console.error("Error in touchmove:", e);
            }}
        }});

        document.addEventListener('touchend', function() {{
            isDragging = false;
        }});

        // Handle window resize
        window.addEventListener('resize', function() {{
            try {{
                // Convert percentage to pixels for swipe control
                var mapWidth = mapContainer.offsetWidth;
                var swipePosition = (parseFloat(swipeControl.style.left) / mapWidth) * 100;
                swipeControl.style.left = (swipePosition * mapWidth / 100) + 'px';

                // Update clip paths
                updateClip();
            }} catch (e) {{
                console.error("Error in resize:", e);
            }}
        }});

        // Ensure map is fully initialized before setting up swipe
        map.whenReady(function() {{
            debug("Map is ready");

            // Initialize swipe if not already done
            setTimeout(function() {{
                if (!mapState.initialized) {{
                    debug("Forcing swipe initialization after timeout");
                    mapState.layersLoaded = true;
                    initializeSwipe();
                }}

                // Additional safety check after a longer delay
                setTimeout(function() {{
                    debug("Final check and refresh");
                    try {{
                        updateClip();
                    }} catch (e) {{
                        console.error("Error in final refresh:", e);
                    }}
                }}, 3000);
            }}, 1000);
        }});

        // Safety mechanism: if layers take too long to load, initialize anyway
        setTimeout(function() {{
            if (!mapState.initialized) {{
                debug("Forcing initialization after extended timeout");
                mapState.satelliteLoaded = true;
                mapState.featuresLoaded = true;
                mapState.layersLoaded = true;
                initializeSwipe();
            }}
        }}, 5000);
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

def create_swipe_map(geojson_path, geotiff_path, feature_type):
    """Create a swipe map with Google Satellite imagery and extracted features."""
    try:
        logger.info(f"Creating swipe map with {geojson_path} and {geotiff_path}")

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
        html_path = os.path.join('static', f"swipe_map_{unique_id}.html")

        # Create the HTML content
        html_content = SWIPE_MAP_TEMPLATE.format(
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

        logger.info(f"Swipe map saved to {html_path}")

        return html_path
    except Exception as e:
        logger.error(f"Error creating swipe map: {str(e)}")
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

        # Create a swipe map
        logger.info(f"Creating swipe map with {geojson_path} and {geotiff_path}")
        html_path = create_swipe_map(geojson_path, geotiff_path, feature_type)

        if html_path:
            logger.info(f"Swipe map created at {html_path}")

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
            logger.error("Failed to create swipe map")
            return None, "Failed to create swipe map"
    except Exception as e:
        logger.error(f"Error in upload_and_process: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error: {str(e)}"

def create_interface():
    """Create the Gradio interface."""
    # Configure Gradio to reduce console errors
    gr.close_all()  # Close any existing Gradio instances

    # Create the interface with custom CSS to handle missing fonts
    with gr.Blocks(
        title="ForestAI - Feature Extraction with Swipe Map",
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
        gr.Markdown("# ForestAI - Feature Extraction with Swipe Map")
        gr.Markdown("Upload a GeoTIFF file and select a feature type to extract. The result will be displayed as a swipe map.")

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
                    label="Swipe Map",
                    value='<div style="text-align:center; padding:20px;">Upload a GeoTIFF file and click "Process GeoTIFF" to see the swipe map</div>',
                    elem_id="map-container"
                )

        # Add error handling to the process button
        def safe_process(geotiff_file, feature_type):
            try:
                if geotiff_file is None:
                    return None, "Please upload a GeoTIFF file"
                return upload_and_process(geotiff_file, feature_type)
            except Exception as e:
                logger.error(f"Error in safe_process: {str(e)}")
                logger.error(traceback.format_exc())
                return None, f"Error: {str(e)}"

        process_btn.click(
            fn=safe_process,
            inputs=[geotiff_file, feature_type],
            outputs=[map_output, status_output]
        )

        gr.Markdown("""
        ## How to use the swipe map:
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
