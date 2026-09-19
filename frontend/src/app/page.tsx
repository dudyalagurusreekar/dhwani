"use client";

import React, { useState, useRef, useEffect } from "react";

import Navbar from "@/components/navigation/Navbar";
import HeroDashboard from "@/components/hero/HeroDashboard";
import MetricStrip from "@/components/dashboard/MetricStrip";
import AboutSection from "@/components/dashboard/AboutSection";
import LiveAnalysisSection from "@/components/dashboard/LiveAnalysisSection";
import ThreatIntelligence from "@/components/dashboard/ThreatIntelligence";
import VerificationWorkflow from "@/components/dashboard/VerificationWorkflow";
import FeatureCards from "@/components/dashboard/FeatureCards";
import CtaSection from "@/components/dashboard/CtaSection";
import Footer from "@/components/navigation/Footer";
import ConnectModelModal from "@/components/modals/ConnectModelModal";

interface AudioSample {
  id: string;
  name: string;
  type: string;
  threat: "authentic" | "warning" | "deepfake";
  confidence: number;
  duration: string;
  spectralDetails: string;
  isCustom?: boolean;
}

const defaultSamples: AudioSample[] = [
  {
    id: "sample-1",
    name: "executive_briefing_raw.wav",
    type: "Natural Human Speech",
    threat: "authentic",
    confidence: 99.8,
    duration: "0:14",
    spectralDetails: "Biological glottal pulses confirmed. No vocoder artifacts.",
  },
  {
    id: "sample-2",
    name: "cloned_voice_scam_call.mp3",
    type: "Diffusion Voice Synthesis",
    threat: "deepfake",
    confidence: 99.2,
    duration: "0:22",
    spectralDetails: "Phase inconsistency in 4kHz-8kHz band. Synthetic vocoder fingerprint.",
  },
  {
    id: "sample-3",
    name: "intercepted_radio_clip.ogg",
    type: "Acoustic Pitch Shifted",
    threat: "warning",
    confidence: 76.4,
    duration: "0:09",
    spectralDetails: "Formant frequency tampering detected. Borderline algorithmic confidence.",
  },
];

export default function Home() {
  const [samples, setSamples] = useState<AudioSample[]>(defaultSamples);
  const [activeSample, setActiveSample] = useState<AudioSample>(defaultSamples[0]);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);

  // Modal and APK/Model Connection states
  const [isConnectModalOpen, setIsConnectModalOpen] = useState<boolean>(false);
  const [connectedEngine, setConnectedEngine] = useState<{
    name: string;
    type: string;
  } | null>(null);

  // Audio Upload
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isAnalyzingUpload, setIsAnalyzingUpload] = useState<boolean>(false);

  // Scroll-reveal observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );
    document
      .querySelectorAll(".reveal, .reveal-left, .reveal-right")
      .forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const handleTriggerUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsAnalyzingUpload(true);
    setIsPlaying(true);

    // Simulate fast neural acoustic analysis
    setTimeout(() => {
      const isSuspect =
        file.name.toLowerCase().includes("clone") ||
        file.name.toLowerCase().includes("fake") ||
        file.name.toLowerCase().includes("ai");

      const newSample: AudioSample = {
        id: `custom-${Date.now()}`,
        name: file.name,
        type: isSuspect ? "Neural Voice Clone (Detected)" : "Acoustic Voice Recording",
        threat: isSuspect ? "deepfake" : "authentic",
        confidence: isSuspect ? 98.7 : 99.4,
        duration: "0:30",
        spectralDetails: isSuspect
          ? "Unnatural harmonic phase alignment detected. Vocoder synthetic synthesis markers identified."
          : "Natural human vocal tract resonance verified. Physiological acoustic jitter confirmed.",
        isCustom: true,
      };

      setSamples((prev) => [newSample, ...prev]);
      setActiveSample(newSample);
      setIsAnalyzingUpload(false);
    }, 900);
  };

  return (
    <div className="relative min-h-screen bg-[#05020D] text-[#F8F7FF] overflow-x-hidden selection:bg-[#8B5CFF]/30 selection:text-white">
      {/* Hidden File Input for Audio Upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*,.wav,.mp3,.ogg,.m4a,.flac"
        className="hidden"
        onChange={handleFileUpload}
      />

      {/* Connect APK & AI Model Modal */}
      <ConnectModelModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        onConnectSuccess={(engine) => {
          setConnectedEngine(engine);
          setIsConnectModalOpen(false);
        }}
      />

      {/* 
        ════════════════════════════════════════════════════════
        GLOBAL BACKGROUND ATMOSPHERIC LIGHTING & TEXTURE
        Premium, layered, controlled dark luxury atmosphere
        ════════════════════════════════════════════════════════
      */}
      <div className="fixed inset-0 pointer-events-none -z-50 overflow-hidden">
        {/* Primary hero glow — large soft purple crown */}
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[1100px] h-[680px] bg-radial from-[#8B5CFF]/13 via-[#7C3CFF]/5 to-transparent rounded-full blur-[160px]" />
        {/* Left cyan atmospheric accent */}
        <div className="absolute top-[20%] -left-40 w-[700px] h-[700px] bg-radial from-[#22D3EE]/7 via-[#0EA5E9]/3 to-transparent rounded-full blur-[170px]" />
        {/* Right magenta accent */}
        <div className="absolute top-[50%] -right-40 w-[750px] h-[750px] bg-radial from-[#7C3AED]/9 via-[#D946EF]/3 to-transparent rounded-full blur-[180px]" />
        {/* Bottom purple anchor */}
        <div className="absolute bottom-[10%] left-1/3 w-[900px] h-[600px] bg-radial from-[#8B5CFF]/10 to-transparent rounded-full blur-[170px]" />
        {/* Mid-page cyan highlight */}
        <div className="absolute top-[70%] left-[20%] w-[500px] h-[500px] bg-radial from-[#22D3EE]/5 to-transparent rounded-full blur-[130px]" />

        {/* Dot grid pattern — ultra-subtle, mask to center */}
        <div className="absolute inset-0 bg-[radial-gradient(circle,#8B5CFF09_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_80%_60%_at_50%_30%,#000_60%,transparent_100%)] opacity-40" />
        
        {/* Horizontal scan line */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#8B5CFF]/20 to-transparent" />
      </div>

      {/* COMPACT FLOATING NAVIGATION */}
      <Navbar
        onOpenConnectModal={() => setIsConnectModalOpen(true)}
        onOpenUpload={handleTriggerUpload}
        connectedModelName={connectedEngine?.name}
      />

      {/* MAIN CONTENT CANVAS */}
      <main className="relative z-10 w-full flex flex-col items-center">
        {/* SECTION 1: EDITORIAL HERO WITH 3D ORB & FLOATING CARDS */}
        <HeroDashboard
          onTriggerUpload={handleTriggerUpload}
          onOpenConnectModal={() => setIsConnectModalOpen(true)}
          isAnalyzingUpload={isAnalyzingUpload}
          connectedModelName={connectedEngine?.name}
          confidenceScore={activeSample.confidence}
          threatLevel={activeSample.threat}
        />

        {/* SECTION 2: STATISTICS / TRUST METRICS STRIP */}
        <div className="w-full reveal">
          <MetricStrip />
        </div>

        {/* SECTION 3: ABOUT ECHOSHIELD */}
        <div className="w-full reveal">
          <AboutSection />
        </div>

        {/* SECTION 4: LIVE VOICE INTELLIGENCE & RISK GAUGE */}
        <div className="w-full reveal">
          <LiveAnalysisSection
            onTriggerUpload={handleTriggerUpload}
            activeSampleName={activeSample.name}
            threatLevel={activeSample.threat}
            confidenceScore={activeSample.confidence}
            isPlaying={isPlaying}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
          />
        </div>

        {/* SECTION 5: THREAT INTELLIGENCE & TELEMETRY */}
        <div className="w-full reveal">
          <ThreatIntelligence />
        </div>

        {/* SECTION 6: ZERO-TRUST VERIFICATION WORKFLOW */}
        <div className="w-full reveal">
          <VerificationWorkflow />
        </div>

        {/* SECTION 7: ASYMMETRIC SECURITY FEATURE CARDS */}
        <div className="w-full reveal">
          <FeatureCards />
        </div>

        {/* SECTION 8: FINAL CONVERSION & DEMO CTA */}
        <div className="w-full reveal">
          <CtaSection
            onOpenConnectModal={() => setIsConnectModalOpen(true)}
            onTriggerUpload={handleTriggerUpload}
          />
        </div>
      </main>

      {/* FOOTER */}
      <Footer />
    </div>
  );
}
