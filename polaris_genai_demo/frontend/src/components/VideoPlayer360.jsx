import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, RotateCw, Volume2, VolumeX, Maximize2, RefreshCw, CheckCircle, Video } from 'lucide-react';

export default function VideoPlayer360({ model }) {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(true);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [isLoading, setIsLoading] = useState(true);
  const [videoError, setVideoError] = useState(false);
  const [progress, setProgress] = useState(0);

  // When model changes, reload video and reset state
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
  }, [model.id]);

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
      {/* Top Bar / Model & File Identifier */}
      <div className="px-5 py-3.5 bg-[#161F2E] border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30">
            <RotateCw className="w-4 h-4 animate-spin" style={{ animationDuration: '6s' }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-bold tracking-wider text-white">
                360° Rotation Video
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800/60 font-semibold">
                8-Second Loop
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono mt-0.5">
              Target File: <span className="text-slate-200 font-bold">{model.video.filename}</span>
            </p>
          </div>
        </div>

        {/* GCS Bucket Source Pill */}
        <div className="flex items-center gap-1.5 px-3 py-1 bg-[#0F1521] border border-slate-700/60 rounded-lg text-[11px] text-slate-300">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
          <span className="font-mono text-slate-400">Source:</span>
          <span className="font-mono text-blue-300 truncate max-w-[260px] sm:max-w-md">
            {model.video.gcs_uri}
          </span>
        </div>
      </div>

      {/* Main Video Viewport */}
      <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden group">
        {/* Loading Spinner */}
        {isLoading && !videoError && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm text-slate-300">
            <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mb-2" />
            <span className="text-xs font-medium tracking-wide">Streaming 360° video from GCS...</span>
          </div>
        )}

        {/* Video Error Message */}
        {videoError && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-red-950/40 text-red-300 p-6 text-center">
            <p className="text-sm font-semibold mb-2">Unable to load 360 rotation video</p>
            <p className="text-xs text-red-400 mb-4 font-mono">{model.video.gcs_uri}</p>
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
          ref={videoRef}
          src={model.video.url}
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

        {/* 360° Overlay Stamp */}
        <div className="absolute top-4 left-4 z-10 pointer-events-none flex items-center gap-2 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 text-white shadow-lg">
          <RotateCw className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-[11px] font-bold tracking-wider uppercase">360° View</span>
        </div>

        {/* Vehicle Badge Overlay Stamp */}
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
          <div className="w-16 h-16 rounded-full bg-blue-600/90 text-white flex items-center justify-center shadow-2xl pl-1 backdrop-blur-md border border-white/20">
            <Play className="w-8 h-8 fill-current" />
          </div>
        </div>

        {/* Timeline Scrub Bar */}
        <div className="absolute bottom-0 inset-x-0 h-1.5 bg-slate-800/80 cursor-pointer">
          <div
            className="h-full bg-gradient-to-r from-blue-600 to-cyan-400 transition-all duration-75"
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
            className="p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white transition shadow-md shadow-blue-600/20 active:scale-95"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current pl-0.5" />}
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
            {isMuted ? <VolumeX className="w-4 h-4 text-slate-400" /> : <Volume2 className="w-4 h-4 text-blue-400" />}
          </button>

          {/* Speed Presets */}
          <div className="flex items-center bg-[#1C2534] border border-slate-700/60 rounded-xl p-1 gap-1">
            {[0.5, 1.0, 1.5, 2.0].map((spd) => (
              <button
                key={spd}
                onClick={() => handleSpeedChange(spd)}
                className={`px-2 py-1 text-xs font-mono font-semibold rounded-lg transition ${
                  playbackSpeed === spd
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#273449]'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <span className="text-[11px] font-mono text-slate-400 block">Single Active Video:</span>
            <span className="text-xs font-mono font-bold text-emerald-400 flex items-center gap-1 justify-end">
              <CheckCircle className="w-3.5 h-3.5" /> sample_360_rotation.mp4
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
