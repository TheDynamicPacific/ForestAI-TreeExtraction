import React, { useState } from 'react';
import { Trees, Sprout, Upload } from 'lucide-react';
import SeedlingDashboard from './SeedlingDashboard';
import ForestHealthDashboard from './ForestHealthDashboard';
import DataUploader from './DataUploader';

const IntegratedSystem = () => {
  const [viewMode, setViewMode] = useState('seedlings'); // Default to 'seedlings'

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Navigation Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex justify-between items-center max-w-screen-2xl mx-auto">
          <div className="flex gap-4">
            <button 
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                viewMode === 'seedlings' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
              onClick={() => setViewMode('seedlings')}
            >
              <Sprout className="w-5 h-5" />
              <span>Seedling Analysis</span>
            </button>
            <button 
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                viewMode === 'forest' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
              onClick={() => setViewMode('forest')}
            >
              <Trees className="w-5 h-5" />
              <span>Forest Health</span>
            </button>
            <button 
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                viewMode === 'upload' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
              onClick={() => setViewMode('upload')}
            >
              <Upload className="w-5 h-5" />
              <span>Upload Data</span>
            </button>
          </div>
          
          <div className="text-gray-400">
            <span className="text-sm">Last Updated: {new Date().toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="max-w-screen-2xl mx-auto">
        {viewMode === 'seedlings' ? (
          <SeedlingDashboard />
        ) : viewMode === 'forest' ? (
          <ForestHealthDashboard />
        ) : (
          <DataUploader />
        )}
      </div>
    </div>
  );
};

export default IntegratedSystem;