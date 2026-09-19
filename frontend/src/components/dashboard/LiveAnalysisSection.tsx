"use client";

import React, { useState } from "react";
import { Radio, ShieldAlert, CheckCircle2, AlertTriangle, Activity, Mic, Volume2, UploadCloud, Play, Pause, Layers } from "lucide-react";
import WaveformVisualizer from "@/components/brand/WaveformVisualizer";

interface LiveAnalysisSectionProps {
  onTriggerUpload?: () => void;
  activeSampleName?: string;
  threatLevel?: "authentic" | "warning" | "deepfake";
  confidenceScore?: number;
  isPlaying?: boolean;
  onTogglePlay?: () => void;
}

export default function LiveAnalysisSection({
  onTriggerUpload,
  activeSampleName = "executive_briefing_raw.wav",
  threatLevel = "authentic",
  confidenceScore = 98.7,
  isPlaying = true,
  onTogglePlay,
}: LiveAnalysisSectionProps) {
  // SVG Radial Gauge math
  const riskScore = threatLevel === "authentic" ? 18 : threatLevel === "warning" ? 64 : 94;
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (riskScore / 100) * circumference;

  const getRiskLabel = () => {
    if (riskScore < 30) return { text: "LOW RISK", color: "text-emerald-400", border: "border-emerald-500/30", bg: "bg-emerald-500/10" };
    if (riskScore < 75) return { text: "ELEVATED", color: "text-amber-400", border: "border-amber-500/30", bg: "bg-amber-500/10" };
    return { text: "CRITICAL", color: "text-red-400", border: "border-red-500/30", bg: "bg-red-500/10" };
  };

  const riskInfo = getRiskLabel();

  return (
    <section id="live-analysis" className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 py-16 sm:py-20">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#22D3EE]/10 border border-[#22D3EE]/25 text-[#22D3EE] text-xs font-mono font-semibold mb-3">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            REAL-TIME THREAT INTELLIGENCE
          </div>
          <h2 className="text-3xl sm:text-4xl font-black text-[#F8F7FF] tracking-tight">
            Live Voice Intelligence & Acoustic Analysis
          </h2>
          <p className="text-[#B8B0C9] text-sm sm:text-base mt-2 max-w-2xl">
            Continuous forensic deconstruction of voice streams to isolate synthetic vocoders,
            detect cloned voices, and evaluate impersonation threat levels.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {onTriggerUpload && (
            <button
              type="button"
              onClick={onTriggerUpload}
              className="px-4 py-2 rounded-xl bg-[rgba(20,10,40,0.65)] hover:bg-[rgba(28,13,50,0.8)] border border-[rgba(160,100,255,0.25)] hover:border-[#22D3EE]/50 text-xs font-medium text-[#F8F7FF] flex items-center gap-2 transition cursor-pointer shadow-lg"
            >
              <UploadCloud className="w-4 h-4 text-[#22D3EE]" />
              <span>Upload Test Audio</span>
            </button>
          )}

          {onTogglePlay && (
            <button
              type="button"
              onClick={onTogglePlay}
              className="px-4 py-2 rounded-xl bg-[rgba(20,10,40,0.65)] hover:bg-[rgba(28,13,50,0.8)] border border-[rgba(160,100,255,0.25)] text-xs font-medium text-[#F8F7FF] flex items-center gap-2 transition cursor-pointer shadow-lg"
            >
              {isPlaying ? (
                <>
                  <Pause className="w-4 h-4 text-[#C084FC]" />
                  <span>Pause Stream</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 text-[#C084FC] fill-[#C084FC]" />
                  <span>Resume Stream</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Two Column Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        {/* Left Column (7 cols): Large Live Waveform & Spectrum Panel */}
        <div className="lg:col-span-7 flex flex-col justify-between rounded-[24px] bg-[rgba(20,10,40,0.6)] border border-[rgba(160,100,255,0.2)] backdrop-blur-[20px] p-6 sm:p-8 shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
          {/* Header Bar */}
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-4">
            <div className="flex items-center gap-3">
              <span className="flex h-2.5 w-2.5 rounded-full bg-[#22D3EE] animate-pulse" />
              <div>
                <div className="text-xs font-mono font-bold text-[#F8F7FF] tracking-wider uppercase">
                  ACTIVE STREAM: {activeSampleName}
                </div>
                <div className="text-[11px] text-[#777083] font-mono">
                  48kHz 24-bit PCM • Ingestion Gateway #1
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="px-2.5 py-1 rounded-md bg-[#160B29] border border-white/5 text-[#22D3EE] font-semibold">
                LIVE
              </span>
              <Mic className="w-3.5 h-3.5 text-[#C084FC]" />
            </div>
          </div>

          {/* Large Waveform Canvas Display */}
          <div className="py-8 my-auto">
            <WaveformVisualizer isAnalyzing={isPlaying} />
          </div>

          {/* Bottom Telemetry Strip */}
          <div className="pt-4 border-t border-white/[0.06] grid grid-cols-3 gap-4 text-center">
            <div className="p-2.5 rounded-xl bg-[#080312]/60 border border-white/5">
              <div className="text-[10px] font-mono text-[#777083] uppercase">Sampling Rate</div>
              <div className="text-xs sm:text-sm font-bold font-mono text-[#F8F7FF] mt-0.5">48,000 Hz</div>
            </div>
            <div className="p-2.5 rounded-xl bg-[#080312]/60 border border-white/5">
              <div className="text-[10px] font-mono text-[#777083] uppercase">Neural Latency</div>
              <div className="text-xs sm:text-sm font-bold font-mono text-[#22D3EE] mt-0.5">11.4 ms</div>
            </div>
            <div className="p-2.5 rounded-xl bg-[#080312]/60 border border-white/5">
              <div className="text-[10px] font-mono text-[#777083] uppercase">Acoustic Phase</div>
              <div className="text-xs sm:text-sm font-bold font-mono text-emerald-400 mt-0.5">Continuous (OK)</div>
            </div>
          </div>
        </div>

        {/* Right Column (5 cols): Risk Analysis & Radial Metric Panel */}
        <div className="lg:col-span-5 flex flex-col justify-between rounded-[24px] bg-[rgba(20,10,40,0.6)] border border-[rgba(160,100,255,0.2)] backdrop-blur-[20px] p-6 sm:p-8 shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-4">
            <h3 className="text-sm font-bold tracking-wider text-[#F8F7FF] font-mono uppercase">
              CURRENT RISK SCORE
            </h3>
            <span className={`text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full ${riskInfo.bg} ${riskInfo.color} ${riskInfo.border} border`}>
              {riskInfo.text}
            </span>
          </div>

          {/* Central Radial Gauge */}
          <div className="relative my-6 flex flex-col items-center justify-center">
            <div className="relative w-40 h-40 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 140 140">
                {/* Background track */}
                <circle
                  cx="70"
                  cy="70"
                  r={radius}
                  stroke="#1C0D32"
                  strokeWidth="10"
                  fill="transparent"
                />
                {/* Foreground animated value */}
                <circle
                  cx="70"
                  cy="70"
                  r={radius}
                  stroke={riskScore < 30 ? "#22C55E" : riskScore < 75 ? "#F59E0B" : "#EF4444"}
                  strokeWidth="10"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  fill="transparent"
                  className="transition-all duration-1000 ease-out"
                />
              </svg>

              {/* Central Value Display */}
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-3xl font-black text-[#F8F7FF] tracking-tight">
                  {riskScore}
                </span>
                <span className="text-[10px] font-mono uppercase text-[#777083]">
                  out of 100
                </span>
              </div>
            </div>

            <div className="mt-3 text-center">
              <div className="text-xs font-medium text-[#B8B0C9]">
                {threatLevel === "authentic"
                  ? "Authentic Glottal Biometrics Confirmed"
                  : threatLevel === "warning"
                  ? "Formant Frequency Anomalies Detected"
                  : "Critical Voice Clone Signature Identified"}
              </div>
            </div>
          </div>

          {/* Sub-Metrics Breakdown Bars */}
          <div className="space-y-3 pt-3 border-t border-white/[0.06]">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#B8B0C9]">Voice Authenticity</span>
                <span className="font-mono font-bold text-[#F8F7FF]">{confidenceScore}%</span>
              </div>
              <div className="w-full bg-[#100820] h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-[#22D3EE] to-emerald-400 h-full rounded-full transition-all duration-700"
                  style={{ width: `${confidenceScore}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#B8B0C9]">Synthetic Diffusion Pattern</span>
                <span className="font-mono font-bold text-[#C084FC]">
                  {threatLevel === "deepfake" ? "98.2%" : "1.8%"}
                </span>
              </div>
              <div className="w-full bg-[#100820] h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-[#8B5CFF] to-[#D946EF] h-full rounded-full transition-all duration-700"
                  style={{ width: threatLevel === "deepfake" ? "98.2%" : "2%" }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#B8B0C9]">Behavioral & Phase Anomaly</span>
                <span className="font-mono font-bold text-[#777083]">
                  {threatLevel === "warning" ? "62.4%" : "8.1%"}
                </span>
              </div>
              <div className="w-full bg-[#100820] h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-amber-400 h-full rounded-full transition-all duration-700"
                  style={{ width: threatLevel === "warning" ? "62.4%" : "8.1%" }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
