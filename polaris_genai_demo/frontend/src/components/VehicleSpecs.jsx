import React from 'react';
import { Gauge, Users, Palette, Shield, Database, Film, FileImage, Cpu } from 'lucide-react';

export default function VehicleSpecs({ model }) {
  if (!model) return null;

  const specCards = [
    {
      label: 'Model ID (Folder)',
      value: model.id,
      icon: Cpu,
      isMono: true,
      color: 'text-blue-400',
    },
    {
      label: 'Vehicle Segment',
      value: model.segment,
      icon: Shield,
      isMono: false,
      color: 'text-indigo-400',
    },
    {
      label: 'Exterior Finish',
      value: model.color,
      icon: Palette,
      isMono: false,
      color: 'text-emerald-400',
    },
    {
      label: 'Engine / Output',
      value: model.hp,
      icon: Gauge,
      isMono: true,
      color: 'text-amber-400',
    },
    {
      label: 'Seating Capacity',
      value: model.seating,
      icon: Users,
      isMono: false,
      color: 'text-sky-400',
    },
    {
      label: '360° Video Options',
      value: model.outdoor_video
        ? 'Studio & Outdoor 360°'
        : (model.video?.filename || 'sample_360_rotation.mp4'),
      icon: Film,
      isMono: !model.outdoor_video,
      color: 'text-cyan-400',
    },
    {
      label: 'Static CGI Angles',
      value: `${model.images?.length || 0} Perspective Views`,
      icon: FileImage,
      isMono: false,
      color: 'text-purple-400',
    },
    {
      label: 'GCS Bucket Path',
      value: `gs://polaris-demo-files/models/${model.id}/`,
      icon: Database,
      isMono: true,
      color: 'text-slate-300',
    },
  ];

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-2xl p-5 shadow-xl">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-800">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
          Model Specifications & Digital Assets
        </h3>
        <span className="text-xs font-mono text-slate-500">• {model.title}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {specCards.map((spec, i) => {
          const Icon = spec.icon;
          return (
            <div
              key={i}
              className="bg-[#161F2E]/70 border border-slate-700/50 rounded-xl p-3 flex items-start gap-3 hover:border-slate-600 transition"
            >
              <div className="p-2 rounded-lg bg-slate-800/80 shrink-0">
                <Icon className={`w-4 h-4 ${spec.color}`} />
              </div>
              <div className="min-w-0 flex-1">
                <span className="text-[11px] uppercase font-semibold text-slate-400 block tracking-wider">
                  {spec.label}
                </span>
                <span
                  className={`text-xs font-bold text-white block truncate mt-0.5 ${
                    spec.isMono ? 'font-mono text-blue-300' : ''
                  }`}
                  title={spec.value}
                >
                  {spec.value}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
