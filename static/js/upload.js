/**
 * File upload and processing functionality
 * This file handles the image upload, processing, and result display
 */

// Store the current GeoJSON filename for download
let currentGeoJsonFilename = null;

// Store the current GeoJSON data and imagery URL for split map
let currentGeoJsonData = null;
let currentImageryUrl = null;
let isSplitMapActive = false;

// DOM elements
const uploadForm = document.getElementById('uploadForm');
const imageFileInput = document.getElementById('imageFile');
const featureTypeSelect = document.getElementById('featureType');
const processingStatus = document.getElementById('processingStatus');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('resultsSection');
const geojsonDisplay = document.getElementById('geojsonDisplay');
const downloadBtn = document.getElementById('downloadBtn');
const toggleSplitMapBtn = document.getElementById('toggleSplitMapBtn');

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

    // Store the current GeoJSON data for later use
    currentGeoJsonData = data.geojson;

    // Create a better imagery URL (Esri World Imagery)
    currentImageryUrl = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

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

    // Reset split map state
    isSplitMapActive = false;
    toggleSplitMapBtn.textContent = 'Enable Split View';
    toggleSplitMapBtn.innerHTML = '<i class="fas fa-columns"></i> Enable Split View';

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

// Format GeoJSON for display
function formatGeoJSON(geojson) {
    try {
        // If it's already a string, parse it first to ensure it's valid JSON
        if (typeof geojson === 'string') {
            geojson = JSON.parse(geojson);
        }

        // Format with 2 spaces indentation
        return JSON.stringify(geojson, null, 2);
    } catch (error) {
        console.error('Error formatting GeoJSON:', error);
        return 'Error formatting GeoJSON';
    }
}

// Handle download button click
downloadBtn.addEventListener('click', function() {
    if (currentGeoJsonFilename) {
        window.location.href = `/download/${currentGeoJsonFilename}`;
    } else {
        showError('No GeoJSON data available for download');
    }
});

// Handle toggle split map button click
toggleSplitMapBtn.addEventListener('click', function() {
    if (!currentGeoJsonData) {
        showError('No GeoJSON data available for split view');
        return;
    }

    if (isSplitMapActive) {
        // Switch back to normal map view
        displayGeoJSON(currentGeoJsonData);
        toggleSplitMapBtn.innerHTML = '<i class="fas fa-columns"></i> Enable Split View';
        isSplitMapActive = false;
        console.log("Split map disabled");
    } else {
        // Switch to split map view
        const featureType = currentGeoJsonData.feature_type || 'buildings';
        const featureTypeName = {
            'buildings': 'Buildings',
            'trees': 'Trees/Vegetation',
            'water': 'Water Bodies',
            'roads': 'Roads'
        }[featureType] || 'Features';

        // Get the style based on feature type from the split-map.js file
        const featureStyle = getStyleForFeatureType(featureType);

        console.log("Enabling split map view with feature type:", featureType);
        console.log("Using imagery URL:", currentImageryUrl);

        // Create the split map
        createSplitMap(
            currentGeoJsonData,
            currentImageryUrl,
            `Extracted ${featureTypeName}`,
            'Satellite Imagery',
            featureStyle
        );

        toggleSplitMapBtn.innerHTML = '<i class="fas fa-map"></i> Disable Split View';
        isSplitMapActive = true;
        console.log("Split map enabled");
    }
});

// Clear file input when the page loads
document.addEventListener('DOMContentLoaded', function() {
    imageFileInput.value = '';
});
