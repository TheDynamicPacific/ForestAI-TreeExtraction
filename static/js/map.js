/**
 * Map initialization and GeoJSON visualization
 * This file handles the map creation and displaying GeoJSON data on it
 */

// Store the map object globally
let map = null;

// Initialize the map with default settings
function initMap() {
    // If map already exists, remove it and create a new one
    if (map !== null) {
        map.remove();
    }

    // Create a new map centered on a default location
    map = L.map('map').setView([40.7, -74.0], 10);

    // Add the base tile layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    // Add a scale control
    L.control.scale().addTo(map);

    return map;
}

// Display GeoJSON data on the map
function displayGeoJSON(geojsonData) {
    if (!map) {
        initMap();
    }

    // Clear any existing GeoJSON layers
    map.eachLayer(function(layer) {
        if (layer instanceof L.GeoJSON) {
            map.removeLayer(layer);
        }
    });

    // Add the GeoJSON data to the map with styling
    const geojsonLayer = L.geoJSON(geojsonData, {
        style: function(feature) {
            // Style polygons
            return {
                fillColor: getRandomColor(),
                weight: 2,
                opacity: 1,
                color: '#666',
                fillOpacity: 0.7
            };
        },
        pointToLayer: function(feature, latlng) {
            // Style points
            return L.circleMarker(latlng, {
                radius: 8,
                fillColor: getRandomColor(),
                color: "#000",
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            });
        },
        onEachFeature: function(feature, layer) {
            // Add popups to show feature properties
            if (feature.properties) {
                let popupContent = '<div class="feature-popup">';
                
                popupContent += '<h5>Feature Properties</h5>';
                
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
