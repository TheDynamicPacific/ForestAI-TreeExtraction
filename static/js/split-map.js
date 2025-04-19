/**
 * Split map functionality for comparing two layers with a swipe control.
 * Inspired by the geoai.create_split_map function.
 */

// Global variables for split map
let splitControl = null;
let layerControl = null;
let leftLayer = null;
let rightLayer = null;
let basemapLayers = {};
let overlayLayers = {};
let splitMapActive = false;

/**
 * Create a split map with GeoJSON on one side and imagery on the other
 *
 * @param {Object} geojsonData - GeoJSON data for building footprints
 * @param {string} imageryUrl - URL for the imagery tile layer
 * @param {string} leftLabel - Label for the left layer
 * @param {string} rightLabel - Label for the right layer
 * @param {Object} geojsonStyle - Style options for the GeoJSON layer
 */
function createSplitMap(geojsonData, imageryUrl, leftLabel, rightLabel, geojsonStyle) {
    console.log("Creating split map with GeoJSON data and imagery URL:", imageryUrl);

    // Clear any existing map
    if (map) {
        map.remove();
    }

    // Initialize the map
    map = L.map('map', {
        center: [0, 0],
        zoom: 2,
        zoomControl: true
    });

    // Create basemap layers
    basemapLayers = {
        'Esri World Imagery': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19,
            attribution: '© Esri'
        }),
        'OpenStreetMap': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }),
        'Google Satellite': L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
            maxZoom: 19,
            attribution: '© Google'
        })
    };

    // Add the default basemap
    rightLayer = basemapLayers['Esri World Imagery'];
    rightLayer.addTo(map);

    // Create the GeoJSON layer with style
    leftLayer = L.geoJSON(geojsonData, {
        style: geojsonStyle || {
            color: 'yellow',
            fillColor: 'yellow',
            fillOpacity: 0.4,
            weight: 2
        }
    }).addTo(map);

    // Create overlay layers
    overlayLayers = {
        [leftLabel || 'Extracted Features']: leftLayer
    };

    // Fit the map to the GeoJSON bounds
    if (leftLayer.getBounds().isValid()) {
        map.fitBounds(leftLayer.getBounds());
    }

    // Create the split control
    console.log("Creating split control with left and right layers");
    splitControl = L.control.sideBySide(leftLayer, rightLayer);
    splitControl.addTo(map);

    // Add layer control
    layerControl = L.control.layers(basemapLayers, overlayLayers, {collapsed: false}).addTo(map);

    // Add labels
    addSplitMapLabels(leftLabel || "Extracted Features", rightLabel || "Satellite Imagery");

    // Add event listeners for layer changes
    map.on('baselayerchange', function(e) {
        console.log("Base layer changed to:", e.name);
        rightLayer = e.layer;
        updateSplitControl();
    });

    // Set split map as active
    splitMapActive = true;

    return map;
}

/**
 * Add labels to the split map
 */
function addSplitMapLabels(leftLabel, rightLabel) {
    // Remove any existing labels
    const existingLabels = document.querySelector('.split-map-labels');
    if (existingLabels) {
        existingLabels.remove();
    }

    // Create a control for the labels
    const labelControl = L.control({position: 'bottomleft'});

    labelControl.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'split-map-labels');
        div.innerHTML = `
            <div class="split-map-label left-label">${leftLabel}</div>
            <div class="split-map-label right-label">${rightLabel}</div>
        `;
        return div;
    };

    labelControl.addTo(map);
}

/**
 * Update the split control when layers change
 */
function updateSplitControl() {
    // Remove existing split control if it exists
    if (splitControl) {
        map.removeControl(splitControl);
    }

    // If we have both left and right layers, create a new split control
    if (leftLayer && rightLayer) {
        console.log("Updating split control with new layers");
        splitControl = L.control.sideBySide(leftLayer, rightLayer);
        splitControl.addTo(map);
    }
}

/**
 * Add CSS styles for the split map
 */
function addSplitMapStyles() {
    // Check if styles already exist
    if (!document.getElementById('split-map-styles')) {
        const styleElement = document.createElement('style');
        styleElement.id = 'split-map-styles';
        styleElement.textContent = `
            .split-map-labels {
                display: flex;
                justify-content: space-between;
                width: 100%;
                position: absolute;
                bottom: 10px;
                left: 0;
                padding: 0 50px;
                pointer-events: none;
                z-index: 1000;
            }
            .split-map-label {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            .left-label {
                margin-right: auto;
            }
            .right-label {
                margin-left: auto;
            }
            /* Style for the side-by-side slider */
            .leaflet-sbs-divider {
                width: 5px !important;
                background-color: white !important;
                box-shadow: 0 0 5px rgba(0, 0, 0, 0.5) !important;
            }
            .leaflet-sbs-range {
                -webkit-appearance: none;
                appearance: none;
                height: 100%;
                width: 100%;
                position: absolute;
                top: 0;
                z-index: 999;
                background: transparent;
                outline: none;
                margin: 0;
                padding: 0;
            }
            .leaflet-sbs-range::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 40px !important;
                height: 40px !important;
                border-radius: 50% !important;
                background: white !important;
                cursor: col-resize !important;
                border: 2px solid #0078A8 !important;
                box-shadow: 0 0 5px rgba(0, 0, 0, 0.5) !important;
            }
            .leaflet-sbs-range::-moz-range-thumb {
                width: 40px !important;
                height: 40px !important;
                border-radius: 50% !important;
                background: white !important;
                cursor: col-resize !important;
                border: 2px solid #0078A8 !important;
                box-shadow: 0 0 5px rgba(0, 0, 0, 0.5) !important;
            }
        `;
        document.head.appendChild(styleElement);
    }
}

/**
 * Get the style for a specific feature type
 * @param {string} featureType - The type of feature
 * @returns {Object} - Style object for the feature
 */
function getStyleForFeatureType(featureType) {
    switch(featureType) {
        case 'buildings':
            return {
                color: 'yellow',
                fillColor: 'yellow',
                fillOpacity: 0.4,
                weight: 2
            };
        case 'trees':
            return {
                color: 'green',
                fillColor: 'green',
                fillOpacity: 0.4,
                weight: 2
            };
        case 'water':
            return {
                color: 'blue',
                fillColor: 'blue',
                fillOpacity: 0.4,
                weight: 2
            };
        case 'roads':
            return {
                color: 'red',
                fillColor: 'red',
                fillOpacity: 0.4,
                weight: 3
            };
        default:
            return {
                color: 'purple',
                fillColor: 'purple',
                fillOpacity: 0.4,
                weight: 2
            };
    }
}

// Add styles when the script loads
document.addEventListener('DOMContentLoaded', function() {
    addSplitMapStyles();
    console.log("Split map styles added");
});
