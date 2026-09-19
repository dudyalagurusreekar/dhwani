"use client";

import React from "react";
import DhwaniSphere from "@/components/hero/DhwaniSphere";
import {
  Sparkles,
  ArrowRight,
  Shield,
  Activity,
  Cpu,
  Radio,
  Zap,
  UploadCloud,
  Smartphone,
  CheckCircle2,
  Lock,
  ShieldCheck,
} from "lucide-react";


interface HeroDashboardProps {
  onTriggerUpload: () => void;
  onOpenConnectModal: () => void;
  isAnalyzingUpload?: boolean;
  connectedModelName?: string | null;
  confidenceScore?: number;
  threatLevel?: "authentic" | "warning" | "deepfake";
}

export default function HeroDashboard({
  onTriggerUpload,
  onOpenConnectModal,
  isAnalyzingUpload = false,
  connectedModelName = null,
  confidenceScore = 98.7,
  threatLevel = "authentic",
}: HeroDashboardProps) {
  return (
    <section
      id="dashboard"
      className="relative w-full max-w-[1400px] mx-auto pt-28 sm:pt-32 pb-12 px-4 sm:px-8 min-h-[88vh] flex flex-col items-center"
    >
      {/* ════════════════════════════════════════════════════════
          ATMOSPHERIC RADIAL LIGHTING — Soft, controlled
          ════════════════════════════════════════════════════════ */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-[55%] w-[700px] sm:w-[900px] h-[500px] sm:h-[700px] bg-radial from-[#8B5CFF]/14 via-[#7C3CFF]/6 to-transparent rounded-full blur-[140px] pointer-events-none -z-10" />
      <div className="absolute top-[30%] left-[15%] w-[350px] h-[350px] bg-radial from-[#22D3EE]/8 to-transparent rounded-full blur-[110px] pointer-events-none -z-10" />
      <div className="absolute top-[40%] right-[10%] w-[280px] h-[280px] bg-radial from-[#D946EF]/7 to-transparent rounded-full blur-[100px] pointer-events-none -z-10" />

      {/* ════════════════════════════════════════════════════════
          WATERMARK BACKGROUND TYPOGRAPHY
          Ultra-faint, creates cinematic depth
          ════════════════════════════════════════════════════════ */}
      <div className="absolute top-[42%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-full text-center pointer-events-none select-none -z-0 overflow-hidden">
        <span className="text-[80px] sm:text-[130px] md:text-[180px] lg:text-[220px] font-black tracking-[0.15em] text-white/[0.025] uppercase leading-none font-sans">
          DHWANI
        </span>
      </div>

      {/* ════════════════════════════════════════════════════════
          MAIN HERO LAYOUT: Typography LEFT + Sphere CENTER/RIGHT
          Premium editorial two-column split
          ════════════════════════════════════════════════════════ */}
      <div className="relative z-10 w-full flex flex-col lg:flex-row items-center gap-8 lg:gap-4 mt-4">

        {/* ─── LEFT COLUMN: Editorial Typography (55% width) ─── */}
        <div className="flex-1 flex flex-col items-center lg:items-start text-center lg:text-left space-y-6 lg:pr-8 xl:pr-12">

          {/* Eyebrow Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[rgba(20,10,40,0.75)] border border-[rgba(160,100,255,0.28)] backdrop-blur-[16px] shadow-[0_4px_20px_rgba(0,0,0,0.45)]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE] animate-pulse" />
            <span className="text-[11px] font-mono font-bold tracking-widest text-[#F8F7FF] uppercase">
              AI VOICE SECURITY PLATFORM · v2.4
            </span>
          </div>

          {/* Main Headline — Controlled scale */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-[62px] xl:text-[68px] font-black tracking-tight text-[#F8F7FF] leading-[1.05]">
            Expose Synthetic<br />
            Voices.{" "}
            <span className="text-gradient-purple-magenta">
              Protect Real
              <br className="hidden sm:block" /> Conversations.
            </span>
          </h1>

          {/* Supporting Text */}
          <p className="max-w-lg text-sm sm:text-base text-[#B8B0C9] font-normal leading-relaxed">
            EchoShield AI continuously analyzes voice interactions to detect
            synthetic speech, assess impersonation risk, and trigger safer
            verification in under 15ms.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-3 pt-1">
            {/* Primary CTA */}
            <a
              href="#live-analysis"
              className="h-[48px] px-6 rounded-[14px] font-semibold text-sm text-white bg-gradient-to-r from-[#8B5CFF] via-[#7C3CFF] to-[#D946EF] hover:brightness-110 shadow-[0_0_28px_rgba(139,92,255,0.4)] hover:shadow-[0_0_40px_rgba(217,70,239,0.5)] transition-all duration-300 flex items-center gap-2 group cursor-pointer"
            >
              <span>START LIVE ANALYSIS</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </a>

            {/* Secondary CTA */}
            <a
              href="#threat-intelligence"
              className="h-[48px] px-5 rounded-[14px] font-medium text-sm text-[#F8F7FF] bg-[rgba(20,10,40,0.65)] hover:bg-[rgba(28,13,50,0.85)] border border-[rgba(160,100,255,0.25)] hover:border-[#8B5CFF]/60 backdrop-blur-[14px] shadow-lg transition-all duration-300 flex items-center gap-2 cursor-pointer"
            >
              <Shield className="w-4 h-4 text-[#22D3EE]" />
              <span>VIEW THREAT CENTER</span>
            </a>
          </div>

          {/* Secondary Action Row */}
          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-2.5">
            <button
              type="button"
              onClick={onTriggerUpload}
              disabled={isAnalyzingUpload}
              className="h-[40px] px-4 rounded-xl font-medium text-xs text-[#B8B0C9] hover:text-[#F8F7FF] bg-[rgba(20,10,40,0.5)] hover:bg-[rgba(28,13,50,0.7)] border border-white/10 hover:border-white/20 transition cursor-pointer flex items-center gap-2"
            >
              <UploadCloud className="w-3.5 h-3.5 text-[#22D3EE]" />
              <span>{isAnalyzingUpload ? "Analyzing..." : "Upload Audio"}</span>
            </button>

            <button
              type="button"
              onClick={onOpenConnectModal}
              className="h-[40px] px-4 rounded-xl font-medium text-xs text-[#C084FC] hover:text-[#F8F7FF] bg-[rgba(20,10,40,0.5)] hover:bg-[rgba(28,13,50,0.7)] border border-[#8B5CFF]/25 hover:border-[#8B5CFF]/50 transition cursor-pointer flex items-center gap-2"
            >
              <Smartphone className="w-3.5 h-3.5 text-[#C084FC]" />
              <span>{connectedModelName ? "Guardian Active" : "Connect APK"}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </button>
          </div>

          {/* Trust Badges Row */}
          <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4 pt-2 text-[11px] text-[#777083] font-mono">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <ShieldCheck className="w-3.5 h-3.5" /> &lt;15ms Response
            </span>
            <span>•</span>
            <span>Zero Audio Retention</span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-[#C084FC]" /> 98.7% Accuracy
            </span>
          </div>
        </div>

        {/* ─── RIGHT COLUMN: 3D Sphere + Floating Cards ─── */}
        <div className="relative flex-shrink-0 w-[340px] sm:w-[420px] lg:w-[440px] xl:w-[500px] h-[340px] sm:h-[420px] lg:h-[440px] xl:h-[500px] flex items-center justify-center">

          {/* 3D Sphere — Contained, not overwhelming */}
          <div className="w-[260px] h-[260px] sm:w-[300px] sm:h-[300px] lg:w-[320px] lg:h-[320px] xl:w-[360px] xl:h-[360px] pointer-events-none flex items-center justify-center z-10">
            <DhwaniSphere className="w-full h-full" />
          </div>

          {/* ── FLOATING GLASS CARD: Top-Left — Live Audio Status */}
          <div className="absolute -left-4 sm:-left-8 top-[8%] z-20 pointer-events-auto animate-float-slow">
            <div className="flex items-center gap-3 p-3 sm:p-3.5 rounded-[16px] bg-[rgba(15,8,30,0.78)] border border-[rgba(160,100,255,0.25)] backdrop-blur-[20px] shadow-[0_16px_40px_rgba(0,0,0,0.55),0_0_20px_rgba(34,211,238,0.12)] w-[190px] sm:w-[210px]">
              <div className="w-8 h-8 rounded-xl bg-[#22D3EE]/12 border border-[#22D3EE]/25 flex items-center justify-center flex-shrink-0">
                <Radio className="w-4 h-4 text-[#22D3EE] animate-pulse" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold font-mono text-[#F8F7FF] tracking-wider uppercase">
                    LIVE STREAM
                  </span>
                  <span className="text-[8px] font-mono text-emerald-400 font-bold bg-emerald-500/10 px-1 py-0.5 rounded">
                    ACTIVE
                  </span>
                </div>
                <p className="text-[10px] text-[#777083] mt-0.5 truncate">
                  48kHz 24-bit PCM
                </p>
                {/* Mini waveform bars */}
                <div className="flex items-end gap-[3px] h-2.5 mt-1.5">
                  {[30, 80, 50, 100, 65, 90, 40, 75, 55, 85].map((h, i) => (
                    <span
                      key={i}
                      className="w-[3px] bg-gradient-to-t from-[#8B5CFF] to-[#22D3EE] rounded-full animate-pulse"
                      style={{
                        height: `${h}%`,
                        animationDelay: `${i * 90}ms`,
                        animationDuration: "1.1s",
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* ── FLOATING GLASS CARD: Top-Right — AI Detection Confidence */}
          <div className="absolute -right-4 sm:-right-8 top-[5%] z-20 pointer-events-auto animate-float-delayed">
            <div className="flex items-center gap-3 p-3 sm:p-3.5 rounded-[16px] bg-[rgba(15,8,30,0.78)] border border-[rgba(160,100,255,0.25)] backdrop-blur-[20px] shadow-[0_16px_40px_rgba(0,0,0,0.55),0_0_20px_rgba(139,92,255,0.15)] w-[168px] sm:w-[185px]">
              <div className="w-8 h-8 rounded-xl bg-[#8B5CFF]/12 border border-[#8B5CFF]/25 flex items-center justify-center flex-shrink-0">
                <Cpu className="w-4 h-4 text-[#C084FC]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[9px] font-mono font-bold text-[#777083] tracking-wider uppercase">
                  AI DETECTION
                </div>
                <div className="text-xl font-black text-[#F8F7FF] tracking-tight">
                  {confidenceScore}%
                </div>
                <div className="text-[9px] text-emerald-400 font-mono flex items-center gap-1 mt-0.5">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  <span>Authentic</span>
                </div>
              </div>
            </div>
          </div>

          {/* ── FLOATING GLASS CARD: Bottom-Right — Risk Score */}
          <div className="absolute -right-2 sm:-right-6 bottom-[8%] z-20 pointer-events-auto animate-float-slow" style={{ animationDelay: "0.8s" }}>
            <div className="flex items-center gap-2.5 p-3 sm:p-3.5 rounded-[16px] bg-[rgba(15,8,30,0.78)] border border-emerald-500/22 backdrop-blur-[20px] shadow-[0_16px_40px_rgba(0,0,0,0.55)] w-[155px] sm:w-[172px]">
              <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center flex-shrink-0">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono font-bold text-[#777083] uppercase">
                    RISK SCORE
                  </span>
                  <span className="text-[8px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-1 py-0.5 rounded">
                    LOW
                  </span>
                </div>
                <div className="text-lg font-black text-[#F8F7FF] tracking-tight">
                  18 <span className="text-[10px] font-mono text-[#777083]">/ 100</span>
                </div>
              </div>
            </div>
          </div>

          {/* ── FLOATING PILL: Bottom-Left — Analysis Latency */}
          <div className="absolute -left-2 sm:-left-4 bottom-[14%] z-20 pointer-events-auto animate-float-delayed" style={{ animationDelay: "1.2s" }}>
            <div className="flex items-center gap-2 px-3 py-2 rounded-full bg-[rgba(15,8,30,0.82)] border border-[#22D3EE]/22 backdrop-blur-[16px] text-[10px] font-mono text-[#F8F7FF] shadow-lg">
              <Zap className="w-3 h-3 text-[#22D3EE]" />
              <span className="font-bold text-[#22D3EE]">&lt;15ms</span>
              <span className="text-[#777083]">Neural Latency</span>
            </div>
          </div>

          {/* ── FLOATING PILL: Top-Center — System Active */}
          <div className="absolute left-1/2 -translate-x-1/2 top-[-8%] sm:top-[-5%] z-20 pointer-events-none">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/22 backdrop-blur-[14px] text-[10px] font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-semibold text-emerald-400 tracking-wide">NEURAL ENGINE ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════
          BOTTOM TEASER: Scroll indicator
          ════════════════════════════════════════════════════════ */}
      <div className="relative z-10 mt-10 sm:mt-12 flex flex-col items-center gap-2 opacity-50 hover:opacity-80 transition-opacity">
        <span className="text-[10px] font-mono text-[#777083] tracking-widest uppercase">
          Scroll to Explore
        </span>
        <div className="w-[1px] h-8 bg-gradient-to-b from-[#8B5CFF]/60 to-transparent" />
      </div>
    </section>
  );
}
