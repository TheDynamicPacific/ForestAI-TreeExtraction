/**
 * Map initialization and GeoJSON visualization
 * This file handles the map creation and displaying GeoJSON data on it
 */

// Store the map object globally
let map = null;
let currentFeatureType = 'buildings';

// Initialize the map with default settings
function initMap() {
    // If map already exists, remove it and create a new one
    if (map !== null) {
        map.remove();
    }

    // Create a new map centered on a default location (Central US instead of NY)
    map = L.map('map').setView([33.0, -97.0], 8);

    // Define tile layers
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    });
    
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Imagery &copy; Esri',
        maxZoom: 19
    });

    // Add OpenStreetMap layer by default
    osmLayer.addTo(map);
    
    // Add layer control
    const baseLayers = {
        "OpenStreetMap": osmLayer,
        "Satellite": satelliteLayer
    };
    
    L.control.layers(baseLayers, null, {position: 'topright'}).addTo(map);

    // Add a scale control
    L.control.scale().addTo(map);

    return map;
}

// Display GeoJSON data on the map
function displayGeoJSON(geojsonData) {
    if (!map) {
        initMap();
    }

    // Update feature type if available in the data
    if (geojsonData && geojsonData.feature_type) {
        currentFeatureType = geojsonData.feature_type;
    }

    // Clear any existing GeoJSON layers
    map.eachLayer(function(layer) {
        if (layer instanceof L.GeoJSON) {
            map.removeLayer(layer);
        }
    });

    // Add the GeoJSON data to the map with styling based on feature type
    const geojsonLayer = L.geoJSON(geojsonData, {
        style: function(feature) {
            // Different styling based on feature type
            switch(currentFeatureType) {
                case 'buildings':
                    return {
                        fillColor: '#e63946',
                        weight: 1.5,
                        opacity: 1,
                        color: '#999',
                        fillOpacity: 0.7
                    };
                case 'trees':
                    return {
                        fillColor: '#2a9d8f',
                        weight: 1,
                        opacity: 0.9,
                        color: '#006d4f',
                        fillOpacity: 0.7
                    };
                case 'water':
                    return {
                        fillColor: '#0077b6',
                        weight: 1,
                        opacity: 0.8,
                        color: '#023e8a',
                        fillOpacity: 0.6
                    };
                case 'roads':
                    return {
                        fillColor: '#a8dadc',
                        weight: 3,
                        opacity: 1,
                        color: '#457b9d',
                        fillOpacity: 0.8
                    };
                default:
                    return {
                        fillColor: getRandomColor(),
                        weight: 2,
                        opacity: 1,
                        color: '#666',
                        fillOpacity: 0.7
                    };
            }
        },
        pointToLayer: function(feature, latlng) {
            // Style points based on feature type
            let pointStyle = {
                radius: 8,
                color: "#000",
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            };
            
            // Set color based on feature type
            switch(currentFeatureType) {
                case 'buildings':
                    pointStyle.fillColor = '#e63946';
                    break;
                case 'trees':
                    pointStyle.fillColor = '#2a9d8f';
                    break;
                case 'water':
                    pointStyle.fillColor = '#0077b6';
                    break;
                case 'roads':
                    pointStyle.fillColor = '#a8dadc';
                    break;
                default:
                    pointStyle.fillColor = getRandomColor();
            }
            
            return L.circleMarker(latlng, pointStyle);
        },
        onEachFeature: function(feature, layer) {
            // Add popups to show feature properties
            if (feature.properties) {
                let popupContent = '<div class="feature-popup">';
                
                // Set title based on feature type
                let title = 'Feature';
                switch(currentFeatureType) {
                    case 'buildings':
                        title = 'Building';
                        break;
                    case 'trees':
                        title = 'Tree/Vegetation';
                        break;
                    case 'water':
                        title = 'Water Body';
                        break;
                    case 'roads':
                        title = 'Road';
                        break;
                }
                
                popupContent += `<h5>${title} Properties</h5>`;
                
                for (const [key, value] of Object.entries(feature.properties)) {
                    popupContent += `<strong>${key}:</strong> ${value}<br>`;
                }
                
                popupContent += '</div>';
                
                layer.bindPopup(popupContent);
            }
        }
    }).addTo(map);

    // Zoom to fit the GeoJSON data bounds
    if (geojsonLayer.getBounds().isValid()) {
        map.fitBounds(geojsonLayer.getBounds());
    }
}

// Generate a random color for styling different features
function getRandomColor() {
    const colors = [
        '#3388ff', '#33a02c', '#1f78b4', '#ff7f00', '#6a3d9a',
        '#a6cee3', '#b2df8a', '#fb9a99', '#fdbf6f', '#cab2d6'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

// Function to format GeoJSON for display
function formatGeoJSON(geojson) {
    return JSON.stringify(geojson, null, 2);
}

// Initialize map when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // The map will be initialized when results are available
});
