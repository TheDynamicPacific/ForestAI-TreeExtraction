import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, ImageOverlay, Rectangle, useMap } from 'react-leaflet';
import { LatLngBoundsExpression, LatLngTuple } from 'leaflet';
import { fromBlob } from 'geotiff';

// Define types for drone images
interface DroneImage {
  url: string;
  bounds: LatLngBoundsExpression;
}

// Function to extract bounds from GeoTIFF
async function getBoundsFromGeoTIFF(file: File): Promise<LatLngBoundsExpression> {
  const tiff = await fromBlob(file);
  const image = await tiff.getImage();
  const bbox = image.getBoundingBox(); // [minX, minY, maxX, maxY]
  return [
    [bbox[1], bbox[0]], // [minLat, minLng]
    [bbox[3], bbox[2]], // [maxLat, maxLng]
  ] as LatLngBoundsExpression;
}

// DroneMap component
function DroneMap({ droneImages }: { droneImages: DroneImage[] }) {
  const map = useMap();
  const [boundingBox, setBoundingBox] = useState<LatLngBoundsExpression | null>(null);

  // Calculate bounding box and center point
  const calculateBoundingBox = (images: DroneImage[]): LatLngBoundsExpression => {
    let minLat = Infinity, minLng = Infinity, maxLat = -Infinity, maxLng = -Infinity;
    images.forEach((image) => {
      const bounds = image.bounds as LatLngTuple[];
      minLat = Math.min(minLat, bounds[0][0]);
      minLng = Math.min(minLng, bounds[0][1]);
      maxLat = Math.max(maxLat, bounds[1][0]);
      maxLng = Math.max(maxLng, bounds[1][1]);
    });
    return [
      [minLat, minLng],
      [maxLat, maxLng],
    ] as LatLngBoundsExpression;
  };

  // Handle drone images
  useEffect(() => {
    if (droneImages.length > 0) {
      const bbox = calculateBoundingBox(droneImages);
      setBoundingBox(bbox);
      map.fitBounds(bbox);
    }
  }, [droneImages, map]);

  return (
    <>
      {/* Base Map */}
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />

      {/* Drone Imagery Overlay */}
      {droneImages.map((image, index) => (
        <React.Fragment key={index}>
          <ImageOverlay
            url={image.url}
            bounds={image.bounds}
            opacity={0.7}
          />
          <Rectangle
            bounds={image.bounds}
            pathOptions={{ color: 'red', weight: 2 }}
          />
        </React.Fragment>
      ))}

      {/* Total Bounding Box Layer */}
      {boundingBox && (
        <Rectangle
          bounds={boundingBox}
          pathOptions={{ color: 'blue', weight: 3 }}
        />
      )}
    </>
  );
}

// DataUploader component
const DataUploader = () => {
  const [droneImages, setDroneImages] = useState<DroneImage[]>([]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  // Handle file input change
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;

    setIsProcessing(true);
    const processedImages: DroneImage[] = [];

    for (const file of Array.from(files)) {
      try {
        // Extract bounds from GeoTIFF
        const bounds = await getBoundsFromGeoTIFF(file);

        // Create a local URL for the file
        const url = URL.createObjectURL(file);

        // Add to processed images
        processedImages.push({ url, bounds });
      } catch (error) {
        console.error('Error processing GeoTIFF:', error);
      }
    }

    setIsProcessing(false);
    setDroneImages(processedImages);
  };

  return (
    <div>
      {/* File Upload Input */}
      <input
        type="file"
        multiple
        onChange={handleFileChange}
        disabled={isProcessing}
        style={{ position: 'absolute', top: 10, left: 10, zIndex: 1000 }}
      />

      {/* Processing Indicator */}
      {isProcessing && (
        <div style={{ position: 'absolute', top: 50, left: 10, zIndex: 1000 }}>
          <span style={{ color: 'white' }}>Processing GeoTIFF files...</span>
        </div>
      )}

      {/* Map */}
      <MapContainer center={[51.505, -0.09]} zoom={13} style={{ height: '100vh', width: '100%' }}>
        <DroneMap droneImages={droneImages} />
      </MapContainer>
    </div>
  );
};

export default DataUploader;