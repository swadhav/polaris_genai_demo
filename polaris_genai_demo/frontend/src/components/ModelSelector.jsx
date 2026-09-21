import React from 'react';
import { Layers, ChevronDown, Check, Car, Palette } from 'lucide-react';

export default function ModelSelector({ models, selectedModelId, onSelectModel }) {
  const currentModel = models.find((m) => m.id === selectedModelId) || models[0];

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-xl">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Main Dropdown Section */}
        <div className="flex-1">
          <label
            htmlFor="model-selector-dropdown"
            className="block text-xs uppercase font-bold tracking-wider text-slate-400 mb-2 flex items-center gap-1.5"
          >
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            Select Polaris Model by ID:
          </label>

          <div className="relative">
            <select
              id="model-selector-dropdown"
              value={selectedModelId}
              onChange={(e) => onSelectModel(e.target.value)}
              className="w-full appearance-none bg-[#1A2232] hover:bg-[#202B3F] text-white font-mono text-sm sm:text-base font-semibold py-3 px-4 pr-10 rounded-xl border border-slate-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition cursor-pointer shadow-inner"
            >
              {models.map((model) => (
                <option key={model.id} value={model.id} className="bg-[#18202C] text-white py-2 font-mono">
                  {model.id} — {model.title} ({model.color})
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3.5 text-slate-400">
              <ChevronDown className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Selected Model Highlight Card */}
        {currentModel && (
          <div className="lg:max-w-md w-full bg-[#182130]/90 border border-slate-700/60 rounded-xl p-3 sm:p-3.5 flex items-center justify-between gap-3 shadow-md">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-blue-900/40 border border-blue-500/30 flex items-center justify-center shrink-0">
                <Car className="w-5 h-5 text-blue-400" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-600/30 text-blue-300 border border-blue-500/30">
                    {currentModel.id}
                  </span>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide truncate">
                    {currentModel.badge}
                  </span>
                </div>
                <div className="text-sm font-bold text-white truncate mt-0.5">
                  {currentModel.title}
                </div>
              </div>
            </div>

            <div className="text-right shrink-0">
              <div className="flex items-center gap-1.5 justify-end text-xs text-slate-300">
                <Palette className="w-3.5 h-3.5 text-blue-400" />
                <span className="font-medium text-slate-200">{currentModel.color}</span>
              </div>
              <span className="text-[11px] text-slate-400 font-mono">{currentModel.segment}</span>
            </div>
          </div>
        )}
      </div>

      {/* Model ID Quick Selector Buttons */}
      <div className="mt-4 pt-3.5 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400 font-medium mr-1">Quick Switch:</span>
        {models.map((model) => {
          const isSelected = model.id === selectedModelId;
          return (
            <button
              key={model.id}
              onClick={() => onSelectModel(model.id)}
              className={`px-3 py-1.5 rounded-lg font-mono text-xs font-semibold flex items-center gap-1.5 transition-all duration-150 ${
                isSelected
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 border border-blue-400 scale-[1.02]'
                  : 'bg-[#1A2232] text-slate-300 hover:bg-[#232F45] hover:text-white border border-slate-700/60'
              }`}
            >
              {isSelected && <Check className="w-3.5 h-3.5 text-white" />}
              {model.id}
            </button>
          );
        })}
      </div>
    </div>
  );
}
