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

# Simple HTML template for a map with a comparison plugin
COMPARE_MAP_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Compare Map</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
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
        .legend {{
            text-align: left;
            line-height: 18px;
            color: #555;
        }}
        .legend i {{
            width: 18px;
            height: 18px;
            float: left;
            margin-right: 8px;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <script>
        // Initialize the map
        var map = L.map('map').setView([{center_lat}, {center_lng}], {zoom_level});
        
        // Add Google Satellite layer
        var googleSat = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20,
            attribution: '&copy; Google'
        }}).addTo(map);
        
        // Add OpenStreetMap as base layer
        var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }});
        
        // Add GeoJSON layer
        var geojsonData = {geojson_data};
        var featureStyle = {feature_style};
        
        var geojsonLayer = L.geoJSON(geojsonData, {{
            style: featureStyle,
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
        
        // Create a simple layer control
        var baseMaps = {{
            "Satellite": googleSat,
            "OpenStreetMap": osm
        }};
        
        var overlayMaps = {{
            "Extracted {feature_type}": geojsonLayer
        }};
        
        L.control.layers(baseMaps, overlayMaps, {{collapsed: false}}).addTo(map);
        
        // Add a simple legend
        var legend = L.control({{position: 'bottomright'}});
        
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML = '<h4>Legend</h4>' +
                '<i style="background:{color}"></i> Extracted {feature_type}<br>';
            return div;
        }};
        
        legend.addTo(map);
        
        // Add a simple info box
        var info = L.control({{position: 'topright'}});
        
        info.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'info');
            div.innerHTML = '<h4>How to use this map</h4>' +
                'Use the layer control in the top right to toggle between layers.<br>' +
                'You can show/hide the extracted features or switch between satellite and map views.';
            return div;
        }};
        
        info.addTo(map);
        
        // Add a scale control
        L.control.scale().addTo(map);
    </script>
</body>
</html>
"""

# HTML template for a side-by-side comparison
SIDE_BY_SIDE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Side by Side Comparison</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            height: 100%;
            width: 100%;
            font-family: Arial, sans-serif;
        }}
        .map-container {{
            display: flex;
            flex-direction: row;
            height: 600px;
            width: 100%;
        }}
        #map-left, #map-right {{
            flex: 1;
            height: 100%;
        }}
        .map-title {{
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 5px 10px;
            border-radius: 5px;
            z-index: 1000;
            font-weight: bold;
        }}
        .left-title {{
            left: 25%;
        }}
        .right-title {{
            left: 75%;
        }}
    </style>
</head>
<body>
    <div class="map-container">
        <div id="map-left"></div>
        <div id="map-right"></div>
        <div class="map-title left-title">Satellite Imagery</div>
        <div class="map-title right-title">Extracted {feature_type}</div>
    </div>
    
    <script>
        // Initialize the left map (satellite only)
        var leftMap = L.map('map-left').setView([{center_lat}, {center_lng}], {zoom_level});
        
        // Add Google Satellite layer to left map
        var googleSat = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={{x}}&y={{y}}&z={{z}}', {{
            maxZoom: 20,
            attribution: '&copy; Google'
        }}).addTo(leftMap);
        
        // Initialize the right map (features)
        var rightMap = L.map('map-right').setView([{center_lat}, {center_lng}], {zoom_level});
        
        // Add OpenStreetMap as base layer for right map
        var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }}).addTo(rightMap);
        
        // Add GeoJSON layer to right map
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
        
        leftMap.fitBounds(bounds);
        rightMap.fitBounds(bounds);
        
        // Sync maps
        leftMap.on('move', function() {{
            rightMap.setView(leftMap.getCenter(), leftMap.getZoom());
        }});
        
        rightMap.on('move', function() {{
            leftMap.setView(rightMap.getCenter(), rightMap.getZoom());
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

def create_comparison_map(geojson_path, geotiff_path, feature_type, map_type="side-by-side"):
    """Create a comparison map with the specified type."""
    try:
        logger.info(f"Creating {map_type} map with {geojson_path} and {geotiff_path}")
        
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
        
        if map_type == "side-by-side":
            html_path = os.path.join('static', f"side_by_side_{unique_id}.html")
            html_content = SIDE_BY_SIDE_TEMPLATE.format(
                feature_type=feature_type.capitalize(),
                center_lat=center_lat,
                center_lng=center_lng,
                zoom_level=zoom_level,
                geojson_data=json.dumps(geojson_data),
                feature_style=json.dumps(style),
                south=south,
                west=west,
                north=north,
                east=east,
                color=style.get("color", "yellow")
            )
        else:  # "compare"
            html_path = os.path.join('static', f"compare_map_{unique_id}.html")
            html_content = COMPARE_MAP_TEMPLATE.format(
                feature_type=feature_type.capitalize(),
                center_lat=center_lat,
                center_lng=center_lng,
                zoom_level=zoom_level,
                geojson_data=json.dumps(geojson_data),
                feature_style=json.dumps(style),
                south=south,
                west=west,
                north=north,
                east=east,
                color=style.get("color", "yellow")
            )
        
        # Save the HTML to a file
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"{map_type.capitalize()} map saved to {html_path}")
        
        return html_path
    except Exception as e:
        logger.error(f"Error creating {map_type} map: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def upload_and_process(geotiff_file, feature_type, map_type):
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
        
        # Create a comparison map
        logger.info(f"Creating {map_type} map with {geojson_path} and {geotiff_path}")
        html_path = create_comparison_map(geojson_path, geotiff_path, feature_type, map_type)
        
        if html_path:
            logger.info(f"{map_type.capitalize()} map created at {html_path}")
            
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
            logger.error(f"Failed to create {map_type} map")
            return None, f"Failed to create {map_type} map"
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
        title="ForestAI - Feature Extraction with Map Comparison",
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
        gr.Markdown("# ForestAI - Feature Extraction with Map Comparison")
        gr.Markdown("Upload a GeoTIFF file and select a feature type to extract. Choose a comparison type to visualize the results.")
        
        with gr.Row():
            with gr.Column(scale=1):
                geotiff_file = gr.File(label="Upload GeoTIFF File")
                feature_type = gr.Dropdown(
                    choices=["buildings", "trees", "water", "roads"],
                    label="Feature Type",
                    value="buildings"
                )
                map_type = gr.Radio(
                    choices=["side-by-side", "compare"],
                    label="Comparison Type",
                    value="side-by-side",
                    info="Side-by-side shows two maps, Compare shows a single map with layer controls"
                )
                process_btn = gr.Button("Process GeoTIFF", variant="primary")
                status_output = gr.Textbox(label="Status", interactive=False)
            
            with gr.Column(scale=2):
                # Use an HTML component to display the map
                map_output = gr.HTML(
                    label="Map Comparison",
                    value='<div style="text-align:center; padding:20px;">Upload a GeoTIFF file and click "Process GeoTIFF" to see the comparison</div>',
                    elem_id="map-container"
                )
        
        # Add error handling to the process button
        def safe_process(geotiff_file, feature_type, map_type):
            try:
                if geotiff_file is None:
                    return None, "Please upload a GeoTIFF file"
                return upload_and_process(geotiff_file, feature_type, map_type)
            except Exception as e:
                logger.error(f"Error in safe_process: {str(e)}")
                logger.error(traceback.format_exc())
                return None, f"Error: {str(e)}"
        
        process_btn.click(
            fn=safe_process,
            inputs=[geotiff_file, feature_type, map_type],
            outputs=[map_output, status_output]
        )
        
        gr.Markdown("""
        ## How to use the comparison:
        
        ### Side-by-Side Mode
        - Left side: Satellite imagery
        - Right side: Extracted features
        - Both maps are synchronized - zoom or pan on either map to update both
        
        ### Compare Mode
        - Single map with layer controls
        - Use the layer control in the top right to toggle between satellite imagery and extracted features
        - You can show both layers at once or switch between them
        """)
    
    return app

if __name__ == "__main__":
    logger.info("Starting ForestAI Gradio application")
    app = create_interface()
    app.launch(share=False)
