"use client";

import React from "react";
import { Sparkles, ArrowRight, ShieldCheck, Download, Smartphone } from "lucide-react";

interface CtaSectionProps {
  onOpenConnectModal?: () => void;
  onTriggerUpload?: () => void;
}

export default function CtaSection({
  onOpenConnectModal,
  onTriggerUpload,
}: CtaSectionProps) {
  return (
    <section className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 py-16 sm:py-24">
      <div className="relative rounded-[28px] bg-gradient-to-b from-[#160B29] to-[#0A0416] border border-[#8B5CFF]/30 p-8 sm:p-14 text-center overflow-hidden shadow-[0_24px_80px_rgba(0,0,0,0.6),0_0_50px_rgba(139,92,255,0.15)]">
        {/* Ambient background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-radial from-[#8B5CFF]/25 via-[#22D3EE]/10 to-transparent rounded-full blur-[90px] pointer-events-none" />

        <div className="relative z-10 max-w-3xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#8B5CFF]/15 border border-[#8B5CFF]/30 text-[#C084FC] text-xs font-mono font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-[#22D3EE]" />
            ENTERPRISE & HACKATHON LIVE DEMO READY
          </div>

          <h2 className="text-3xl sm:text-5xl font-black text-[#F8F7FF] tracking-tight leading-[1.1]">
            Ready to Protect Your Organization from Synthetic Voice Cloning?
          </h2>

          <p className="text-sm sm:text-base text-[#B8B0C9] max-w-xl mx-auto leading-relaxed">
            Deploy EchoShield AI across your SIP trunks, call center pipelines, and executive Android devices with zero infrastructure friction.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            {onTriggerUpload && (
              <button
                type="button"
                onClick={onTriggerUpload}
                className="px-7 py-3.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-[#8B5CFF] via-[#7C3CFF] to-[#D946EF] hover:brightness-110 shadow-[0_0_30px_rgba(139,92,255,0.45)] transition-all flex items-center gap-2 cursor-pointer"
              >
                <span>Upload Audio for Deepfake Scan</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}

            {onOpenConnectModal && (
              <button
                type="button"
                onClick={onOpenConnectModal}
                className="px-6 py-3.5 rounded-xl bg-[#100820] hover:bg-[#160B29] border border-[#8B5CFF]/35 text-sm font-medium text-[#F8F7FF] transition cursor-pointer flex items-center gap-2"
              >
                <Smartphone className="w-4 h-4 text-[#22D3EE]" />
                <span>Pair Mobile APK Guardian</span>
              </button>
            )}
          </div>

          <div className="pt-6 flex flex-wrap items-center justify-center gap-6 text-xs text-[#777083] font-mono">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <ShieldCheck className="w-4 h-4" /> Sub-15ms Detection
            </span>
            <span>•</span>
            <span>Zero Audio Data Retention</span>
            <span>•</span>
            <span>REST & WebSockets Compatible</span>
          </div>
        </div>
      </div>
    </section>
  );
}
