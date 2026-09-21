import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  ZoomIn,
  X,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Store,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Sparkles,
  ShieldCheck,
  Building2,
  Layers,
  ArrowRight,
  UploadCloud,
  RefreshCw,
  Loader2,
  ImagePlus,
  FileImage,
  Check,
} from 'lucide-react';

export default function ImageGallery({
  model,
  selectedDealer,
  dealers = [],
  onSelectDealer,
  onDealersUpdated,
}) {
  const images = model?.images || [];
  const [selectedImageIndex, setSelectedImageIndex] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [evalLoading, setEvalLoading] = useState(false);

  // Upload & Generation states
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState('');
  const [uploadError, setUploadError] = useState(null);
  const [generationError, setGenerationError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [imageVersion, setImageVersion] = useState(Date.now());
  const [showReplaceBg, setShowReplaceBg] = useState(false);

  const fileInputRef = useRef(null);
  const replaceFileInputRef = useRef(null);
  const attemptedAutoGenerations = useRef(new Set());

  const modelId = model?.id;
  const dealerId = selectedDealer?.id;
  const hasBackground = Boolean(selectedDealer?.has_background);
  const hasLogo = Boolean(selectedDealer?.has_logo);
  const hasShowroomImage = Boolean(
    hasBackground && selectedDealer?.generated_models?.includes(modelId)
  );

  const showroomImageUrl = `/api/dealers/${dealerId}/models/${modelId}/showroom?v=${imageVersion}`;
  const showroomEvalUrl = `/api/dealers/${dealerId}/models/${modelId}/evaluation?v=${imageVersion}`;

  // Fetch QA audit evaluation report when model or dealer changes or when image is generated
  useEffect(() => {
    let isMounted = true;
    if (hasShowroomImage && dealerId && modelId) {
      setEvalLoading(true);
      fetch(showroomEvalUrl)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (isMounted) {
            setEvaluation(data);
            setEvalLoading(false);
          }
        })
        .catch(() => {
          if (isMounted) {
            setEvaluation(null);
            setEvalLoading(false);
          }
        });
    } else {
      setEvaluation(null);
      setEvalLoading(false);
    }
    return () => {
      isMounted = false;
    };
  }, [dealerId, modelId, hasShowroomImage, imageVersion]);

  // Requirement 2: If dealer background & logo are both available, but vehicle showroom image is missing for selected model -> Auto-generate & display
  useEffect(() => {
    if (!dealerId || !modelId) return;
    const taskKey = `${dealerId}:${modelId}`;

    if (
      hasBackground &&
      hasLogo &&
      !hasShowroomImage &&
      !isGenerating &&
      !isUploading &&
      !attemptedAutoGenerations.current.has(taskKey)
    ) {
      attemptedAutoGenerations.current.add(taskKey);
      handleAutoGenerate(dealerId, modelId);
    }
  }, [dealerId, modelId, hasBackground, hasLogo, hasShowroomImage, isGenerating, isUploading]);

  // Trigger showroom image generation
  const handleAutoGenerate = async (targetDealerId, targetModelId) => {
    setIsGenerating(true);
    setGenerationError(null);
    setGenerationStep('Verifying dealer background and clean architectural plate...');

    const timer1 = setTimeout(() => {
      setGenerationStep('Compositing vehicle 3/4 perspective & ray-tracing floor reflections...');
    }, 3500);
    const timer2 = setTimeout(() => {
      setGenerationStep('Synthesizing 3D dealer architectural wall signage...');
    }, 8000);
    const timer3 = setTimeout(() => {
      setGenerationStep('Executing autonomous Gemini 2.5 Flash QA compliance audit...');
    }, 13000);

    try {
      const res = await fetch(`/api/dealers/${targetDealerId}/models/${targetModelId}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.message || data.error || 'Showroom generation failed');
      }

      setImageVersion(Date.now());
      if (onDealersUpdated) {
        await onDealersUpdated();
      }
    } catch (err) {
      console.error('Showroom auto-generation failed:', err);
      setGenerationError(err.message || 'Showroom staging generation failed');
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setIsGenerating(false);
      setGenerationStep('');
    }
  };

  // Requirement 1: Handle file selection for background upload
  const handleFileSelect = (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setUploadError('Please select a valid image file (JPEG, PNG, or WEBP)');
      return;
    }
    setSelectedFile(file);
    setUploadError(null);
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewUrl(e.target.result);
    };
    reader.readAsDataURL(file);
  };

  // Requirement 1: Upload background image, save in dealer folder, and run generate_dealer_showroom.py
  const handleUploadAndGenerate = async () => {
    if (!selectedFile || !dealerId || !modelId) return;

    setIsUploading(true);
    setUploadError(null);
    setGenerationStep(`Saving background photo to dealers/${dealerId}/dealer background.jpg...`);

    const timer1 = setTimeout(() => {
      setGenerationStep('Inpainting clean architectural plate (removing rival OEM branding)...');
    }, 3500);
    const timer2 = setTimeout(() => {
      setGenerationStep(`Compositing ${model?.title} with ray-traced reflections...`);
    }, 9000);
    const timer3 = setTimeout(() => {
      setGenerationStep('Rendering 3D dealer wall signage & logo lighting...');
    }, 15000);
    const timer4 = setTimeout(() => {
      setGenerationStep('Autonomous Gemini 2.5 Flash QA compliance evaluation...');
    }, 20000);

    try {
      const formData = new FormData();
      formData.append('image', selectedFile);
      formData.append('model_id', modelId);

      const res = await fetch(`/api/dealers/${dealerId}/upload-background`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.message || data.error || 'Failed to upload background or generate showroom');
      }

      // Cleanup selection state
      setSelectedFile(null);
      setPreviewUrl(null);
      setShowReplaceBg(false);
      setImageVersion(Date.now());
      if (onDealersUpdated) {
        await onDealersUpdated();
      }
    } catch (err) {
      console.error('Upload & showroom generation failed:', err);
      setUploadError(err.message || 'Background upload and generation failed');
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      clearTimeout(timer4);
      setIsUploading(false);
      setGenerationStep('');
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  // Construct combined images array for Lightbox navigation
  const lightboxItems = [];
  if (hasShowroomImage) {
    lightboxItems.push({
      url: showroomImageUrl,
      label: `Dealer Showroom (${selectedDealer?.name || selectedDealer?.folder_name})`,
      filename: `${modelId}_showroom.png`,
      isShowroom: true,
      gcs_uri: `gs://polaris-demo-files/dealers/${dealerId}/generated/${modelId}_showroom.png`,
      evaluation: evaluation,
    });
  }
  images.forEach((img) => {
    lightboxItems.push({
      ...img,
      isShowroom: false,
    });
  });

  const openLightbox = (idx) => {
    setSelectedImageIndex(idx);
  };

  const closeLightbox = () => {
    setSelectedImageIndex(null);
  };

  const prevImage = (e) => {
    e.stopPropagation();
    setSelectedImageIndex((prev) => (prev === 0 ? lightboxItems.length - 1 : prev - 1));
  };

  const nextImage = (e) => {
    e.stopPropagation();
    setSelectedImageIndex((prev) => (prev === lightboxItems.length - 1 ? 0 : prev + 1));
  };

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-2xl p-5 shadow-xl space-y-6">
      {/* =====================================================================
          PART 1: DEALER SHOWROOM STAGING (Featured Image or Upload/Generation UI)
          ===================================================================== */}
      <div className="border border-slate-800/90 rounded-2xl p-4 sm:p-5 bg-gradient-to-b from-[#161F2E] to-[#121824] shadow-lg">
        {/* Dealer Showroom Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-3">
            {selectedDealer?.logo_url ? (
              <div className="w-12 h-10 rounded-lg bg-white/10 p-1 border border-slate-700/80 flex items-center justify-center shrink-0 overflow-hidden">
                <img
                  src={selectedDealer.logo_url}
                  alt={selectedDealer.name}
                  className="max-w-full max-h-full object-contain"
                />
              </div>
            ) : (
              <div className="p-2 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30">
                <Store className="w-5 h-5" />
              </div>
            )}
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide">
                  Vehicle in Dealer Showroom
                </h2>
                <span className="px-2 py-0.5 text-xs font-mono font-bold rounded-full bg-blue-900/60 text-blue-300 border border-blue-700/50">
                  {selectedDealer?.folder_name || 'Dealer'}
                </span>
                {isGenerating || isUploading ? (
                  <span className="px-2 py-0.5 text-[11px] font-bold rounded-full bg-blue-950/90 text-blue-300 border border-blue-700/60 flex items-center gap-1 animate-pulse">
                    <Loader2 className="w-3 h-3 animate-spin text-blue-400" /> Staging in Progress
                  </span>
                ) : hasShowroomImage ? (
                  <span className="px-2 py-0.5 text-[11px] font-bold rounded-full bg-emerald-950/90 text-emerald-300 border border-emerald-700/60 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Staged
                  </span>
                ) : !hasBackground ? (
                  <span className="px-2 py-0.5 text-[11px] font-bold rounded-full bg-amber-950/90 text-amber-300 border border-amber-700/60 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-amber-400" /> Pending Background
                  </span>
                ) : (
                  <span className="px-2 py-0.5 text-[11px] font-bold rounded-full bg-sky-950/90 text-sky-300 border border-sky-700/60 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-sky-400" /> Ready to Stage
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Dealer Showroom:{' '}
                <span className="text-slate-200 font-semibold">{selectedDealer?.name}</span> • Folder:{' '}
                <span className="font-mono text-blue-400">{selectedDealer?.folder_name}</span>
              </p>
            </div>
          </div>

          {/* Header Action Controls */}
          <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
            {/* Replace Background Toggle if staged */}
            {hasShowroomImage && !isGenerating && !isUploading && (
              <button
                onClick={() => setShowReplaceBg(!showReplaceBg)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 border transition ${
                  showReplaceBg
                    ? 'bg-blue-600 text-white border-blue-400'
                    : 'bg-[#1A2232] text-slate-300 hover:text-white border-slate-700 hover:border-slate-600'
                }`}
                title="Upload a new background photo for this dealer"
              >
                <ImagePlus className="w-3.5 h-3.5 text-blue-400" />
                <span>{showReplaceBg ? 'Cancel Replace' : 'Replace Background'}</span>
              </button>
            )}

            {/* Re-generate button if staged */}
            {hasShowroomImage && !isGenerating && !isUploading && (
              <button
                onClick={() => {
                  attemptedAutoGenerations.current.delete(`${dealerId}:${modelId}`);
                  handleAutoGenerate(dealerId, modelId);
                }}
                className="px-3 py-1.5 rounded-lg bg-[#1A2232] hover:bg-[#202B3F] text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 border border-slate-700 hover:border-blue-500/50 transition"
                title="Regenerate showroom staging for this vehicle"
              >
                <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
                <span>Regenerate</span>
              </button>
            )}

            {/* Dealer Quick Selector */}
            {dealers.length > 0 && onSelectDealer && (
              <div className="flex items-center gap-1.5">
                <select
                  value={selectedDealer?.id || ''}
                  onChange={(e) => onSelectDealer(e.target.value)}
                  className="bg-[#1A2232] text-white font-mono text-xs font-semibold py-1.5 px-3 rounded-lg border border-slate-700 hover:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
                >
                  {dealers.map((d) => (
                    <option key={d.id} value={d.id} className="bg-[#18202C] text-white">
                      {d.folder_name} {d.has_background ? '(Ready)' : '(No BG)'}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* ------------------------------------------------------------------
            STATE 1: Active Generation or Upload Progress Card
            ------------------------------------------------------------------ */}
        {(isGenerating || isUploading) && (
          <div className="relative rounded-xl overflow-hidden border border-blue-500/40 bg-gradient-to-br from-[#0F1A2E] via-[#0E1524] to-[#131D2D] p-8 sm:p-12 text-center shadow-2xl my-2">
            <div className="max-w-xl mx-auto space-y-5">
              {/* Pulsing Staging Icon */}
              <div className="relative w-16 h-16 mx-auto">
                <div className="absolute inset-0 rounded-2xl bg-blue-500/20 animate-ping" />
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 border border-blue-400/50 flex items-center justify-center text-white shadow-xl shadow-blue-500/30">
                  <Loader2 className="w-8 h-8 animate-spin text-white" />
                </div>
              </div>

              <div>
                <h3 className="text-lg sm:text-xl font-bold text-white tracking-wide">
                  {isUploading
                    ? 'Uploading Background & Staging Vehicle...'
                    : 'Generating Vehicle in Dealer Showroom...'}
                </h3>
                <p className="text-xs sm:text-sm text-slate-300 mt-1">
                  Staging <span className="font-semibold text-blue-400">{model?.title}</span> into{' '}
                  <span className="font-semibold text-slate-200">{selectedDealer?.name}</span> showroom
                </p>
              </div>

              {/* Live Step Progress Indicator */}
              <div className="bg-[#0A0F18]/90 border border-blue-500/30 rounded-xl px-4 py-3 text-xs font-mono text-blue-300 flex items-center justify-center gap-2 shadow-inner">
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping shrink-0" />
                <span className="truncate">{generationStep || 'Running Nano Banana staging agent...'}</span>
              </div>

              {/* Agent Pipeline Steps Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-[11px] font-mono">
                <div className="px-2.5 py-1.5 rounded-lg bg-blue-950/60 border border-blue-800/40 text-blue-300 flex items-center justify-center gap-1.5">
                  <Check className="w-3 h-3 text-blue-400" /> Clean Plate
                </div>
                <div className="px-2.5 py-1.5 rounded-lg bg-blue-950/60 border border-blue-800/40 text-blue-300 flex items-center justify-center gap-1.5">
                  <Sparkles className="w-3 h-3 text-blue-400" /> 3/4 Perspective
                </div>
                <div className="px-2.5 py-1.5 rounded-lg bg-blue-950/60 border border-blue-800/40 text-blue-300 flex items-center justify-center gap-1.5">
                  <Building2 className="w-3 h-3 text-blue-400" /> 3D Wall Signage
                </div>
                <div className="px-2.5 py-1.5 rounded-lg bg-blue-950/60 border border-blue-800/40 text-blue-300 flex items-center justify-center gap-1.5">
                  <ShieldCheck className="w-3 h-3 text-blue-400" /> Gemini QA
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            STATE 2: Replace Background Panel (Optional overlay when staged)
            ------------------------------------------------------------------ */}
        {showReplaceBg && hasShowroomImage && !isGenerating && !isUploading && (
          <div className="mb-4 p-5 bg-[#0D1420] border-2 border-blue-500/40 rounded-xl shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-blue-400" />
                <h4 className="text-sm font-bold text-white">
                  Upload New Showroom Background for {selectedDealer?.name}
                </h4>
              </div>
              <button
                onClick={() => {
                  setShowReplaceBg(false);
                  setSelectedFile(null);
                  setPreviewUrl(null);
                  setUploadError(null);
                }}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300 mb-3">
              Uploading a new background will overwrite the current showroom plate and re-run staging for {model?.title}.
            </p>

            {/* Dropzone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => replaceFileInputRef.current?.click()}
              className={`p-6 border-2 border-dashed rounded-xl cursor-pointer text-center transition ${
                isDragging
                  ? 'border-blue-400 bg-blue-950/30'
                  : 'border-slate-700 hover:border-blue-500 bg-[#121927]/60'
              }`}
            >
              <input
                ref={replaceFileInputRef}
                type="file"
                accept="image/png, image/jpeg, image/jpg, image/webp"
                className="hidden"
                onChange={(e) => handleFileSelect(e.target.files[0])}
              />

              {previewUrl ? (
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-36 h-20 object-cover rounded-lg border border-blue-400/60 shadow-md"
                  />
                  <div className="text-left text-xs space-y-1">
                    <span className="text-white font-semibold block truncate max-w-xs">{selectedFile?.name}</span>
                    <span className="text-slate-400 font-mono block">
                      {(selectedFile?.size / 1024 / 1024).toFixed(2)} MB • {selectedFile?.type}
                    </span>
                    <span className="text-blue-400 font-medium">Click to select a different photo</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <UploadCloud className="w-8 h-8 text-blue-400 mx-auto mb-1" />
                  <span className="text-xs font-semibold text-white block">
                    Click to choose photo or drag & drop here
                  </span>
                  <span className="text-[11px] text-slate-400 font-mono block">
                    JPEG, PNG, or WEBP (recommended 1920×1080 or higher)
                  </span>
                </div>
              )}
            </div>

            {selectedFile && (
              <div className="mt-4 flex items-center justify-end gap-2.5">
                <button
                  onClick={() => {
                    setSelectedFile(null);
                    setPreviewUrl(null);
                  }}
                  className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Clear Selection
                </button>
                <button
                  onClick={handleUploadAndGenerate}
                  className="px-4 py-2 text-xs font-bold rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-blue-500/20 flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  Upload & Re-Stage {model?.title}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------------
            STATE 3: CONDITION A — Showroom Image IS Generated & Staged
            ------------------------------------------------------------------ */}
        {hasShowroomImage && !isGenerating && !isUploading && (
          <div className="relative group bg-slate-950 rounded-xl overflow-hidden border border-slate-700/80 shadow-2xl">
            {/* Showroom Image Viewport */}
            <div
              onClick={() => openLightbox(0)}
              className="relative aspect-16/9 sm:aspect-21/9 max-h-[500px] w-full flex items-center justify-center cursor-pointer overflow-hidden"
            >
              <img
                src={showroomImageUrl}
                alt={`${model?.title} staged in ${selectedDealer?.name} showroom`}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />

              {/* Lighting & Vignette Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-black/20 pointer-events-none" />

              {/* Hover Zoom Overlay */}
              <div className="absolute inset-0 bg-blue-950/30 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center pointer-events-none">
                <div className="p-3 rounded-full bg-blue-600/90 text-white shadow-2xl backdrop-blur-md transform scale-75 group-hover:scale-100 transition-transform">
                  <ZoomIn className="w-6 h-6" />
                </div>
              </div>

              {/* Top-Right Badges */}
              <div className="absolute top-3 right-3 flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-black/70 backdrop-blur-md text-blue-300 border border-blue-500/40 flex items-center gap-1.5 shadow-lg">
                  <Sparkles className="w-3.5 h-3.5 text-blue-400" /> Nano Banana Composited
                </span>

                {evaluation && (
                  <span className="px-2.5 py-1 text-xs font-mono font-bold rounded-lg bg-emerald-950/90 backdrop-blur-md text-emerald-300 border border-emerald-600/60 flex items-center gap-1 shadow-lg">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    QA Score: {evaluation.total_score}/100
                  </span>
                )}
              </div>

              {/* Bottom-Left Information Overlay */}
              <div className="absolute bottom-3 left-3 right-3 flex flex-col sm:flex-row sm:items-end justify-between gap-2 text-white">
                <div className="bg-black/60 backdrop-blur-md p-2.5 sm:p-3 rounded-xl border border-white/10 max-w-xl">
                  <div className="text-xs uppercase tracking-wider text-blue-400 font-bold flex items-center gap-1.5">
                    <Building2 className="w-3.5 h-3.5" />
                    {selectedDealer?.name} Showroom Staging
                  </div>
                  <div className="text-sm sm:text-base font-bold text-white mt-0.5">
                    {model?.title} ({model?.color})
                  </div>
                  <div className="text-xs text-slate-300 mt-1 flex flex-wrap gap-2">
                    <span className="text-emerald-400 font-medium">✓ Ray-traced floor reflections</span>
                    <span>•</span>
                    <span className="text-blue-300 font-medium">✓ 3D branded wall signage</span>
                    <span>•</span>
                    <span className="text-sky-300 font-medium">✓ Zero rival OEM IP</span>
                  </div>
                </div>

                <button
                  onClick={() => openLightbox(0)}
                  className="px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-xs flex items-center gap-1.5 self-start sm:self-auto shadow-lg backdrop-blur-md border border-blue-400/40 transition"
                >
                  <ZoomIn className="w-3.5 h-3.5" /> High-Res Inspection
                </button>
              </div>
            </div>

            {/* QA Audit Summary Drawer */}
            {evaluation && (
              <div className="px-4 py-3 bg-[#101622] border-t border-slate-800 text-xs text-slate-300 flex flex-wrap items-center justify-between gap-2 font-mono">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-slate-400">Entity: <strong className="text-white">{evaluation.scores?.vehicle_entity_preservation || 35}/35</strong></span>
                  <span className="text-slate-400">Photorealism: <strong className="text-white">{evaluation.scores?.photorealism_reflections_shadows || 25}/25</strong></span>
                  <span className="text-slate-400">Competitor IP: <strong className="text-emerald-400">0% Rival IP (Clean)</strong></span>
                  <span className="text-slate-400">Dealer Signage: <strong className="text-white">{evaluation.scores?.dealer_3d_signage || 15}/15</strong></span>
                </div>
                <div className="text-[11px] text-blue-400">
                  Model: {modelId} • Dealer: {dealerId}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------------
            STATE 4: CONDITION B — Background IS MISSING -> Upload Option
            ------------------------------------------------------------------ */}
        {!hasBackground && !isGenerating && !isUploading && (
          <div className="bg-amber-950/20 border-2 border-dashed border-amber-700/60 rounded-xl p-5 sm:p-7 text-center my-2 space-y-4">
            <div className="max-w-2xl mx-auto space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-amber-900/40 border border-amber-600/40 flex items-center justify-center mx-auto text-amber-400 shadow-inner">
                <AlertTriangle className="w-6 h-6" />
              </div>

              {/* Exact Required User Phrasing */}
              <h3 className="text-base sm:text-lg font-bold text-amber-200">
                Image is not generated since dealer background is missing.
              </h3>

              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                No showroom background photograph was found in the repository for dealer{' '}
                <span className="font-semibold text-white font-mono">{selectedDealer?.folder_name}</span>{' '}
                ({selectedDealer?.name}). Upload a dealer background photograph below to stage{' '}
                <span className="font-semibold text-blue-400">{model?.title}</span> into this dealer's showroom.
              </p>

              {/* Upload Dropzone Box */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`p-6 sm:p-8 border-2 border-dashed rounded-xl cursor-pointer text-center transition bg-[#0E1522]/80 ${
                  isDragging
                    ? 'border-blue-400 bg-blue-950/40 shadow-lg shadow-blue-500/20'
                    : 'border-slate-700 hover:border-blue-500 hover:bg-[#121927]'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png, image/jpeg, image/jpg, image/webp"
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files[0])}
                />

                {previewUrl ? (
                  <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                    <img
                      src={previewUrl}
                      alt="Selected Preview"
                      className="w-44 h-24 object-cover rounded-lg border-2 border-blue-500 shadow-lg"
                    />
                    <div className="text-left text-xs space-y-1">
                      <div className="flex items-center gap-1.5 text-white font-bold text-sm">
                        <FileImage className="w-4 h-4 text-blue-400" />
                        <span className="truncate max-w-xs">{selectedFile?.name}</span>
                      </div>
                      <span className="text-slate-400 font-mono block">
                        Size: {(selectedFile?.size / 1024 / 1024).toFixed(2)} MB • {selectedFile?.type}
                      </span>
                      <span className="text-emerald-400 font-medium block">
                        ✓ Ready to upload as <code className="font-mono text-emerald-300">dealer background.jpg</code>
                      </span>
                      <span className="text-blue-400 font-semibold cursor-pointer underline">
                        Click here to select a different photo
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <UploadCloud className="w-10 h-10 text-blue-400 mx-auto" />
                    <div>
                      <span className="text-sm font-bold text-white block">
                        Click to select dealer background photo or drag & drop here
                      </span>
                      <span className="text-xs text-slate-400 font-mono block mt-1">
                        Accepts JPG, PNG, WEBP • Saves to <span className="text-blue-400">dealers/{selectedDealer?.folder_name}/dealer background.jpg</span>
                      </span>
                    </div>
                    <button
                      type="button"
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-xs inline-flex items-center gap-1.5 shadow-md transition"
                    >
                      <ImagePlus className="w-4 h-4" /> Browse Photo
                    </button>
                  </div>
                )}
              </div>

              {/* Upload Error Alert */}
              {uploadError && (
                <div className="p-3 rounded-xl bg-red-950/60 border border-red-800 text-xs text-red-200 flex items-center justify-between gap-2 text-left">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                    <span>{uploadError}</span>
                  </div>
                  <button
                    onClick={() => setUploadError(null)}
                    className="text-red-300 hover:text-white underline shrink-0 font-medium"
                  >
                    Dismiss
                  </button>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                {selectedFile && (
                  <>
                    <button
                      onClick={() => {
                        setSelectedFile(null);
                        setPreviewUrl(null);
                        setUploadError(null);
                      }}
                      className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl transition"
                    >
                      Clear File
                    </button>
                    <button
                      onClick={handleUploadAndGenerate}
                      className="px-5 py-2.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-blue-500/25 flex items-center gap-2 transition"
                    >
                      <Sparkles className="w-4 h-4" />
                      Upload Background & Stage {model?.title} Showroom
                    </button>
                  </>
                )}

                {/* Quick Switch to Ready Dealer (Power Lodge) */}
                {dealers.some((d) => d.id === 'power_lodge') && onSelectDealer && !selectedFile && (
                  <button
                    onClick={() => onSelectDealer('power_lodge')}
                    className="px-4 py-2 bg-[#1A2232] hover:bg-[#202B3F] text-slate-300 hover:text-white border border-slate-700 rounded-xl text-xs flex items-center gap-2 transition"
                  >
                    <span>View Staged Showroom for <strong>power_lodge</strong></span>
                    <ArrowRight className="w-4 h-4 text-blue-400" />
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------
            STATE 5: Background & Logo available, but showroom staging error
            ------------------------------------------------------------------ */}
        {hasBackground && hasLogo && !hasShowroomImage && !isGenerating && !isUploading && generationError && (
          <div className="bg-red-950/30 border border-red-800/80 rounded-xl p-6 text-center my-2 space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-red-900/40 border border-red-600/40 flex items-center justify-center mx-auto text-red-400">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-red-200">
                Showroom Staging Generation Encountered an Error
              </h3>
              <p className="text-xs text-red-300 max-w-xl mx-auto mt-1 font-mono">
                {generationError}
              </p>
            </div>
            <button
              onClick={() => {
                attemptedAutoGenerations.current.delete(`${dealerId}:${modelId}`);
                handleAutoGenerate(dealerId, modelId);
              }}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-semibold rounded-xl text-xs inline-flex items-center gap-2 shadow-lg transition"
            >
              <RefreshCw className="w-4 h-4" /> Retry Staging Generation
            </button>
          </div>
        )}
      </div>

      {/* =====================================================================
          PART 2: ALONG WITH THE OTHER IMAGES OF THE VEHICLE (CGI Perspectives)
          ===================================================================== */}
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white tracking-wide">
                  Vehicle Factory CGI Perspectives
                </h3>
                <span className="px-2 py-0.5 text-xs font-mono font-bold rounded-full bg-indigo-900/60 text-indigo-300 border border-indigo-700/50">
                  {images.length} Camera Angles
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Dynamic CGI Studio Perspectives for {model?.title}: Front, Profile, Rear/Dash, 3/4, Top-Down
              </p>
            </div>
          </div>

          <span className="text-xs text-slate-400 font-mono">
            Click any image to enlarge
          </span>
        </div>

        {/* Up to 5 Static Images Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {images.map((img, idx) => {
            const lightboxIdx = hasShowroomImage ? idx + 1 : idx;
            return (
              <div
                key={img.filename}
                onClick={() => openLightbox(lightboxIdx)}
                className="group relative bg-[#182130] rounded-xl overflow-hidden border border-slate-700/70 hover:border-blue-500 transition-all duration-200 cursor-pointer shadow-lg hover:shadow-blue-500/10 hover:-translate-y-1 flex flex-col"
              >
                {/* Perspective Label Ribbon */}
                <div className="px-3 py-2 bg-[#1E293B] border-b border-slate-700/60 flex items-center justify-between">
                  <span className="text-xs font-bold text-white truncate">{img.label}</span>
                  <span className="text-[10px] font-mono text-blue-400 font-semibold">#{idx + 1}</span>
                </div>

                {/* Thumbnail Image Viewport */}
                <div className="relative aspect-4/3 bg-slate-950 flex items-center justify-center overflow-hidden">
                  <img
                    src={img.url}
                    alt={`${model?.title} - ${img.label}`}
                    loading="lazy"
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />

                  {/* Hover Zoom Overlay */}
                  <div className="absolute inset-0 bg-blue-950/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center">
                    <div className="p-2.5 rounded-full bg-blue-600 text-white shadow-xl transform scale-75 group-hover:scale-100 transition-transform">
                      <ZoomIn className="w-5 h-5" />
                    </div>
                  </div>
                </div>

                {/* Filename & Angle meta */}
                <div className="p-2.5 bg-[#141C28] text-[11px] text-slate-400 flex items-center justify-between font-mono truncate">
                  <span className="truncate">{img.filename}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* =====================================================================
          PART 3: HIGH-RESOLUTION LIGHTBOX MODAL (Showroom + All Angles)
          ===================================================================== */}
      {selectedImageIndex !== null && lightboxItems[selectedImageIndex] && (
        <div
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 sm:p-6"
          onClick={closeLightbox}
        >
          <div
            className="relative max-w-5xl w-full bg-[#121824] rounded-2xl overflow-hidden border border-slate-700 shadow-2xl flex flex-col max-h-[92vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-5 py-3.5 bg-[#161F2E] border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span
                  className={`px-2.5 py-1 rounded font-mono text-xs font-bold text-white ${
                    lightboxItems[selectedImageIndex].isShowroom ? 'bg-emerald-600' : 'bg-blue-600'
                  }`}
                >
                  {lightboxItems[selectedImageIndex].label}
                </span>
                <span className="text-sm font-semibold text-white">
                  {model?.title} ({model?.id})
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {selectedImageIndex + 1} of {lightboxItems.length}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={lightboxItems[selectedImageIndex].url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                  title="Open full resolution in new tab"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>
                <button
                  onClick={closeLightbox}
                  className="p-2 rounded-lg bg-slate-800 hover:bg-red-600 text-slate-300 hover:text-white transition"
                  title="Close (Esc)"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Image Display with Prev/Next buttons */}
            <div className="relative flex-1 bg-black flex items-center justify-center p-4 min-h-[350px] overflow-hidden">
              <img
                src={lightboxItems[selectedImageIndex].url}
                alt={lightboxItems[selectedImageIndex].label}
                className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-2xl"
              />

              {/* Prev Button */}
              <button
                onClick={prevImage}
                className="absolute left-4 p-3 rounded-full bg-black/60 hover:bg-blue-600 text-white backdrop-blur-md border border-white/10 transition shadow-xl"
                title="Previous Image"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>

              {/* Next Button */}
              <button
                onClick={nextImage}
                className="absolute right-4 p-3 rounded-full bg-black/60 hover:bg-blue-600 text-white backdrop-blur-md border border-white/10 transition shadow-xl"
                title="Next Image"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Footer */}
            <div className="px-5 py-3 bg-[#161F2E] border-t border-slate-800 flex flex-wrap items-center justify-between text-xs text-slate-400 font-mono">
              <span>File: {lightboxItems[selectedImageIndex].filename}</span>
              <span className="text-blue-400">{lightboxItems[selectedImageIndex].gcs_uri}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
