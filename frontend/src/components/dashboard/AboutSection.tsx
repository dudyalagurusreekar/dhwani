"use client";

import React from "react";
import { Shield, Fingerprint, Zap, Lock, ArrowUpRight, Cpu } from "lucide-react";

export default function AboutSection() {
  const highlights = [
    {
      title: "Glottal Pulse Biometrics",
      desc: "Detects human physiological vocal tract vibration vs. diffusion model artifacts.",
      icon: Fingerprint,
      accent: "text-[#22D3EE]",
    },
    {
      title: "Sub-15ms Edge Latency",
      desc: "Runs inline during phone and WebRTC calls without perceptible conversational delay.",
      icon: Zap,
      accent: "text-[#8B5CFF]",
    },
    {
      title: "Zero-Trust Protocol",
      desc: "Every voice interaction is continuously authenticated; trust is never assumed.",
      icon: Lock,
      accent: "text-[#D946EF]",
    },
  ];

  return (
    <section className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 py-16 sm:py-24">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
        {/* Left Column: Glass Visual Graphic Panel */}
        <div className="lg:col-span-5 relative group">
          <div className="relative rounded-[24px] bg-[rgba(20,10,40,0.65)] border border-[rgba(160,100,255,0.22)] backdrop-blur-[20px] p-6 sm:p-8 shadow-[0_20px_60px_rgba(0,0,0,0.45)] overflow-hidden">
            {/* Ambient inner glow */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-radial from-[#8B5CFF]/20 to-transparent rounded-full blur-[60px] pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-radial from-[#22D3EE]/15 to-transparent rounded-full blur-[60px] pointer-events-none" />

            <div className="relative z-10 flex flex-col justify-between h-full space-y-6">
              <div className="flex items-center justify-between">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#160B29] border border-[#8B5CFF]/30 text-[#C084FC] text-[11px] font-mono font-semibold">
                  <Cpu className="w-3.5 h-3.5 text-[#22D3EE]" />
                  NEURAL DISCRIMINATOR v2.4
                </div>
                <span className="text-[10px] font-mono text-[#777083]">48kHz TELEMETRY</span>
              </div>

              {/* Graphic Representation of Neural Voice Deconstruction */}
              <div className="p-5 rounded-2xl bg-[#080312]/80 border border-white/[0.05] space-y-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#B8B0C9] font-medium">Acoustic Glottal Pulse</span>
                  <span className="text-emerald-400 font-mono font-bold">NATURAL (99.8%)</span>
                </div>
                <div className="w-full bg-[#100820] h-2 rounded-full overflow-hidden p-0.5 border border-white/5">
                  <div className="bg-gradient-to-r from-[#22D3EE] to-emerald-400 h-full rounded-full w-[99.8%]" />
                </div>

                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-[#B8B0C9] font-medium">Vocoder Phase Artifacts</span>
                  <span className="text-[#777083] font-mono font-bold">0.02% (NONE)</span>
                </div>
                <div className="w-full bg-[#100820] h-2 rounded-full overflow-hidden p-0.5 border border-white/5">
                  <div className="bg-gradient-to-r from-red-500 to-[#D946EF] h-full rounded-full w-[2%]" />
                </div>

                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-[#B8B0C9] font-medium">Spectral Envelope Match</span>
                  <span className="text-[#C084FC] font-mono font-bold">VERIFIED</span>
                </div>
                <div className="w-full bg-[#100820] h-2 rounded-full overflow-hidden p-0.5 border border-white/5">
                  <div className="bg-gradient-to-r from-[#8B5CFF] to-[#C084FC] h-full rounded-full w-[96.4%]" />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-[#B8B0C9] font-mono pt-2 border-t border-white/[0.06]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Real-time voiceprint verified</span>
                </div>
                <span className="text-[#22D3EE] font-bold">11.8 ms</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Editorial Copy */}
        <div className="lg:col-span-7 space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#8B5CFF]/10 border border-[#8B5CFF]/25 text-[#C084FC] text-xs font-mono font-semibold tracking-wider uppercase">
            ABOUT ECHOSHIELD AI
          </div>

          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black text-[#F8F7FF] tracking-tight leading-[1.12]">
            AI-powered protection for authentic voices.
          </h2>

          <p className="text-base sm:text-lg text-[#B8B0C9] leading-relaxed max-w-2xl font-normal">
            EchoShield AI combines acoustic intelligence, synthetic speech detection and
            real-time risk analysis to protect telecom networks, executive communications,
            and financial institutions from deepfake voice impersonation attacks.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
            {highlights.map((item, idx) => {
              const Icon = item.icon;
              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-[rgba(20,10,40,0.45)] border border-[rgba(160,100,255,0.14)] space-y-2 hover:border-[#8B5CFF]/40 transition-colors"
                >
                  <Icon className={`w-5 h-5 ${item.accent}`} />
                  <h4 className="text-sm font-bold text-[#F8F7FF] tracking-wide">
                    {item.title}
                  </h4>
                  <p className="text-xs text-[#777083] leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
