import os
import logging
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory
import json
from werkzeug.utils import secure_filename
from utils.image_processing import process_image
from utils.geospatial import process_image_to_geojson

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
PROCESSED_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processed')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tif', 'tiff'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # Check if a file was selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get feature type, default to buildings if not specified
    feature_type = request.form.get('feature_type', 'buildings')
    logging.info(f"Processing image for feature type: {feature_type}")
    
    # Check if the file is an allowed type
    if file and allowed_file(file.filename):
        # Generate a unique filename to prevent collisions
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Save the uploaded file
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        try:
            # Process the image
            processed_image_path = process_image(file_path, PROCESSED_FOLDER)
            
            # Convert processed image to GeoJSON using improved processing with feature type
            geojson_data = process_image_to_geojson(processed_image_path, feature_type=feature_type)
            
            # Save GeoJSON to file
            geojson_filename = f"{uuid.uuid4().hex}.geojson"
            geojson_path = os.path.join(PROCESSED_FOLDER, geojson_filename)
            
            with open(geojson_path, 'w') as f:
                json.dump(geojson_data, f)
            
            return jsonify({
                'success': True,
                'filename': unique_filename,
                'geojson_filename': geojson_filename,
                'feature_type': feature_type,
                'geojson': geojson_data
            })
            
        except Exception as e:
            logging.error(f"Error processing file: {str(e)}")
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(PROCESSED_FOLDER, filename, as_attachment=True)

# Serve the processed GeoJSON data
@app.route('/geojson/<filename>')
def get_geojson(filename):
    try:
        with open(os.path.join(PROCESSED_FOLDER, filename), 'r') as f:
            geojson_data = json.load(f)
        return jsonify(geojson_data)
    except Exception as e:
        logging.error(f"Error loading GeoJSON: {str(e)}")
        return jsonify({'error': 'Error loading GeoJSON'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
