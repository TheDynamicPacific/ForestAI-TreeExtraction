import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip } from 'recharts';
import { Activity, Maximize2, Layers, Grid } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import 'leaflet/dist/leaflet.css';

const SeedlingDashboard = () => {
  const [map, setMap] = useState(null);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [activeBaseLayer, setActiveBaseLayer] = useState('satellite');
  const [baseLayers, setBaseLayers] = useState({});
  const [analysisData] = useState({
    totalSeedlings: 1247,
    confidence: 94.2,
    timestamp: '22:03',
    resolution: '10cm',
    gridSize: '50x50m',
    imageLocation: {
      center: [31.1733286, -87.438407], // Updated center coordinates
      bounds: [
        [31.1683286, -87.443407], // SW corner - adjusted to create a reasonable boundary
        [31.1783286, -87.433407]  // NE corner - adjusted to create a reasonable boundary
      ],
      zoom: 16, // Increased zoom level for better initial view
      address: "4165 Nursery Rd, Atmore, AL 36502" // Updated address
    },
    healthStatus: {
      healthy: 987,
      unhealthy: 260
    },
    seedlingPositions: Array.from({ length: 50 }, () => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      health: Math.random() > 0.2 ? 'healthy' : 'unhealthy'
    }))
  });

  const healthData = [
    { name: 'Healthy', value: analysisData.healthStatus.healthy },
    { name: 'Unhealthy', value: analysisData.healthStatus.unhealthy }
  ];

  const HEALTH_COLORS = ['#34D399', '#EF4444'];

  useEffect(() => {
    if (typeof window !== 'undefined' && !map) {
      import('leaflet').then(L => {
        // Initialize map with high zoom level for detailed view
        const mapInstance = L.map('map', {
          zoomControl: false, // We'll add custom zoom control
          minZoom: 5,
          maxZoom: 20
        }).setView(analysisData.imageLocation.center, analysisData.imageLocation.zoom);

        // Define all available base layers
        const baseLayersConfig = {
          'Satellite': L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
            attribution: '© Google',
            maxZoom: 20
          }),
          'Hybrid': L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
            attribution: '© Google',
            maxZoom: 20
          }),
          'Streets': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
          }),
          'Terrain': L.tileLayer('https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}', {
            attribution: '© Google',
            maxZoom: 20
          })
        };

        // Add satellite layer as default
        baseLayersConfig['Satellite'].addTo(mapInstance);
        
        // Add layer control with custom styling
        const layerControl = L.control.layers(baseLayersConfig, {}, {
          position: 'topright',
          collapsed: false,
          className: 'bg-gray-800 rounded-lg p-2 text-gray-300'
        }).addTo(mapInstance);

        // Add custom zoom control
        L.control.zoom({
          position: 'topright'
        }).addTo(mapInstance);

        // Add scale control
        L.control.scale({
          imperial: true,
          metric: true,
          position: 'bottomright'
        }).addTo(mapInstance);

        // Store base layers for later reference
        setBaseLayers(baseLayersConfig);

        // Add nursery marker
        const marker = L.marker(analysisData.imageLocation.center, {
          title: 'PRT Atmore Nursery'
        }).bindPopup(
          '<div class="text-gray-900">' +
          '<strong>PRT Atmore Nursery</strong><br>' +
          `${analysisData.totalSeedlings} seedlings detected<br>` +
          `${analysisData.confidence}% confidence` +
          '</div>'
        ).addTo(mapInstance);

        // Add monitoring area rectangle
        const bounds = L.latLngBounds(
          analysisData.imageLocation.bounds[0],
          analysisData.imageLocation.bounds[1]
        );
        
        const rectangle = L.rectangle(bounds, {
          color: '#34D399',
          weight: 2,
          fillColor: '#34D399',
          fillOpacity: 0.1,
          dashArray: '5, 5'
        }).addTo(mapInstance);

        // Add selection functionality
        let drawingRect = null;
        let startPoint = null;

        mapInstance.on('mousedown', (e) => {
          startPoint = e.latlng;
          if (drawingRect) {
            mapInstance.removeLayer(drawingRect);
          }
          drawingRect = L.rectangle([startPoint, startPoint], {
            color: '#60A5FA',
            weight: 2,
            fillColor: '#60A5FA',
            fillOpacity: 0.1
          }).addTo(mapInstance);
        });

        mapInstance.on('mousemove', (e) => {
          if (startPoint && drawingRect) {
            const bounds = L.latLngBounds(startPoint, e.latlng);
            drawingRect.setBounds(bounds);
          }
        });

        mapInstance.on('mouseup', (e) => {
          if (startPoint && drawingRect) {
            const bounds = L.latLngBounds(startPoint, e.latlng);
            setSelectedRegion({
              bounds: bounds,
              center: bounds.getCenter()
            });
            startPoint = null;
          }
        });

        // Fit to monitoring area bounds
        mapInstance.fitBounds(bounds, {
          padding: [50, 50]
        });

        setMap(mapInstance);

        return () => {
          mapInstance.remove();
        };
      });
    }
  }, []);

  // Layer switch handler
  const handleLayerSwitch = (layerName) => {
    if (map && baseLayers[layerName]) {
      Object.entries(baseLayers).forEach(([name, layer]) => {
        if (name === layerName) {
          map.addLayer(layer);
        } else {
          map.removeLayer(layer);
        }
      });
      setActiveBaseLayer(layerName.toLowerCase());
    }
  };

  return (
    <div className="bg-gray-900 p-4 w-full h-full min-h-screen">
      <div className="grid grid-cols-12 gap-4">
        {/* Header with Analysis Status */}
        <div className="col-span-12">
          <Alert className="bg-green-500/20 border-green-500/50">
            <AlertDescription className="text-green-400">
              Processing complete: {analysisData.totalSeedlings} seedlings detected with {analysisData.confidence}% confidence
            </AlertDescription>
          </Alert>
        </div>

        {/* Main Stats */}
        <div className="col-span-3">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-green-400">Detection Stats</CardTitle>
                <Grid className="text-green-400 w-5 h-5" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="flex justify-between text-gray-300">
                    <span>Total Count</span>
                    <span>{analysisData.totalSeedlings}</span>
                  </div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="flex justify-between text-gray-300">
                    <span>Healthy</span>
                    <span className="text-green-400">{analysisData.healthStatus.healthy}</span>
                  </div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="flex justify-between text-gray-300">
                    <span>Unhealthy</span>
                    <span className="text-red-400">{analysisData.healthStatus.unhealthy}</span>
                  </div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="flex justify-between text-gray-300">
                    <span>Location</span>
                    <span>{analysisData.imageLocation.address}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Health Distribution */}
        <div className="col-span-3">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <CardTitle className="text-green-400">Health Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="w-full h-64 flex items-center justify-center">
                <PieChart width={200} height={200}>
                  <Pie
                    data={healthData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {healthData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={HEALTH_COLORS[index]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937',
                      border: 'none',
                      borderRadius: '0.5rem'
                    }}
                    labelStyle={{ color: '#9CA3AF' }}
                  />
                </PieChart>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Detected Seedlings View */}
        <div className="col-span-6">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-green-400">Detected Seedlings</CardTitle>
                <div className="flex gap-2">
                  <button className="bg-green-500/20 p-2 rounded-lg">
                    <Maximize2 className="text-green-400 w-5 h-5" />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="relative w-full h-64 bg-gray-700/50 rounded-lg overflow-hidden">
                <div className="absolute inset-0">
                  {analysisData.seedlingPositions.map((seedling, index) => (
                    <div
                      key={index}
                      className={`absolute w-2 h-2 rounded-full ${
                        seedling.health === 'healthy' ? 'bg-green-400' : 'bg-red-400'
                      }`}
                      style={{
                        left: `${seedling.x}%`,
                        top: `${seedling.y}%`,
                        transform: 'translate(-50%, -50%)'
                      }}
                    />
                  ))}
                </div>
                <div className="absolute inset-0 border border-gray-600">
                  <div className="text-gray-400 text-center mt-4">
                    Selected area view
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Enhanced Map */}
        <div className="col-span-12">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-green-400">Location Map</CardTitle>
                <div className="flex gap-2">
                  {/* Layer quick access buttons */}
                  <div className="flex gap-2 mr-4">
                    {Object.keys(baseLayers).map((layerName) => (
                      <button
                        key={layerName}
                        className={`bg-green-500/20 p-2 rounded-lg text-sm ${
                          activeBaseLayer === layerName.toLowerCase() ? 'ring-2 ring-green-400' : ''
                        }`}
                        onClick={() => handleLayerSwitch(layerName)}
                      >
                        <span className="text-green-400">{layerName}</span>
                      </button>
                    ))}
                  </div>
                  {/* Fit to bounds button */}
                  <button 
                    className="bg-green-500/20 p-2 rounded-lg"
                    onClick={() => {
                      if (map && selectedRegion) {
                        map.fitBounds(selectedRegion.bounds);
                      } else if (map) {
                        map.fitBounds(L.latLngBounds(
                          analysisData.imageLocation.bounds[0],
                          analysisData.imageLocation.bounds[1]
                        ));
                      }
                    }}
                  >
                    <Maximize2 className="text-green-400 w-5 h-5" />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div id="map" className="w-full h-96 rounded-lg overflow-hidden" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default SeedlingDashboard;