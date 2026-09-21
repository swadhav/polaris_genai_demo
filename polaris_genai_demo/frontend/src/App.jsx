import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ModelSelector from './components/ModelSelector';
import DealerSelector from './components/DealerSelector';
import VideoPlayer360 from './components/VideoPlayer360';
import ImageGallery from './components/ImageGallery';
import VehicleSpecs from './components/VehicleSpecs';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';

export default function App() {
  const [models, setModels] = useState([]);
  const [dealers, setDealers] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState('G27G5X99AZ');
  const [selectedDealerId, setSelectedDealerId] = useState('power_lodge');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCatalogData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [modelsRes, dealersRes] = await Promise.all([
        fetch('/api/models'),
        fetch('/api/dealers'),
      ]);

      if (!modelsRes.ok) {
        throw new Error(`Failed to load models (HTTP ${modelsRes.status})`);
      }
      const modelsData = await modelsRes.json();
      if (modelsData.models && modelsData.models.length > 0) {
        setModels(modelsData.models);
        // Default to G27G5X99AZ if exists, otherwise first model
        const defaultExists = modelsData.models.some((m) => m.id === 'G27G5X99AZ');
        if (!defaultExists) {
          setSelectedModelId(modelsData.models[0].id);
        }
      } else {
        throw new Error('No models found in catalog');
      }

      if (dealersRes.ok) {
        const dealersData = await dealersRes.json();
        if (dealersData.dealers && dealersData.dealers.length > 0) {
          setDealers(dealersData.dealers);
          // Default to power_lodge (which has background & staged images) or first dealer
          const hasPowerLodge = dealersData.dealers.some((d) => d.id === 'power_lodge');
          if (hasPowerLodge) {
            setSelectedDealerId('power_lodge');
          } else {
            setSelectedDealerId(dealersData.dealers[0].id);
          }
        }
      }
    } catch (err) {
      console.error('Error fetching catalog data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchDealers = async () => {
    try {
      const dealersRes = await fetch('/api/dealers');
      if (dealersRes.ok) {
        const dealersData = await dealersRes.json();
        if (dealersData.dealers && dealersData.dealers.length > 0) {
          setDealers(dealersData.dealers);
        }
      }
    } catch (err) {
      console.error('Error refreshing dealers:', err);
    }
  };

  useEffect(() => {
    fetchCatalogData();
  }, []);

  const selectedModel = models.find((m) => m.id === selectedModelId) || models[0];
  const selectedDealer = dealers.find((d) => d.id === selectedDealerId) || dealers[0];

  return (
    <div className="min-h-screen bg-[#0B0F15] text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Top Navbar */}
      <Header
        selectedModel={selectedModel}
        totalModels={models.length}
        selectedDealer={selectedDealer}
        dealers={dealers}
        onSelectDealer={setSelectedDealerId}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 text-slate-400">
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin mb-3" />
            <span className="text-sm font-medium">Loading Polaris Models & Dealers Catalog from GCS...</span>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-950/40 border border-red-800/80 rounded-2xl p-6 text-center max-w-xl mx-auto my-12">
            <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
            <h3 className="text-base font-bold text-red-200 mb-1">Failed to Load Catalog Data</h3>
            <p className="text-sm text-red-300 mb-4 font-mono">{error}</p>
            <button
              onClick={fetchCatalogData}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-semibold rounded-xl text-xs flex items-center gap-2 mx-auto"
            >
              <RefreshCw className="w-4 h-4" /> Try Again
            </button>
          </div>
        )}

        {/* Loaded View */}
        {!loading && !error && selectedModel && (
          <>
            {/* Dual Selection Controls: Model Selector & Dealer Selector */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Model Selector Bar */}
              <ModelSelector
                models={models}
                selectedModelId={selectedModelId}
                onSelectModel={setSelectedModelId}
              />

              {/* Dealer Selector Bar */}
              <DealerSelector
                dealers={dealers}
                selectedDealerId={selectedDealerId}
                onSelectDealer={setSelectedDealerId}
                selectedModel={selectedModel}
                onDealersUpdated={fetchDealers}
              />
            </div>

            {/* 360 Video Player Showcase */}
            <section aria-label="360 Rotation Video">
              <VideoPlayer360 model={selectedModel} />
            </section>

            {/* Vehicle Specs & Digital Asset Metadata */}
            <section aria-label="Vehicle Specs">
              <VehicleSpecs model={selectedModel} />
            </section>

            {/* Dealer Showroom Staging & Static Multi-Angle Images Gallery */}
            <section aria-label="Dealer Showroom & Multi-Angle Asset Showcase">
              <ImageGallery
                model={selectedModel}
                selectedDealer={selectedDealer}
                dealers={dealers}
                onSelectDealer={setSelectedDealerId}
                onDealersUpdated={fetchDealers}
              />
            </section>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-[#090D13] py-6 mt-12 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            © 2026 Polaris Inc. • GenAI 360° Studio & Dealer Showroom Showcase
          </span>
          <span className="font-mono text-[11px] text-slate-600">
            Storage: <span className="text-slate-400">gs://polaris-demo-files</span> • Engine: <span className="text-blue-500">Veo 3.1 & Nano Banana</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
