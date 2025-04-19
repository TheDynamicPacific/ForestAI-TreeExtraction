import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip, LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { Activity, Maximize2, Layers, Grid, Trees, Sprout, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

const ForestHealthDashboard = () => {
  const [map, setMap] = useState(null);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [activeView, setActiveView] = useState('seedlings');

  const [forestData] = useState({
    totalArea: 5280, // hectares
    timestamp: '22:03',
    resolution: '50cm',
    location: {
      center: [44.5588, -110.5728], // Yellowstone coordinates
      bounds: [
        [44.5488, -110.5828],
        [44.5688, -110.5628]
      ],
      zoom: 13,
      address: "Yellowstone National Park"
    },
    healthStatus: {
      healthy: 3850,
      infected: 980,
      dead: 450
    },
    diseaseTypes: {
      barkBeetle: 620,
      rootDisease: 180,
      fungalInfection: 180
    },
    // Tree positions for visualization (simulated data)
    treePositions: Array.from({ length: 100 }, () => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      health: Math.random() > 0.7 
        ? 'healthy' 
        : Math.random() > 0.5 
          ? 'infected' 
          : 'dead'
    })),
    // Historical data
    healthHistory: Array.from({ length: 12 }, (_, i) => ({
      month: `M${i + 1}`,
      healthy: 70 + Math.random() * 10,
      infected: 20 + Math.random() * 5,
      dead: 5 + Math.random() * 5
    }))
  });

  const healthData = [
    { name: 'Healthy', value: forestData.healthStatus.healthy },
    { name: 'Infected', value: forestData.healthStatus.infected },
    { name: 'Dead', value: forestData.healthStatus.dead }
  ];

  const diseaseData = [
    { name: 'Bark Beetle', value: forestData.diseaseTypes.barkBeetle },
    { name: 'Root Disease', value: forestData.diseaseTypes.rootDisease },
    { name: 'Fungal', value: forestData.diseaseTypes.fungalInfection }
  ];

  const HEALTH_COLORS = {
    healthy: '#34D399',
    infected: '#FBBF24',
    dead: '#EF4444'
  };

  const DISEASE_COLORS = ['#8B5CF6', '#EC4899', '#F97316'];

  useEffect(() => {
    if (typeof window !== 'undefined' && !map) {
      import('leaflet').then(L => {
        const mapInstance = L.map('forest-map').setView(forestData.location.center, forestData.location.zoom);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors'
        }).addTo(mapInstance);

        // Add area marker
        const marker = L.marker(forestData.location.center)
          .bindPopup('Monitored Forest Area')
          .addTo(mapInstance);

        // Add monitoring area rectangle
        const bounds = L.latLngBounds(
          forestData.location.bounds[0],
          forestData.location.bounds[1]
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
        {/* Header Alert */}
        <div className="col-span-12">
          <Alert className="bg-yellow-500/20 border-yellow-500/50">
            <AlertTriangle className="w-5 h-5 text-yellow-400 mr-2" />
            <AlertDescription className="text-yellow-400">
              Alert: High bark beetle activity detected in northern section - {forestData.diseaseTypes.barkBeetle} hectares affected
            </AlertDescription>
          </Alert>
        </div>

        {/* Forest Health Stats */}
        <div className="col-span-3">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-green-400">Forest Health</CardTitle>
                <Trees className="text-green-400 w-5 h-5" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="flex justify-between text-gray-300">
                    <span>Total Area</span>
                    <span>{forestData.totalArea} ha</span>
                  </div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="flex justify-between text-gray-300">
                    <span>Healthy</span>
                    <span className="text-green-400">{forestData.healthStatus.healthy} ha</span>
                  </div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="flex justify-between text-gray-300">
                    <span>Infected</span>
                    <span className="text-yellow-400">{forestData.healthStatus.infected} ha</span>
                  </div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="flex justify-between text-gray-300">
                    <span>Dead</span>
                    <span className="text-red-400">{forestData.healthStatus.dead} ha</span>
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
                      <Cell 
                        key={`cell-${index}`} 
                        fill={Object.values(HEALTH_COLORS)[index]} 
                      />
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

        {/* Disease Distribution */}
        <div className="col-span-6">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-green-400">Disease Distribution</CardTitle>
                <div className="flex gap-2">
                  <button className="bg-green-500/20 p-2 rounded-lg">
                    <Maximize2 className="text-green-400 w-5 h-5" />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="w-full h-64">
                <BarChart width={600} height={200} data={diseaseData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937',
                      border: 'none',
                      borderRadius: '0.5rem'
                    }}
                    labelStyle={{ color: '#9CA3AF' }}
                  />
                  <Bar dataKey="value">
                    {diseaseData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={DISEASE_COLORS[index]} />
                    ))}
                  </Bar>
                </BarChart>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tree Health Visualization */}
        <div className="col-span-6">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <CardTitle className="text-green-400">Selected Area Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative w-full h-64 bg-gray-700/50 rounded-lg overflow-hidden">
                <div className="absolute inset-0">
                  {forestData.treePositions.map((tree, index) => (
                    <div
                      key={index}
                      className={`absolute w-2 h-2 rounded-full`}
                      style={{
                        left: `${tree.x}%`,
                        top: `${tree.y}%`,
                        backgroundColor: HEALTH_COLORS[tree.health],
                        transform: 'translate(-50%, -50%)'
                      }}
                    />
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Health Trends */}
        <div className="col-span-6">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <CardTitle className="text-green-400">Health Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="w-full h-64">
                <LineChart width={600} height={200} data={forestData.healthHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="month" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937',
                      border: 'none',
                      borderRadius: '0.5rem'
                    }}
                    labelStyle={{ color: '#9CA3AF' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="healthy" 
                    stroke={HEALTH_COLORS.healthy} 
                    strokeWidth={2}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="infected" 
                    stroke={HEALTH_COLORS.infected} 
                    strokeWidth={2}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="dead" 
                    stroke={HEALTH_COLORS.dead} 
                    strokeWidth={2}
                  />
                </LineChart>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Map */}
        <div className="col-span-12">
          <Card className="bg-gray-800 border-0">
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle className="text-green-400">Forest Area</CardTitle>
                <div className="flex gap-2">
                  <button className="bg-green-500/20 p-2 rounded-lg">
                    <Layers className="text-green-400 w-5 h-5" />
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div id="forest-map" className="w-full h-96 rounded-lg overflow-hidden" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default ForestHealthDashboard;