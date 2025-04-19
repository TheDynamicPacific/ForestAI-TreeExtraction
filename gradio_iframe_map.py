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

# Define feature styles
FEATURE_STYLES = {
    'buildings': {"color": "yellow", "fillColor": "yellow", "fillOpacity": 0.4, "weight": 2},
    'trees': {"color": "green", "fillColor": "green", "fillOpacity": 0.4, "weight": 2},
    'water': {"color": "blue", "fillColor": "blue", "fillOpacity": 0.4, "weight": 2},
    'roads': {"color": "red", "fillColor": "red", "fillOpacity": 0.4, "weight": 3}
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

def create_map_html(geojson_path, geotiff_path, feature_type, use_split=True):
    """Create an HTML map with the GeoJSON and GeoTIFF layers."""
    try:
        logger.info(f"Creating map with {geojson_path} and {geotiff_path}")

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
        style = FEATURE_STYLES.get(feature_type, {"color": "yellow", "fillOpacity": 0.4})
        logger.debug(f"Using style: {style}")

        # Add the GeoJSON to the map
        m.add_gdf(gdf, layer_name=f"Extracted {feature_type.capitalize()}", style=style)

        # Generate a unique filename for the HTML
        unique_id = str(uuid.uuid4().hex)

        if use_split:
            try:
                # Try to create a split map
                logger.debug(f"Creating split map with left layer: Satellite Imagery, right layer: Extracted {feature_type.capitalize()}")

                # Create the split map
                split_map = m.split_map(
                    left_layer="Satellite Imagery",
                    right_layer=f"Extracted {feature_type.capitalize()}"
                )

                if split_map is not None:
                    # Split map was created successfully
                    html_path = os.path.join('static', f"split_map_{unique_id}.html")
                    logger.debug(f"Saving split map to: {html_path}")

                    # Save the split map to HTML
                    split_map.save(html_path)
                    logger.info(f"Split map saved to {html_path}")
                    return html_path
            except Exception as e:
                logger.error(f"Error creating split map: {str(e)}")
                logger.error(traceback.format_exc())
                # Fall through to regular map

        # If split map failed or wasn't requested, create a regular map
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
    with gr.Blocks(title="ForestAI - Feature Extraction with Map") as app:
        gr.Markdown("# ForestAI - Feature Extraction with Map")
        gr.Markdown("Upload a GeoTIFF file and select a feature type to extract. The result will be displayed on a map.")

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
                    label="Map Output",
                    value='<div style="text-align:center; padding:20px;">Upload a GeoTIFF file and click "Process GeoTIFF" to see the map</div>',
                    elem_id="map-container"
                )

        process_btn.click(
            fn=upload_and_process,
            inputs=[geotiff_file, feature_type],
            outputs=[map_output, status_output]
        )

        gr.Markdown("""
        ## How to use the map:
        1. Upload a GeoTIFF file
        2. Select the feature type to extract
        3. Click "Process GeoTIFF"
        4. The map will display with the extracted features overlaid on the satellite imagery
        5. If available, a split map will be shown with a slider to compare the layers
        6. You can zoom in/out and pan the map to explore the results
        """)

    return app

if __name__ == "__main__":
    logger.info("Starting ForestAI Gradio application")
    app = create_interface()
    app.launch(share=False)
