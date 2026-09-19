"use client";

import React from "react";
import { Shield, Cpu, Zap, ArrowUpRight } from "lucide-react";

export default function MetricsBar() {
  return (
    <div className="w-full max-w-5xl mx-auto mt-12 px-4">
      <div className="relative rounded-2xl bg-[#111827]/80 border border-[#1E293B] backdrop-blur-2xl p-4 sm:p-5 shadow-lg flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Metrics */}
        <div className="flex items-center gap-6 sm:gap-10 w-full md:w-auto justify-around md:justify-start">
          <div className="flex flex-col">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">125k</span>
              <span className="text-[#22D3EE] font-bold text-lg">+</span>
            </div>
            <span className="text-[11px] uppercase tracking-wider text-[#94A3B8] font-medium">Voices Verified</span>
          </div>

          <div className="flex items-center justify-center">
            <button
              type="button"
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#A855F7] to-[#7C3AED] hover:to-[#22D3EE] text-white font-semibold text-xs shadow-[var(--dhwani-glow-purple)] flex items-center gap-1.5 transition-all duration-300 group"
            >
              <span>Live Shield</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-[#22D3EE] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </button>
          </div>

          <div className="flex flex-col">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">99.4</span>
              <span className="text-[#A855F7] font-bold text-lg">%</span>
            </div>
            <span className="text-[11px] uppercase tracking-wider text-[#94A3B8] font-medium">Forensic Precision</span>
          </div>

          <div className="flex flex-col">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">&lt;15</span>
              <span className="text-[#22D3EE] font-bold text-lg">ms</span>
            </div>
            <span className="text-[11px] uppercase tracking-wider text-[#94A3B8] font-medium">Detection Latency</span>
          </div>
        </div>

        <div className="hidden md:block h-10 w-[1px] bg-[#1E293B]" />

        {/* Partners */}
        <div className="flex items-center gap-5 text-[#94A3B8] text-xs w-full md:w-auto justify-center">
          <span className="text-[#94A3B8]/60 font-medium uppercase text-[10px] tracking-widest">Protected by:</span>
          <div className="flex items-center gap-4 font-mono text-[#E2E8F0] text-[11px]">
            <span className="flex items-center gap-1 hover:text-[#22D3EE] transition cursor-default">
              <Shield className="w-3.5 h-3.5 text-[#22D3EE]" />VOICENET.IO
            </span>
            <span className="text-[#1E293B]">•</span>
            <span className="flex items-center gap-1 hover:text-[#A855F7] transition cursor-default">
              <Cpu className="w-3.5 h-3.5 text-[#A855F7]" />SPECTRA.AI
            </span>
            <span className="text-[#1E293B]">•</span>
            <span className="flex items-center gap-1 hover:text-[#10B981] transition cursor-default">
              <Zap className="w-3.5 h-3.5 text-[#10B981]" />DEEPGUARD
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
