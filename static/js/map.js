/**
 * Map initialization and GeoJSON visualization
 * This file handles the map creation and displaying GeoJSON data on it
 */

// Store the map object globally
let map = null;
let currentFeatureType = 'buildings';

// Initialize the map with default settings
function initMap(initialCoords) {
    // If map already exists, remove it and create a new one
    if (map !== null) {
        map.remove();
    }

    // Default center coordinates (will be overridden by GeoJSON data)
    let center = [0, 0];
    let zoom = 2;

    // If coordinates are provided, use them
    if (initialCoords && initialCoords.lat !== undefined && initialCoords.lng !== undefined) {
        center = [initialCoords.lat, initialCoords.lng];
        zoom = initialCoords.zoom || 13;
    }

    // Initialize the map with the center coordinates
    map = L.map('map').setView(center, zoom);

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
    // Log the GeoJSON data for debugging
    console.log('GeoJSON data received:', geojsonData);

    if (geojsonData && geojsonData.features && geojsonData.features.length > 0) {
        console.log('First feature:', geojsonData.features[0]);
        if (geojsonData.features[0].geometry && geojsonData.features[0].geometry.coordinates) {
            console.log('First feature coordinates:',
                geojsonData.features[0].geometry.type === 'Polygon' ?
                geojsonData.features[0].geometry.coordinates[0][0] :
                geojsonData.features[0].geometry.coordinates[0][0][0]);
        }
    }

    // Calculate center coordinates from GeoJSON data
    let initialCoords = calculateCenterFromGeoJSON(geojsonData);
    console.log('Calculated center coordinates:', initialCoords);

    if (!map) {
        initMap(initialCoords);
    }

    // Switch to satellite view for better context when viewing features
    if (geojsonData && geojsonData.features && geojsonData.features.length > 0) {
        // Switch to satellite view for better visualization
        try {
            document.querySelectorAll('.leaflet-control-layers-base input')[1].click();
        } catch (e) {
            console.warn('Could not switch to satellite view:', e);
        }
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
        const bounds = geojsonLayer.getBounds();
        console.log('GeoJSON bounds:', bounds);
        map.fitBounds(bounds);
    } else {
        console.warn('GeoJSON bounds not valid');
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

// Calculate center coordinates from GeoJSON data
function calculateCenterFromGeoJSON(geojsonData) {
    if (!geojsonData || !geojsonData.features || geojsonData.features.length === 0) {
        return { lat: 0, lng: 0, zoom: 2 }; // Default to world view
    }

    try {
        // Create a temporary GeoJSON layer to calculate bounds
        const tempLayer = L.geoJSON(geojsonData);
        const bounds = tempLayer.getBounds();

        if (bounds.isValid()) {
            const center = bounds.getCenter();
            // Calculate appropriate zoom level based on bounds size
            const zoom = getBoundsZoomLevel(bounds);
            return { lat: center.lat, lng: center.lng, zoom: zoom };
        }
    } catch (e) {
        console.warn('Error calculating center from GeoJSON:', e);
    }

    // If we can't calculate from features, try to get center from the first feature
    try {
        const firstFeature = geojsonData.features[0];
        if (firstFeature.geometry && firstFeature.geometry.coordinates) {
            let coords;

            // Handle different geometry types
            if (firstFeature.geometry.type === 'Point') {
                coords = firstFeature.geometry.coordinates;
                return { lat: coords[1], lng: coords[0], zoom: 15 };
            } else if (firstFeature.geometry.type === 'Polygon') {
                coords = firstFeature.geometry.coordinates[0][0];
                return { lat: coords[1], lng: coords[0], zoom: 13 };
            } else if (firstFeature.geometry.type === 'MultiPolygon') {
                coords = firstFeature.geometry.coordinates[0][0][0];
                return { lat: coords[1], lng: coords[0], zoom: 13 };
            }
        }
    } catch (e) {
        console.warn('Error getting coordinates from first feature:', e);
    }

    // Default fallback
    return { lat: 0, lng: 0, zoom: 2 };
}

// Calculate appropriate zoom level based on bounds size
function getBoundsZoomLevel(bounds) {
    const WORLD_DIM = { height: 256, width: 256 };
    const ZOOM_MAX = 18;

    const ne = bounds.getNorthEast();
    const sw = bounds.getSouthWest();

    const latFraction = (ne.lat - sw.lat) / 180;
    const lngFraction = (ne.lng - sw.lng) / 360;

    const latZoom = Math.floor(Math.log(1 / latFraction) / Math.LN2);
    const lngZoom = Math.floor(Math.log(1 / lngFraction) / Math.LN2);

    const zoom = Math.min(latZoom, lngZoom, ZOOM_MAX);

    return zoom > 0 ? zoom - 1 : 0; // Zoom out slightly for better context
}

// Initialize map when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // The map will be initialized when results are available
});
