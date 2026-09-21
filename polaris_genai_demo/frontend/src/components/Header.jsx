import React from 'react';
import { Store, ShieldCheck, ChevronDown, CheckCircle2 } from 'lucide-react';

export default function Header({
  selectedModel,
  totalModels,
  selectedDealer,
  dealers = [],
  onSelectDealer,
}) {
  return (
    <header className="border-b border-slate-800 bg-[#0E131C]/90 backdrop-blur-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Polaris Star Brand */}
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center shadow-lg shadow-blue-500/20 border border-blue-400/30 shrink-0">
            <svg viewBox="0 0 24 24" className="w-6 h-6 text-white fill-current">
              <polygon points="12,2 14.5,9.5 22,12 14.5,14.5 12,22 9.5,14.5 2,12 9.5,9.5" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black tracking-wider text-white uppercase font-sans">
                POLARIS <span className="text-blue-500 font-bold">360° STUDIO</span>
              </h1>
              <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider bg-blue-950/80 text-blue-400 border border-blue-800/60 rounded-full">
                GenAI Veo + Nano Banana
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Interactive 360° Rotations, CGI Perspectives & Dealer Showroom Staging
            </p>
          </div>
        </div>

        {/* Dealer Dropdown & System Badges */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          {/* Dealer Dropdown in Header */}
          {dealers.length > 0 && onSelectDealer && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900/90 border border-slate-700/80 rounded-xl shadow-inner">
              <Store className="w-4 h-4 text-blue-400 shrink-0" />
              <span className="text-slate-400 font-medium text-[11px] hidden sm:inline">Dealer:</span>
              <div className="relative">
                <select
                  value={selectedDealer?.id || ''}
                  onChange={(e) => onSelectDealer(e.target.value)}
                  className="appearance-none bg-transparent text-white font-mono text-xs font-bold pr-5 focus:outline-none cursor-pointer"
                >
                  {dealers.map((d) => (
                    <option key={d.id} value={d.id} className="bg-[#18202C] text-white py-1">
                      {d.folder_name} {d.has_background ? '✓' : '⚠️'}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 pointer-events-none absolute right-0 top-1/2 -translate-y-1/2" />
              </div>
            </div>
          )}

          {/* GCS Bucket Badge */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900/90 border border-slate-800 rounded-lg text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-mono text-[11px] text-slate-400">GCS:</span>
            <span className="font-mono text-[11px] text-emerald-400 font-semibold">polaris-demo-files</span>
          </div>

          {/* Total Models Badge */}
          <div className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 bg-slate-900/90 border border-slate-800 rounded-lg text-slate-300">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-[11px] text-slate-300 font-medium">{totalModels} Models</span>
          </div>
        </div>
      </div>
    </header>
  );
}
