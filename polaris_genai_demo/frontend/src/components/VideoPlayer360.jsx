import React, { useRef, useState, useEffect } from 'react';
import {
  Play,
  Pause,
  RotateCw,
  Volume2,
  VolumeX,
  Maximize2,
  RefreshCw,
  CheckCircle,
  Mountain,
  Sun,
  Video,
} from 'lucide-react';

export default function VideoPlayer360({ model }) {
  const videoRef = useRef(null);
  const [videoMode, setVideoMode] = useState('studio'); // 'studio' | 'outdoor'
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [isLoading, setIsLoading] = useState(true);
  const [videoError, setVideoError] = useState(false);
  const [progress, setProgress] = useState(0);

  const isOutdoor = videoMode === 'outdoor';

  const studioVideo = model.video || {
    filename: 'sample_360_rotation.mp4',
    url: `/api/models/${model.id}/video`,
    gcs_uri: `gs://polaris-demo-files/models/${model.id}/sample_360_rotation.mp4`,
  };

  const outdoorVideo = model.outdoor_video || {
    filename: 'outdoor_background_360.mp4',
    url: `/api/models/${model.id}/video?variant=outdoor`,
    gcs_uri: `gs://polaris-demo-files/models/${model.id}/outdoor_background_360.mp4`,
  };

  const currentVideo = isOutdoor ? outdoorVideo : studioVideo;

  // When model or video mode changes, reload video and reset state
  useEffect(() => {
    setIsLoading(true);
    setVideoError(false);
    setProgress(0);
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackSpeed;
      videoRef.current.load();
      videoRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false));
    }
  }, [model.id, videoMode]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const newMuted = !isMuted;
    videoRef.current.muted = newMuted;
    setIsMuted(newMuted);
  };

  const handleSpeedChange = (speed) => {
    if (!videoRef.current) return;
    videoRef.current.playbackRate = speed;
    setPlaybackSpeed(speed);
  };

  const handleRestart = () => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = 0;
    videoRef.current.play();
    setIsPlaying(true);
  };

  const handleFullscreen = () => {
    if (!videoRef.current) return;
    if (videoRef.current.requestFullscreen) {
      videoRef.current.requestFullscreen();
    }
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const current = videoRef.current.currentTime;
    const total = videoRef.current.duration;
    if (total > 0) {
      setProgress((current / total) * 100);
    }
  };

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col">
      {/* Top Bar / Model & File Identifier with Video Switcher */}
      <div className="px-5 py-3.5 bg-[#161F2E] border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Video Title & Target File */}
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-xl border transition-colors ${
              isOutdoor
                ? 'bg-emerald-600/20 text-emerald-400 border-emerald-500/30'
                : 'bg-blue-600/20 text-blue-400 border-blue-500/30'
            }`}
          >
            {isOutdoor ? (
              <Mountain className="w-4 h-4 text-emerald-400" />
            ) : (
              <RotateCw className="w-4 h-4 animate-spin text-blue-400" style={{ animationDuration: '6s' }} />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-bold tracking-wider text-white">
                {isOutdoor ? 'Outdoor Background 360° Video' : '360° Rotation Video'}
              </span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold border ${
                  isOutdoor
                    ? 'bg-emerald-950 text-emerald-400 border-emerald-800/60'
                    : 'bg-blue-950 text-blue-400 border-blue-800/60'
                }`}
              >
                {isOutdoor ? 'Scenic Landscape Loop' : '8-Second Loop'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono mt-0.5">
              Target File: <span className="text-slate-200 font-bold">{currentVideo.filename}</span>
            </p>
          </div>
        </div>

        {/* Center: Video Mode Switcher (Studio 360 vs Outdoor Background 360) */}
        <div className="flex items-center bg-[#0C121D] p-1 rounded-xl border border-slate-700/80 shadow-inner">
          <button
            type="button"
            onClick={() => setVideoMode('studio')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
              !isOutdoor
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
            title="Switch to Studio 360° Rotation Video"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span>Studio 360°</span>
          </button>
          <button
            type="button"
            onClick={() => setVideoMode('outdoor')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
              isOutdoor
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
            title="Switch to Outdoor Background 360° Video"
          >
            <Mountain className="w-3.5 h-3.5" />
            <span>Outdoor Background 360°</span>
          </button>
        </div>

        {/* Right: GCS Bucket Source Pill */}
        <div className="flex items-center gap-1.5 px-3 py-1 bg-[#0F1521] border border-slate-700/60 rounded-lg text-[11px] text-slate-300">
          <span
            className={`w-1.5 h-1.5 rounded-full ${isOutdoor ? 'bg-emerald-400' : 'bg-blue-400'}`}
          ></span>
          <span className="font-mono text-slate-400">Source:</span>
          <span
            className={`font-mono truncate max-w-[260px] sm:max-w-md ${
              isOutdoor ? 'text-emerald-300' : 'text-blue-300'
            }`}
          >
            {currentVideo.gcs_uri}
          </span>
        </div>
      </div>

      {/* Main Video Viewport */}
      <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden group">
        {/* Loading Spinner */}
        {isLoading && !videoError && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm text-slate-300">
            <RefreshCw
              className={`w-8 h-8 animate-spin mb-2 ${isOutdoor ? 'text-emerald-500' : 'text-blue-500'}`}
            />
            <span className="text-xs font-medium tracking-wide">
              Streaming {isOutdoor ? 'outdoor background' : '360° rotation'} video from GCS...
            </span>
          </div>
        )}

        {/* Video Error Message */}
        {videoError && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-red-950/40 text-red-300 p-6 text-center">
            <p className="text-sm font-semibold mb-2">
              Unable to load {isOutdoor ? 'outdoor background 360' : '360 rotation'} video
            </p>
            <p className="text-xs text-red-400 mb-4 font-mono">{currentVideo.gcs_uri}</p>
            <button
              onClick={handleRestart}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-semibold"
            >
              Retry
            </button>
          </div>
        )}

        {/* HTML5 Video Element */}
        <video
          key={currentVideo.url}
          ref={videoRef}
          src={currentVideo.url}
          autoPlay
          loop
          muted={isMuted}
          playsInline
          onCanPlay={() => setIsLoading(false)}
          onWaiting={() => setIsLoading(true)}
          onPlaying={() => setIsLoading(false)}
          onError={() => {
            setIsLoading(false);
            setVideoError(true);
          }}
          onTimeUpdate={handleTimeUpdate}
          className="w-full h-full object-contain cursor-pointer"
          onClick={togglePlay}
        />

        {/* Video Mode Overlay Stamp (Top-Left) */}
        <button
          onClick={() => setVideoMode(isOutdoor ? 'studio' : 'outdoor')}
          title={`Click to switch to ${isOutdoor ? 'Studio 360°' : 'Outdoor Background 360°'}`}
          className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-black/70 hover:bg-black/90 transition backdrop-blur-md px-3.5 py-1.5 rounded-full border border-white/10 text-white shadow-lg cursor-pointer"
        >
          {isOutdoor ? (
            <>
              <Mountain className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-[11px] font-bold tracking-wider uppercase text-emerald-300">
                Outdoor 360°
              </span>
            </>
          ) : (
            <>
              <RotateCw className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-[11px] font-bold tracking-wider uppercase text-blue-300">
                Studio 360°
              </span>
            </>
          )}
          <span className="text-[10px] text-slate-400 pl-1 border-l border-white/20">Switch</span>
        </button>

        {/* Floating Switcher Bar Overlay (Top-Center) */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 hidden md:flex items-center bg-black/80 backdrop-blur-md p-1 rounded-full border border-white/15 shadow-2xl">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setVideoMode('studio');
            }}
            className={`px-3 py-1 rounded-full text-[11px] font-semibold transition flex items-center gap-1.5 ${
              !isOutdoor
                ? 'bg-blue-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <RotateCw className="w-3 h-3" /> Studio
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setVideoMode('outdoor');
            }}
            className={`px-3 py-1 rounded-full text-[11px] font-semibold transition flex items-center gap-1.5 ${
              isOutdoor
                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Mountain className="w-3 h-3" /> Outdoor Background
          </button>
        </div>

        {/* Vehicle Badge Overlay Stamp (Top-Right) */}
        <div className="absolute top-4 right-4 z-10 pointer-events-none hidden sm:flex items-center gap-2 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 text-white shadow-lg">
          <span className="text-[11px] font-mono text-blue-400 font-bold">{model.id}</span>
          <span className="text-[11px] text-slate-300">{model.title}</span>
        </div>

        {/* Quick Click-to-Play Indicator */}
        <div
          onClick={togglePlay}
          className={`absolute inset-0 flex items-center justify-center pointer-events-none transition-opacity duration-200 ${
            isPlaying ? 'opacity-0' : 'opacity-100 bg-black/40'
          }`}
        >
          <div
            className={`w-16 h-16 rounded-full text-white flex items-center justify-center shadow-2xl pl-1 backdrop-blur-md border border-white/20 ${
              isOutdoor ? 'bg-emerald-600/90' : 'bg-blue-600/90'
            }`}
          >
            <Play className="w-8 h-8 fill-current" />
          </div>
        </div>

        {/* Timeline Scrub Bar */}
        <div className="absolute bottom-0 inset-x-0 h-1.5 bg-slate-800/80 cursor-pointer">
          <div
            className={`h-full transition-all duration-75 ${
              isOutdoor
                ? 'bg-gradient-to-r from-emerald-600 to-teal-400'
                : 'bg-gradient-to-r from-blue-600 to-cyan-400'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Video Control Bar */}
      <div className="p-4 bg-[#141B26] border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {/* Play / Pause */}
          <button
            onClick={togglePlay}
            className={`p-2.5 rounded-xl text-white transition shadow-md active:scale-95 ${
              isOutdoor
                ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20'
                : 'bg-blue-600 hover:bg-blue-500 shadow-blue-600/20'
            }`}
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4 fill-current" />
            ) : (
              <Play className="w-4 h-4 fill-current pl-0.5" />
            )}
          </button>

          {/* Restart */}
          <button
            onClick={handleRestart}
            className="p-2.5 rounded-xl bg-[#1C2534] hover:bg-[#253247] text-slate-300 hover:text-white transition border border-slate-700/60 active:scale-95"
            title="Restart 360° Loop"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {/* Mute Toggle */}
          <button
            onClick={toggleMute}
            className="p-2.5 rounded-xl bg-[#1C2534] hover:bg-[#253247] text-slate-300 hover:text-white transition border border-slate-700/60 active:scale-95"
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? (
              <VolumeX className="w-4 h-4 text-slate-400" />
            ) : (
              <Volume2 className={`w-4 h-4 ${isOutdoor ? 'text-emerald-400' : 'text-blue-400'}`} />
            )}
          </button>

          {/* Speed Presets */}
          <div className="flex items-center bg-[#1C2534] border border-slate-700/60 rounded-xl p-1 gap-1">
            {[0.5, 1.0, 1.5, 2.0].map((spd) => (
              <button
                key={spd}
                onClick={() => handleSpeedChange(spd)}
                className={`px-2 py-1 text-xs font-mono font-semibold rounded-lg transition ${
                  playbackSpeed === spd
                    ? isOutdoor
                      ? 'bg-emerald-600 text-white'
                      : 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#273449]'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>

          {/* Quick Toggle Switch in Control Bar */}
          <button
            type="button"
            onClick={() => setVideoMode(isOutdoor ? 'studio' : 'outdoor')}
            className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition border ${
              isOutdoor
                ? 'bg-emerald-950/60 border-emerald-600/50 text-emerald-300 hover:bg-emerald-900/60'
                : 'bg-blue-950/60 border-blue-600/50 text-blue-300 hover:bg-blue-900/60'
            }`}
            title={`Switch to ${isOutdoor ? 'Studio 360°' : 'Outdoor Background 360°'}`}
          >
            {isOutdoor ? (
              <Mountain className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <RotateCw className="w-3.5 h-3.5 text-blue-400" />
            )}
            <span className="hidden md:inline">
              Switch to {isOutdoor ? 'Studio 360°' : 'Outdoor Background'}
            </span>
            <span className="md:hidden">{isOutdoor ? 'Studio' : 'Outdoor'}</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          {/* Active Video Status */}
          <div className="text-right hidden sm:block">
            <span className="text-[11px] font-mono text-slate-400 block">Active Video Stream:</span>
            <span
              className={`text-xs font-mono font-bold flex items-center gap-1 justify-end ${
                isOutdoor ? 'text-emerald-400' : 'text-blue-400'
              }`}
            >
              <CheckCircle className="w-3.5 h-3.5" /> {currentVideo.filename}
            </span>
          </div>

          {/* Fullscreen */}
          <button
            onClick={handleFullscreen}
            className="p-2.5 rounded-xl bg-[#1C2534] hover:bg-[#253247] text-slate-300 hover:text-white transition border border-slate-700/60 active:scale-95"
            title="Fullscreen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
