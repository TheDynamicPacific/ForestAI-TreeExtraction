/**
 * File upload and processing functionality
 * This file handles the image upload, processing, and result display
 */

// Store the current GeoJSON filename for download
let currentGeoJsonFilename = null;

// DOM elements
const uploadForm = document.getElementById('uploadForm');
const imageFileInput = document.getElementById('imageFile');
const featureTypeSelect = document.getElementById('featureType');
const processingStatus = document.getElementById('processingStatus');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('resultsSection');
const geojsonDisplay = document.getElementById('geojsonDisplay');
const downloadBtn = document.getElementById('downloadBtn');

// Handle form submission
uploadForm.addEventListener('submit', function(event) {
    event.preventDefault();

    // Get the selected file
    const file = imageFileInput.files[0];

    // Check if a file was selected
    if (!file) {
        showError('Please select an image file to upload');
        return;
    }

    // Check file type
    const validImageTypes = ['image/png', 'image/jpeg', 'image/tiff', 'image/tif'];
    if (!validImageTypes.includes(file.type)) {
        showError('Please select a valid image file (PNG, JPG, or TIFF)');
        return;
    }

    // Show processing status and hide error message
    processingStatus.classList.remove('d-none');
    errorMessage.classList.add('d-none');
    resultsSection.classList.add('d-none');

    // Create FormData object for file upload
    const formData = new FormData();
    formData.append('file', file);
    formData.append('feature_type', featureTypeSelect.value);

    // Upload the file - add error handling for network issues
    fetch('/upload', {
        method: 'POST',
        body: formData,
        // Add timeout for large uploads
        timeout: 120000, // 2 minutes timeout
        // Add credentials for session cookies
        credentials: 'same-origin'
    }).catch(error => {
        console.error('Network error occurred:', error);
        processingStatus.classList.add('d-none');
        if (error.name === 'AbortError') {
            showError('Upload timed out. Try a smaller file or check your connection.');
        } else {
            showError('Network error: ' + error.message);
        }
        throw error;
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || 'Upload failed');
            });
        }
        return response.json();
    })
    .then(data => {
        // Hide processing status
        processingStatus.classList.add('d-none');

        // Store the GeoJSON filename for download
        currentGeoJsonFilename = data.geojson_filename;

        // Display the results
        displayResults(data);
    })
    .catch(error => {
        // Hide processing status and show error
        processingStatus.classList.add('d-none');
        showError(error.message || 'An error occurred during processing');
    });
});

// Display the processing results
function displayResults(data) {
    // Show the results section
    resultsSection.classList.remove('d-none');

    // Calculate center coordinates from GeoJSON data
    let initialCoords = calculateCenterFromGeoJSON(data.geojson);

    // Initialize the map if not already done
    if (!map) {
        initMap(initialCoords);
    }

    // Update the header to show the feature type
    const featureType = data.feature_type || 'buildings';
    const featureTypeName = {
        'buildings': 'Buildings',
        'trees': 'Trees/Vegetation',
        'water': 'Water Bodies',
        'roads': 'Roads'
    }[featureType] || 'Features';

    // Update the card header text
    const resultsHeader = document.querySelector('#resultsSection .card-header h3');
    if (resultsHeader) {
        resultsHeader.innerHTML = `<i class="fas fa-map"></i> ${featureTypeName} Extraction Results`;
    }

    // Add feature type to GeoJSON data for styling
    const geojsonWithType = data.geojson;
    geojsonWithType.feature_type = data.feature_type;

    // Display the GeoJSON on the map
    displayGeoJSON(geojsonWithType);

    // Format and display the GeoJSON in the text area
    geojsonDisplay.textContent = formatGeoJSON(data.geojson);

    // Scroll to the results section
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('d-none');
}

// Handle download button click
downloadBtn.addEventListener('click', function() {
    if (currentGeoJsonFilename) {
        window.location.href = `/download/${currentGeoJsonFilename}`;
    } else {
        showError('No GeoJSON data available for download');
    }
});

// Clear file input when the page loads
document.addEventListener('DOMContentLoaded', function() {
    imageFileInput.value = '';
});
