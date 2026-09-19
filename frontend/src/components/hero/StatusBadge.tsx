"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, ShieldAlert } from "lucide-react";

export type ThreatLevel = "authentic" | "warning" | "deepfake";

interface StatusBadgeProps {
  status?: ThreatLevel;
  confidence?: number;
  label?: string;
}

export default function StatusBadge({
  status = "authentic",
  confidence = 99.4,
  label,
}: StatusBadgeProps) {
  const configs = {
    authentic: {
      border: "border-[#10B981]/30",
      bg: "bg-[#10B981]/8",
      glow: "shadow-[0_0_18px_-3px_rgba(16,185,129,0.3)]",
      text: "text-[#10B981]",
      dot: "bg-[#10B981]",
      icon: CheckCircle2,
      defaultLabel: "Authentic Human Voiceprint",
    },
    warning: {
      border: "border-[#F59E0B]/30",
      bg: "bg-[#F59E0B]/8",
      glow: "shadow-[0_0_18px_-3px_rgba(245,158,11,0.3)]",
      text: "text-[#F59E0B]",
      dot: "bg-[#F59E0B]",
      icon: AlertTriangle,
      defaultLabel: "Acoustic Discontinuity Warning",
    },
    deepfake: {
      border: "border-[#EF4444]/30",
      bg: "bg-[#EF4444]/8",
      glow: "shadow-[0_0_18px_-3px_rgba(239,68,68,0.35)]",
      text: "text-[#EF4444]",
      dot: "bg-[#EF4444]",
      icon: ShieldAlert,
      defaultLabel: "Synthetic Voice Clone Detected",
    },
  };

  const current = configs[status];
  const Icon = current.icon;

  return (
    <div
      className={`inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border backdrop-blur-md transition-all duration-300 ${current.border} ${current.bg} ${current.glow}`}
    >
      <span className="relative flex h-2 w-2">
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${current.dot}`} />
        <span className={`relative inline-flex rounded-full h-2 w-2 ${current.dot}`} />
      </span>

      <Icon className={`w-3.5 h-3.5 ${current.text}`} />

      <span className={`text-xs font-semibold tracking-wide ${current.text}`}>
        {label || current.defaultLabel}
      </span>

      <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-white/10 text-white/90">
        {confidence}%
      </span>
    </div>
  );
}
