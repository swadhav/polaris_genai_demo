import React from 'react';
import { Store, ChevronDown, Check, AlertTriangle, CheckCircle2, Image as ImageIcon } from 'lucide-react';

export default function DealerSelector({
  dealers,
  selectedDealerId,
  onSelectDealer,
  selectedModel,
}) {
  const currentDealer = dealers.find((d) => d.id === selectedDealerId) || dealers[0];
  const modelId = selectedModel?.id;
  const hasShowroomImage = currentDealer?.generated_models?.includes(modelId);

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-xl">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Main Dropdown Section */}
        <div className="flex-1">
          <label
            htmlFor="dealer-selector-dropdown"
            className="block text-xs uppercase font-bold tracking-wider text-slate-400 mb-2 flex items-center gap-1.5"
          >
            <Store className="w-3.5 h-3.5 text-blue-400" />
            Select Dealer Showroom (GCS Bucket Folder):
          </label>

          <div className="relative">
            <select
              id="dealer-selector-dropdown"
              value={selectedDealerId}
              onChange={(e) => onSelectDealer(e.target.value)}
              className="w-full appearance-none bg-[#1A2232] hover:bg-[#202B3F] text-white font-mono text-sm sm:text-base font-semibold py-3 px-4 pr-10 rounded-xl border border-slate-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition cursor-pointer shadow-inner"
            >
              {dealers.map((dealer) => (
                <option key={dealer.id} value={dealer.id} className="bg-[#18202C] text-white py-2 font-mono">
                  {dealer.folder_name} — {dealer.name} {dealer.has_background ? '(Background Ready)' : '(Background Missing)'}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3.5 text-slate-400">
              <ChevronDown className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Selected Dealer Status Card */}
        {currentDealer && (
          <div className="lg:max-w-md w-full bg-[#182130]/90 border border-slate-700/60 rounded-xl p-3 sm:p-3.5 flex items-center justify-between gap-3 shadow-md">
            <div className="flex items-center gap-3 min-w-0">
              {currentDealer.logo_url ? (
                <div className="w-12 h-10 rounded-lg bg-white/10 p-1 border border-slate-700 flex items-center justify-center shrink-0 overflow-hidden">
                  <img
                    src={currentDealer.logo_url}
                    alt={currentDealer.name}
                    className="max-w-full max-h-full object-contain"
                  />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-lg bg-blue-900/40 border border-blue-500/30 flex items-center justify-center shrink-0">
                  <Store className="w-5 h-5 text-blue-400" />
                </div>
              )}
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-600/30 text-blue-300 border border-blue-500/30">
                    {currentDealer.folder_name}
                  </span>
                  {currentDealer.has_background ? (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-700/60 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Ready
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-400 border border-amber-700/60 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> No Background
                    </span>
                  )}
                </div>
                <div className="text-sm font-bold text-white truncate mt-0.5">
                  {currentDealer.name}
                </div>
              </div>
            </div>

            <div className="text-right shrink-0">
              <div className="text-xs font-medium">
                {hasShowroomImage ? (
                  <span className="text-emerald-400 flex items-center gap-1 justify-end">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Staged
                  </span>
                ) : (
                  <span className="text-slate-400 flex items-center gap-1 justify-end">
                    <ImageIcon className="w-3.5 h-3.5" /> Not Generated
                  </span>
                )}
              </div>
              <span className="text-[10px] text-slate-500 font-mono">
                {currentDealer.generated_models?.length || 0} Models Staged
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Quick Switch Dealer Pills */}
      <div className="mt-4 pt-3.5 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400 font-medium mr-1">Dealers in GCS Bucket:</span>
        {dealers.map((dealer) => {
          const isSelected = dealer.id === selectedDealerId;
          return (
            <button
              key={dealer.id}
              onClick={() => onSelectDealer(dealer.id)}
              className={`px-3 py-1.5 rounded-lg font-mono text-xs font-semibold flex items-center gap-1.5 transition-all duration-150 ${
                isSelected
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 border border-blue-400 scale-[1.02]'
                  : 'bg-[#1A2232] text-slate-300 hover:bg-[#232F45] hover:text-white border border-slate-700/60'
              }`}
            >
              {isSelected && <Check className="w-3.5 h-3.5 text-white" />}
              <span>{dealer.folder_name}</span>
              {dealer.has_background ? (
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400/80"></span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
