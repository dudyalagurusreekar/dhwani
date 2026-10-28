"use client";

import React from "react";
import { Cpu, ShieldCheck, Activity, Lock, Smartphone, Radio, Sparkles } from "lucide-react";

export default function FeatureCards() {
  return (
    <section id="features" className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 py-16 sm:py-20">
      <div className="text-center max-w-2xl mx-auto mb-14">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#8B5CFF]/10 border border-[#8B5CFF]/25 text-[#C084FC] text-xs font-mono font-semibold mb-3">
          CYBERSECURITY CAPABILITIES
        </div>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black text-[#F8F7FF] tracking-tight">
          Built for Real-Time Voice Defense
        </h2>
        <p className="text-[#B8B0C9] text-sm sm:text-base mt-2">
          Enterprise-grade acoustic discrimination engine engineered for zero false-positive tolerance.
        </p>
      </div>

      {/* Asymmetric Glass Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Card 1 (7 cols): REAL-TIME SYNTHETIC DETECTION */}
        <div className="md:col-span-7 rounded-[24px] bg-[rgba(20,10,40,0.55)] border border-[rgba(160,100,255,0.18)] backdrop-blur-[18px] p-7 sm:p-9 shadow-[0_20px_60px_rgba(0,0,0,0.35)] hover:border-[#8B5CFF]/40 transition-all group flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-2xl bg-gradient-to-br from-[#8B5CFF]/20 to-[#22D3EE]/20 border border-[#8B5CFF]/35 text-[#22D3EE]">
                <Cpu className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono text-[#8B5CFF] font-semibold tracking-wider">
                SOTA NEURAL ENGINE
              </span>
            </div>

            <h3 className="text-xl sm:text-2xl font-bold text-[#F8F7FF] tracking-tight">
              Real-Time Synthetic Speech & Diffusion Isolation
            </h3>
            <p className="text-sm text-[#B8B0C9] leading-relaxed max-w-xl">
              Trained on multi-lingual deepfake datasets to immediately expose ElevenLabs,
              VALL-E, and open-source diffusion vocoders by isolating phase discontinuities in the 4kHz–8kHz bands.
            </p>
          </div>

          <div className="mt-8 pt-6 border-t border-white/[0.06] flex items-center gap-4 text-xs font-mono text-[#777083]">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <ShieldCheck className="w-4 h-4" /> RawNet3 + AASIST Models
            </span>
            <span>•</span>
            <span>&lt;15ms Response Time</span>
          </div>
        </div>

        {/* Card 2 (5 cols): DYNAMIC RISK SCORING */}
        <div className="md:col-span-5 rounded-[24px] bg-[rgba(20,10,40,0.55)] border border-[rgba(160,100,255,0.18)] backdrop-blur-[18px] p-7 sm:p-9 shadow-[0_20px_60px_rgba(0,0,0,0.35)] hover:border-[#22D3EE]/40 transition-all group flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-2xl bg-[#22D3EE]/10 border border-[#22D3EE]/30 text-[#22D3EE]">
                <Activity className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono text-[#22D3EE] font-semibold tracking-wider">
                CONTINUOUS SCORING
              </span>
            </div>

            <h3 className="text-xl sm:text-2xl font-bold text-[#F8F7FF] tracking-tight">
              Dynamic Impersonation Risk Scoring
            </h3>
            <p className="text-sm text-[#B8B0C9] leading-relaxed">
              Calculates conversational threat ratings frame-by-frame, escalating alerts only when
              microscopic vocal tract resonance diverges from physiological baselines.
            </p>
          </div>

          <div className="mt-8 pt-6 border-t border-white/[0.06] flex items-center gap-2 text-xs font-mono text-[#C084FC]">
            <span>Radial Threat Metric Integration</span>
          </div>
        </div>

        {/* Card 3 (5 cols): VOICE BIOMETRIC FORENSICS */}
        <div className="md:col-span-5 rounded-[24px] bg-[rgba(20,10,40,0.55)] border border-[rgba(160,100,255,0.18)] backdrop-blur-[18px] p-7 sm:p-9 shadow-[0_20px_60px_rgba(0,0,0,0.35)] hover:border-[#D946EF]/40 transition-all group flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-2xl bg-[#D946EF]/10 border border-[#D946EF]/30 text-[#D946EF]">
                <Radio className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono text-[#D946EF] font-semibold tracking-wider">
                ACOUSTIC FORENSICS
              </span>
            </div>

            <h3 className="text-xl sm:text-2xl font-bold text-[#F8F7FF] tracking-tight">
              Glottal Frequency & Harmonic Pulse Check
            </h3>
            <p className="text-sm text-[#B8B0C9] leading-relaxed">
              Analyzes vocal fold vibration dynamics and bio-acoustic spectral envelopes that generative
              vocoders cannot authentically synthesize.
            </p>
          </div>

          <div className="mt-8 pt-6 border-t border-white/[0.06] flex items-center gap-2 text-xs font-mono text-emerald-400">
            <span>Biological Pulse Verification Active</span>
          </div>
        </div>

        {/* Card 4 (7 cols): PRIVACY-FIRST ZERO-TRUST ARCHITECTURE */}
        <div className="md:col-span-7 rounded-[24px] bg-[rgba(20,10,40,0.55)] border border-[rgba(160,100,255,0.18)] backdrop-blur-[18px] p-7 sm:p-9 shadow-[0_20px_60px_rgba(0,0,0,0.35)] hover:border-[#8B5CFF]/40 transition-all group flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-2xl bg-[#8B5CFF]/10 border border-[#8B5CFF]/30 text-[#C084FC]">
                <Lock className="w-6 h-6" />
              </div>
              <span className="text-xs font-mono text-[#8B5CFF] font-semibold tracking-wider">
                EDGE ARCHITECTURE
              </span>
            </div>

            <h3 className="text-xl sm:text-2xl font-bold text-[#F8F7FF] tracking-tight">
              Privacy-First On-Device Mobile APK Guardian
            </h3>
            <p className="text-sm text-[#B8B0C9] leading-relaxed max-w-xl">
              Zero raw audio leaves client devices. Android APK runs quantized neural inference
              directly at the edge, transmitting only mathematical acoustic vectors over encrypted WebSockets.
            </p>
          </div>

          <div className="mt-8 pt-6 border-t border-white/[0.06] flex items-center gap-4 text-xs font-mono text-[#777083]">
            <span className="flex items-center gap-1.5 text-[#22D3EE]">
              <Smartphone className="w-4 h-4" /> Android APK Compatible
            </span>
            <span>•</span>
            <span>End-to-End Cryptographic Signatures</span>
          </div>
        </div>
      </div>
    </section>
  );
}
