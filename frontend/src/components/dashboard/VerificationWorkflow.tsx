"use client";

import React, { useState } from "react";
import { Mic, BarChart3, BellRing, UserCheck, ArrowRight, ShieldAlert, CheckCircle2, PhoneCall, KeyRound } from "lucide-react";

export default function VerificationWorkflow() {
  const [verificationState, setVerificationState] = useState<"idle" | "verifying" | "success" | "escalated">("idle");
  const [activeActionText, setActiveActionText] = useState("");

  const steps = [
    {
      step: "01",
      title: "DETECT",
      subtitle: "Continuous Ingestion",
      desc: "Microscopic voiceprints sampled every 10ms to capture vocoder phase anomalies and acoustic jitters.",
      icon: Mic,
      color: "text-[#22D3EE]",
      border: "border-[#22D3EE]/30",
    },
    {
      step: "02",
      title: "SCORE RISK",
      subtitle: "Neural Confidence",
      desc: "RawNet3 + AASIST deep neural classifiers benchmark formant stability against authentic biometrics.",
      icon: BarChart3,
      color: "text-[#8B5CFF]",
      border: "border-[#8B5CFF]/30",
    },
    {
      step: "03",
      title: "ALERT",
      subtitle: "Sub-Audible Flag",
      desc: "Impersonation risk threshold exceeded triggers zero-trust flags to caller and compliance consoles.",
      icon: BellRing,
      color: "text-[#D946EF]",
      border: "border-[#D946EF]/30",
    },
    {
      step: "04",
      title: "VERIFY",
      subtitle: "Multi-Factor Action",
      desc: "Triggers out-of-band biometric challenge, cryptographic token verification, or automated supervisor drop.",
      icon: UserCheck,
      color: "text-emerald-400",
      border: "border-emerald-500/30",
    },
  ];

  const handleAction = (type: "verify" | "callback" | "auth") => {
    setVerificationState("verifying");
    setTimeout(() => {
      if (type === "verify") {
        setVerificationState("success");
        setActiveActionText("Caller Verified via Cryptographic Out-Of-Band Challenge");
      } else if (type === "callback") {
        setVerificationState("success");
        setActiveActionText("Encrypted Callback Scheduled on Verified Device (+1-555-0198)");
      } else {
        setVerificationState("escalated");
        setActiveActionText("Biometric FIDO2 Challenge Dispatched to Mobile Guardian");
      }
    }, 900);
  };

  return (
    <section id="workflow" className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 py-16 sm:py-24">
      {/* Section Title */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#8B5CFF]/10 border border-[#8B5CFF]/25 text-[#C084FC] text-xs font-mono font-semibold mb-3">
          ZERO-TRUST DEFENSE ARCHITECTURE
        </div>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black text-[#F8F7FF] tracking-tight">
          Detect. Score Risk. Alert. Verify.
        </h2>
        <p className="text-[#B8B0C9] text-sm sm:text-base mt-3 leading-relaxed">
          EchoShield AI automates the complete synthetic voice defense chain from acoustic
          packet ingestion to multi-factor mitigation before fraud occurs.
        </p>
      </div>

      {/* 4-Step Horizontal Pipeline */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 lg:gap-6 relative">
        {steps.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="relative rounded-[22px] bg-[rgba(20,10,40,0.55)] border border-[rgba(160,100,255,0.18)] backdrop-blur-[18px] p-6 shadow-[0_15px_40px_rgba(0,0,0,0.3)] hover:border-[#8B5CFF]/40 transition-all group"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-2xl font-black font-mono text-[#777083] group-hover:text-[#F8F7FF] transition-colors">
                  {item.step}
                </span>
                <div className={`p-2.5 rounded-xl bg-[#160B29] border ${item.border}`}>
                  <Icon className={`w-4 h-4 ${item.color}`} />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="text-xs font-mono font-bold tracking-widest text-[#B8B0C9] uppercase">
                  {item.subtitle}
                </div>
                <h3 className="text-lg font-bold text-[#F8F7FF] tracking-wide">
                  {item.title}
                </h3>
                <p className="text-xs text-[#777083] leading-relaxed pt-1">
                  {item.desc}
                </p>
              </div>

              {/* Glowing Arrow between steps on desktop */}
              {idx < steps.length - 1 && (
                <div className="hidden md:block absolute -right-3 lg:-right-4 top-1/2 -translate-y-1/2 z-20 text-[#8B5CFF]/50 pointer-events-none">
                  <ArrowRight className="w-5 h-5" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Interactive Verification Panel Demonstration */}
      <div className="mt-12 rounded-[24px] bg-[rgba(20,10,40,0.7)] border border-[#EF4444]/30 backdrop-blur-[20px] p-6 sm:p-8 shadow-[0_20px_60px_rgba(0,0,0,0.4),0_0_30px_rgba(239,68,68,0.1)]">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-2xl bg-red-500/15 border border-red-500/30 text-red-400 shrink-0">
              <ShieldAlert className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
                  ACTION REQUIRED
                </span>
                <span className="text-xs text-[#777083] font-mono">Incident #8849-V</span>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-[#F8F7FF] mt-1">
                Suspicious synthetic voice pattern detected on active call
              </h3>
              <p className="text-xs sm:text-sm text-[#B8B0C9] mt-0.5 max-w-xl">
                Phase jitter variance exceeded safe baseline (+84.2%). Select a defensive mitigation protocol:
              </p>
            </div>
          </div>

          {/* Action Trigger Buttons */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => handleAction("verify")}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#8B5CFF] to-[#7C3CFF] hover:brightness-110 text-xs font-semibold text-white transition cursor-pointer shadow-[0_0_20px_rgba(139,92,255,0.4)] flex items-center gap-2"
            >
              <CheckCircle2 className="w-4 h-4 text-[#22D3EE]" />
              <span>Verify Caller</span>
            </button>

            <button
              type="button"
              onClick={() => handleAction("callback")}
              className="px-4 py-2.5 rounded-xl bg-[#160B29] hover:bg-[#1C0D32] border border-[#8B5CFF]/30 text-xs font-semibold text-[#F8F7FF] transition cursor-pointer flex items-center gap-2"
            >
              <PhoneCall className="w-4 h-4 text-[#C084FC]" />
              <span>Request Callback</span>
            </button>

            <button
              type="button"
              onClick={() => handleAction("auth")}
              className="px-4 py-2.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-xs font-semibold text-red-300 transition cursor-pointer flex items-center gap-2"
            >
              <KeyRound className="w-4 h-4 text-red-400" />
              <span>Additional Auth</span>
            </button>
          </div>
        </div>

        {/* Dynamic Verification Output Notice */}
        {verificationState !== "idle" && (
          <div className="mt-5 pt-4 border-t border-white/[0.08] flex items-center gap-2 text-xs font-mono text-emerald-400">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>
              {verificationState === "verifying" ? "Dispatching cryptographic challenge..." : activeActionText}
            </span>
          </div>
        )}
      </div>
    </section>
  );
}
