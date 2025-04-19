cat << 'EOF' > src/components/SeedlingDashboard.tsx
import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip } from 'recharts';
import { Activity, Maximize2, Layers, Grid } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import 'leaflet/dist/leaflet.css';

const SeedlingDashboard = () => {
  const [map, setMap] = useState(null);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [analysisData] = useState({
    totalSeedlings: 1247,
    confidence: 94.2,
    timestamp: '22:03',
    resolution: '10cm',
    gridSize: '50x50m',
    imageLocation: {
      center: [31.0240, -87.4674], // PRT Atmore Nursery coordinates
      bounds: [
        [31.0190, -87.4724], // SW corner
        [31.0290, -87.4624]  // NE corner
      ],
      zoom: 15,
      address: "4165 Ross Rd, Atmore, AL 36502"
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
        const mapInstance = L.map('map').setView(analysisData.imageLocation.center, analysisData.imageLocation.zoom);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors'
        }).addTo(mapInstance);

        const marker = L.marker(analysisData.imageLocation.center)
          .bindPopup('PRT Atmore Nursery')
          .addTo(mapInstance);

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

        L.control.zoom({
          position: 'topright'
        }).addTo(mapInstance);

        setMap(mapInstance);

        return () => {
          mapInstance.remove();
        };
      });
    }
  }, []);

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

        {/* Health Status Distribution */}
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

        {/* Full Width Map */}
        <div className="col-span-12">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-green-400">Location Map</CardTitle>
                <div className="flex gap-2">
                  <button className="bg-green-500/20 p-2 rounded-lg">
                    <Layers className="text-green-400 w-5 h-5" />
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
EOF