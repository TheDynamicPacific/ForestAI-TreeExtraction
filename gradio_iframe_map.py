import os
import gradio as gr
import leafmap.foliumap as leafmap
import geopandas as gpd
import rasterio
from rasterio.warp import transform_bounds
import json
import tempfile
import shutil
import uuid
import logging
import traceback
from utils.advanced_extraction import extract_features_from_geotiff
import folium
from folium import plugins
import numpy as np
from PIL import Image

# Create directories if they don't exist
os.makedirs('uploads', exist_ok=True)
os.makedirs('processed', exist_ok=True)
os.makedirs('temp', exist_ok=True)
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

# Define feature styles - Only trees with green edge and yellow fill
FEATURE_STYLES = {
    'trees': {"color": "green", "fillColor": "yellow", "fillOpacity": 0.2, "weight": 2}
}

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

def create_split_view_map(geojson_path, geotiff_path, feature_type):
    """Create a split-view map with proper layer control."""
    try:
        logger.info(f"Creating split-view map with {geojson_path} and {geotiff_path}")

        # Get bounds from GeoTIFF
        bounds = get_bounds_from_geotiff(geotiff_path)
        if bounds:
            west, south, east, north = bounds
            center = [(south + north) / 2, (west + east) / 2]
            # Calculate appropriate zoom level based on bounds
            lat_diff = north - south
            lon_diff = east - west
            max_diff = max(lat_diff, lon_diff)
            if max_diff < 0.01:
                zoom = 16
            elif max_diff < 0.05:
                zoom = 14
            elif max_diff < 0.1:
                zoom = 12
            else:
                zoom = 10
        else:
            center = [0, 0]
            zoom = 2

        # Create base map
        m = folium.Map(location=center, zoom_start=zoom)

        # Create two tile layers for the split view
        # Left layer - OpenStreetMap
        left_layer = folium.TileLayer(
            tiles='OpenStreetMap',
            name='OpenStreetMap',
            overlay=False,
            control=False
        )
        
        # Right layer - Satellite imagery
        right_layer = folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=False
        )

        # Add both layers to the map
        left_layer.add_to(m)
        right_layer.add_to(m)

        # Read GeoJSON data
        gdf = gpd.read_file(geojson_path)
        
        # Convert to WGS84 if needed
        if gdf.crs and gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs('EPSG:4326')

        # Get the style for the feature type (green edge, yellow fill)
        style = FEATURE_STYLES.get(feature_type, {"color": "green", "fillColor": "yellow", "fillOpacity": 0.4})

        # Create GeoJSON layer from the data
        geojson_layer = folium.GeoJson(
            gdf.to_json(),
            name=f'Extracted Trees',
            style_function=lambda x: style
        )

        # Add the GeoJSON layer to the map
        geojson_layer.add_to(m)

        # Add side-by-side plugin
        plugins.SideBySideLayers(
            layer_left=left_layer,
            layer_right=right_layer
        ).add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)

        # Fit bounds if available
        if bounds:
            m.fit_bounds([[south, west], [north, east]])

        # Generate a unique filename for the HTML
        unique_id = str(uuid.uuid4().hex)
        html_path = os.path.join('static', f"split_map_{unique_id}.html")
        
        # Save the map
        m.save(html_path)
        logger.info(f"Split-view map saved to {html_path}")

        return html_path

    except Exception as e:
        logger.error(f"Error creating split-view map: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def create_map_html(geojson_path, geotiff_path, feature_type, use_split=True):
    """Create an HTML map with the GeoJSON and GeoTIFF layers."""
    try:
        if use_split:
            # Use the new split-view implementation
            return create_split_view_map(geojson_path, geotiff_path, feature_type)
        
        # Regular map implementation (fallback)
        logger.info(f"Creating regular map with {geojson_path} and {geotiff_path}")

        # Create a leafmap Map
        m = leafmap.Map()

        # Get bounds from GeoTIFF
        bounds = get_bounds_from_geotiff(geotiff_path)
        if bounds:
            west, south, east, north = bounds
            logger.debug(f"Zooming to bounds: {south}, {west}, {north}, {east}")
            m.zoom_to_bounds([south, west, north, east])
        else:
            logger.warning("No bounds found, using default map view")

        # Add the GeoTIFF as a raster layer
        logger.debug(f"Adding raster layer: {geotiff_path}")
        m.add_raster(geotiff_path, layer_name="Satellite Imagery")

        # Add the GeoJSON as a vector layer
        logger.debug(f"Adding vector layer: {geojson_path}")
        gdf = gpd.read_file(geojson_path)

        # Get the style for the feature type
        style = FEATURE_STYLES.get(feature_type, {"color": "green", "fillColor": "yellow", "fillOpacity": 0.4})
        logger.debug(f"Using style: {style}")

        # Add the GeoJSON to the map
        m.add_gdf(gdf, layer_name=f"Extracted Trees", style=style)

        # Generate a unique filename for the HTML
        unique_id = str(uuid.uuid4().hex)
        html_path = os.path.join('static', f"map_{unique_id}.html")
        logger.debug(f"Creating regular map and saving to: {html_path}")

        # Save the map to HTML
        m.to_html(html_path)
        logger.info(f"Regular map saved to {html_path}")

        return html_path
    except Exception as e:
        logger.error(f"Error creating map: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def upload_and_process(geotiff_file):
    """Upload and process a GeoTIFF file."""
    if geotiff_file is None:
        logger.warning("No file uploaded")
        return None, "Please upload a GeoTIFF file"

    try:
        # Fixed to trees only
        feature_type = 'trees'
        
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
        logger.info(f"Processing GeoTIFF for tree extraction")
        geojson_path, error = process_geotiff(geotiff_path, feature_type)

        if error:
            logger.error(f"Error during processing: {error}")
            return None, error

        # Create a map
        logger.info(f"Creating map with {geojson_path} and {geotiff_path}")

        # First try with split map
        html_path = create_map_html(geojson_path, geotiff_path, feature_type, use_split=True)

        if not html_path:
            # If split map failed, try with regular map
            logger.warning("Split map failed, trying regular map")
            html_path = create_map_html(geojson_path, geotiff_path, feature_type, use_split=False)

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
            return iframe_html, f"Successfully extracted trees from {filename}"
        else:
            logger.error("Failed to create map")
            return None, "Failed to create map"
    except Exception as e:
        logger.error(f"Error in upload_and_process: {str(e)}")
        logger.error(traceback.format_exc())
        return None, f"Error: {str(e)}"

def create_interface():
    """Create the Gradio interface."""
    with gr.Blocks(title="ForestAI - Tree Detection") as app:
        gr.Markdown("# ForestAI - Tree Detection from Satellite Imagery")
        gr.Markdown("Upload a GeoTIFF file to detect and map trees. The result will be displayed on a split-view map.")

        with gr.Row():
            with gr.Column(scale=1):
                geotiff_file = gr.File(label="Upload GeoTIFF File")
                process_btn = gr.Button("Detect Trees", variant="primary")
                status_output = gr.Textbox(label="Status", interactive=False)

            with gr.Column(scale=2):
                # Use an HTML component to display the map
                map_output = gr.HTML(
                    label="Map Output",
                    value='<div style="text-align:center; padding:20px;">Upload a GeoTIFF file and click "Detect Trees" to see the map</div>',
                    elem_id="map-container"
                )

        process_btn.click(
            fn=upload_and_process,
            inputs=[geotiff_file],
            outputs=[map_output, status_output]
        )

        gr.Markdown("""
        ## How to use the map:
        1. Upload a GeoTIFF file
        2. Click "Detect Trees"
        3. The map will display with a split-view slider:
           - Left side: OpenStreetMap base layer
           - Right side: Satellite imagery
           - Extracted trees overlay (green edge with yellow fill) on both sides
        4. Drag the vertical slider to compare the layers
        5. Use the layer control to toggle trees on/off
        6. Zoom in/out and pan the map to explore the results
        """)

    return app

if __name__ == "__main__":
    logger.info("Starting ForestAI Tree Detection application")
    app = create_interface()
    app.launch(share=False)