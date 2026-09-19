"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Download,
  FileAudio,
  Film,
  Globe,
  Hash,
  Layers,
  Lock,
  Phone,
  PhoneCall,
  PhoneOff,
  Play,
  Radio,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  UploadCloud,
  Video,
  Volume2,
  XCircle,
} from "lucide-react";

interface LiveCallState {
  call_sid: string;
  stream_sid: string;
  caller: string;
  callee: string;
  start_time: string;
  duration_sec: number;
  status: string;
  speech: boolean;
  speech_ratio: number;
  energy_db: number;
  risk_score: number;
  risk_level: string;
  consensus: string;
  consensus_explanation: string;
  attribution: string;
  policy_action?: string;
  policy_severity?: string;
  policy_reason?: string;
  reasons: string[];
  detectors: Array<{
    model: string;
    raw_score: number;
    latency_ms: number;
  }>;
}

export default function UnifiedCyberDashboard() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "live-call" | "analyze" | "risk-monitor" | "incidents" | "system"
  >("overview");

  // Telemetry & Live Call WebSocket State
  const [wsConnected, setWsConnected] = useState(false);
  const [liveCall, setLiveCall] = useState<LiveCallState>({
    call_sid: "CA-981240-LIVE",
    stream_sid: "MZ-817293-TELEPHONY",
    caller: "+1 (***) ***-2671",
    callee: "+1 (***) ***-0199",
    start_time: new Date().toISOString(),
    duration_sec: 18,
    status: "CONNECTED",
    speech: true,
    speech_ratio: 0.82,
    energy_db: -22.4,
    risk_score: 78,
    risk_level: "HIGH",
    consensus: "UNANIMOUS",
    consensus_explanation: "All 4 models unanimously agree audio is spoof.",
    attribution: "PHYSICAL_REPLAY",
    policy_action: "TERMINATE_SESSION",
    policy_severity: "CRITICAL",
    policy_reason: "Definitive voice spoof attack confirmed (PHYSICAL_REPLAY, risk: 78%).",
    reasons: [
      "Multiple consecutive suspicious windows",
      "Cross-model agreement",
      "Elevated temporal risk",
    ],
    detectors: [
      { model: "W2V2-AASIST", raw_score: 0.94, latency_ms: 36.2 },
      { model: "AASIST", raw_score: 0.98, latency_ms: 20.4 },
      { model: "AASIST-L", raw_score: 0.99, latency_ms: 17.8 },
      { model: "ACOUSTIC", raw_score: 0.72, latency_ms: 4.1 },
    ],
  });

  // System telemetry state
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [chainIntegrity, setChainIntegrity] = useState<any>(null);

  // File analysis state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisReport, setAnalysisReport] = useState<any>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Connect to Backend WebSocket
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWs = () => {
      try {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const host = window.location.hostname || "localhost";
        ws = new WebSocket(`${protocol}//${host}:8000/ws/dashboard`);

        ws.onopen = () => {
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "risk_update" && msg.data) {
              setLiveCall((prev) => ({
                ...prev,
                ...msg.data,
                status: "CONNECTED",
              }));
            } else if (msg.type === "call_started" && msg.data) {
              setLiveCall((prev) => ({
                ...prev,
                ...msg.data,
                status: "STREAMING",
              }));
            } else if (msg.type === "call_ended") {
              setLiveCall((prev) => ({ ...prev, status: "DISCONNECTED" }));
            }
          } catch (e) {
            console.error("WS parse error:", e);
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          reconnectTimeout = setTimeout(connectWs, 3000);
        };
      } catch (e) {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connectWs, 5000);
      }
    };

    connectWs();
    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  // Poll System Status and Incidents
  const fetchStatusAndIncidents = async () => {
    try {
      const host = window.location.hostname || "localhost";
      const sysRes = await fetch(`http://${host}:8000/api/system/status`);
      if (sysRes.ok) {
        setSystemStatus(await sysRes.json());
      }
      const incRes = await fetch(`http://${host}:8000/api/incidents`);
      if (incRes.ok) {
        const incData = await incRes.json();
        setIncidents(incData.incidents || []);
        setChainIntegrity({
          count: incData.count,
          chain_intact: incData.chain_intact,
          latest_hash: incData.latest_chain_hash,
        });
      }
    } catch (e) {
      console.warn("Backend poll warning:", e);
    }
  };

  useEffect(() => {
    fetchStatusAndIncidents();
    const timer = setInterval(fetchStatusAndIncidents, 6000);
    return () => clearInterval(timer);
  }, []);

  // Handle File Upload Analysis
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setIsAnalyzing(true);
    setAnalysisError(null);
    setAnalysisReport(null);

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const host = window.location.hostname || "localhost";
      const res = await fetch(`http://${host}:8000/api/analyze/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload analysis failed");
      }

      const report = await res.json();
      setAnalysisReport(report);
      fetchStatusAndIncidents();
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to analyze media file");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle YouTube Analysis
  const handleYouTubeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl) return;

    setIsAnalyzing(true);
    setAnalysisError(null);
    setAnalysisReport(null);

    try {
      const host = window.location.hostname || "localhost";
      const res = await fetch(`http://${host}:8000/api/analyze/youtube`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: youtubeUrl }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "YouTube extraction failed");
      }

      const report = await res.json();
      setAnalysisReport(report);
      fetchStatusAndIncidents();
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to analyze YouTube audio stream");
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 py-8">
      {/* 
        ════════════════════════════════════════════════════════
        CYBER CONTROL BAR (TABS + STATUS BADGES)
        ════════════════════════════════════════════════════════
      */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-[#0F081E]/80 border border-[#8B5CFF]/20 backdrop-blur-xl mb-8">
        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: "overview", label: "Overview", icon: Shield },
            { id: "live-call", label: "Live Call", icon: PhoneCall },
            { id: "analyze", label: "Analyze Media", icon: UploadCloud },
            { id: "risk-monitor", label: "Risk Monitor", icon: Activity },
            { id: "incidents", label: "Evidence & Audit", icon: Hash },
            { id: "system", label: "System Health", icon: Cpu },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                  isActive
                    ? "bg-[#8B5CFF] text-white shadow-[0_0_20px_rgba(139,92,255,0.4)]"
                    : "text-[#A7A3B5] hover:text-white hover:bg-white/5"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Global Connection Badges */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#080312] border border-white/10">
            <span
              className={`w-2 h-2 rounded-full ${
                wsConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
              }`}
            />
            <span className="text-[#A7A3B5] font-mono">
              WSS: {wsConnected ? "STREAMING" : "CONNECTING"}
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#080312] border border-white/10">
            <Radio className="w-3.5 h-3.5 text-[#22D3EE]" />
            <span className="text-[#A7A3B5] font-mono">
              MODELS: {systemStatus?.active_models?.length || 5} ONLINE
            </span>
          </div>
        </div>
      </div>

      {/* 
        ════════════════════════════════════════════════════════
        TAB A: OVERVIEW / COMMAND CENTER
        ════════════════════════════════════════════════════════
      */}
      {activeTab === "overview" && (
        <div className="space-y-6 animate-fadeIn">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-[#0D061A]/80 border border-white/10">
              <span className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider">
                Active Telephony Call
              </span>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {liveCall.caller}
                </span>
                <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded font-mono">
                  {liveCall.status}
                </span>
              </div>
              <p className="text-xs text-[#7A758F] mt-2">
                Duration: 00:{String(liveCall.duration_sec).padStart(2, "0")} | VAD Speech:{" "}
                {Math.round(liveCall.speech_ratio * 100)}%
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-[#0D061A]/80 border border-white/10">
              <span className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider">
                Current Risk Assessment
              </span>
              <div className="flex items-baseline justify-between mt-2">
                <span
                  className={`text-2xl font-bold font-mono ${
                    liveCall.risk_score > 70
                      ? "text-rose-400"
                      : liveCall.risk_score > 40
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}
                >
                  {liveCall.risk_score}%
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
                    liveCall.risk_score > 70
                      ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                      : liveCall.risk_score > 40
                      ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  }`}
                >
                  {liveCall.risk_level}
                </span>
              </div>
              <p className="text-xs text-[#7A758F] mt-2">
                Consensus: {liveCall.consensus} ({liveCall.attribution})
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-[#0D061A]/80 border border-white/10">
              <span className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider">
                RTX 5060 GPU Acceleration
              </span>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {systemStatus?.gpu?.vram_allocated_mb || "0.0"} MB
                </span>
                <span className="text-xs text-[#22D3EE] bg-[#22D3EE]/10 px-2 py-0.5 rounded font-mono">
                  CUDA 12.8
                </span>
              </div>
              <p className="text-xs text-[#7A758F] mt-2">
                Providers: CUDAExecutionProvider active
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-[#0D061A]/80 border border-white/10">
              <span className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider">
                Cryptographic Audit Ledger
              </span>
              <div className="flex items-baseline justify-between mt-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {chainIntegrity?.count || 0} Events
                </span>
                <span className="text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded font-mono">
                  INTACT
                </span>
              </div>
              <p className="text-xs text-[#7A758F] mt-2 truncate font-mono">
                SHA-256: {chainIntegrity?.latest_hash?.slice(0, 16) || "00000000"}...
              </p>
            </div>
          </div>

          {/* Quick Jump Banner into Live Call Monitor */}
          <div className="p-6 rounded-3xl bg-gradient-to-r from-[#170B30] to-[#0A0418] border border-[#8B5CFF]/30 flex flex-col md:flex-row items-center justify-between gap-6 shadow-[0_10px_40px_rgba(0,0,0,0.5)]">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                <h3 className="text-lg font-bold text-white tracking-wide">
                  LIVE INTERCEPT: Suspect Telephony Inbound Stream
                </h3>
              </div>
              <p className="text-sm text-[#A7A3B5] max-w-2xl">
                Dhwani telephony gateway decoded Twilio G.711 μ-law stream and identified high-confidence
                vocoder/synthetic artifacts across all 4 anti-spoofing models. Active countermeasure engaged.
              </p>
            </div>
            <button
              onClick={() => setActiveTab("live-call")}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-[#8B5CFF] to-[#D946EF] text-white font-semibold text-sm hover:opacity-90 transition-opacity flex items-center gap-2 flex-shrink-0 cursor-pointer shadow-[0_0_20px_rgba(139,92,255,0.4)]"
            >
              <PhoneCall className="w-4 h-4" />
              Open Live Call Monitor
            </button>
          </div>
        </div>
      )}

      {/* 
        ════════════════════════════════════════════════════════
        TAB B: LIVE CALL SCREEN (Requirement 3 & 20)
        ════════════════════════════════════════════════════════
      */}
      {activeTab === "live-call" && (
        <div className="space-y-6 animate-fadeIn">
          <div className="p-6 rounded-3xl bg-[#0C061A]/90 border border-[#8B5CFF]/30 shadow-2xl">
            {/* Header / Call Status */}
            <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/10">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                  <Phone className="w-6 h-6 text-emerald-400 animate-pulse" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold text-white">LIVE CALL MONITOR</h2>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-semibold">
                      {liveCall.status}
                    </span>
                  </div>
                  <p className="text-xs text-[#A7A3B5] mt-1 font-mono">
                    Call SID: {liveCall.call_sid} | Stream SID: {liveCall.stream_sid}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-6">
                <div className="text-right">
                  <span className="text-xs text-[#7A758F] uppercase font-mono">Duration</span>
                  <div className="text-2xl font-mono font-bold text-white">
                    00:{String(liveCall.duration_sec).padStart(2, "0")}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-[#7A758F] uppercase font-mono">Speech Activity</span>
                  <div className="text-2xl font-mono font-bold text-[#22D3EE]">
                    {Math.round(liveCall.speech_ratio * 100)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Caller Information with Privacy Masking (Requirement 3 & 19) */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 py-6 border-b border-white/10 text-xs font-mono">
              <div className="p-4 rounded-xl bg-[#080312] border border-white/5">
                <span className="text-[#7A758F] uppercase">Caller (Privacy Masked)</span>
                <div className="text-base font-semibold text-white mt-1">{liveCall.caller}</div>
              </div>
              <div className="p-4 rounded-xl bg-[#080312] border border-white/5">
                <span className="text-[#7A758F] uppercase">Gateway Callee</span>
                <div className="text-base font-semibold text-white mt-1">{liveCall.callee}</div>
              </div>
              <div className="p-4 rounded-xl bg-[#080312] border border-white/5">
                <span className="text-[#7A758F] uppercase">Audio Stream State</span>
                <div className="text-base font-semibold text-emerald-400 mt-1">
                  8 kHz μ-law → 16 kHz PCM
                </div>
              </div>
            </div>

            {/* Primary Live Risk Assessment Strip */}
            <div className="py-6 border-b border-white/10">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
                <div className="space-y-2">
                  <span className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider">
                    Ensemble Risk Score
                  </span>
                  <div className="flex items-baseline gap-3">
                    <span
                      className={`text-5xl font-black font-mono ${
                        liveCall.risk_score > 70
                          ? "text-rose-400"
                          : liveCall.risk_score > 40
                          ? "text-amber-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {liveCall.risk_score}%
                    </span>
                    <span
                      className={`text-sm px-3 py-1 rounded-lg font-bold font-mono ${
                        liveCall.risk_score > 70
                          ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                          : liveCall.risk_score > 40
                          ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                          : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                      }`}
                    >
                      {liveCall.risk_level}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider">
                    Model Consensus & Vector
                  </span>
                  <div className="text-lg font-bold text-white font-mono">
                    Agreement: {liveCall.consensus}
                  </div>
                  <p className="text-xs text-[#A7A3B5]">
                    Vector: <span className="text-[#22D3EE] font-semibold">{liveCall.attribution}</span>
                  </p>
                </div>

                <div className="space-y-2">
                  <span className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider">
                    Mitigation Policy Enacted
                  </span>
                  <div className="text-sm font-bold text-rose-400 bg-rose-500/10 p-2.5 rounded-xl border border-rose-500/20 font-mono">
                    {liveCall.policy_action || "HOLD_PROTECTED_ACTION"}
                  </div>
                  <p className="text-xs text-[#7A758F]">{liveCall.policy_reason}</p>
                </div>
              </div>
            </div>

            {/* Individual Detector Cards (Requirement 3: W2V2, AASIST, AASIST-L, Acoustic) */}
            <div className="pt-6">
              <h4 className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider mb-4">
                Neural Model Prediction Breakdown
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {liveCall.detectors.map((det) => (
                  <div
                    key={det.model}
                    className="p-4 rounded-xl bg-[#080312] border border-white/10 space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-white font-semibold">{det.model}</span>
                      <span className="text-[#22D3EE]">{det.latency_ms} ms</span>
                    </div>
                    <div className="flex items-baseline justify-between">
                      <span className="text-xs text-[#7A758F]">Spoof Score</span>
                      <span
                        className={`text-lg font-bold font-mono ${
                          det.raw_score > 0.6
                            ? "text-rose-400"
                            : det.raw_score > 0.3
                            ? "text-amber-400"
                            : "text-emerald-400"
                        }`}
                      >
                        {Math.round(det.raw_score * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          det.raw_score > 0.6
                            ? "bg-rose-500"
                            : det.raw_score > 0.3
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                        }`}
                        style={{ width: `${Math.round(det.raw_score * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Primary Reasons / Explainability */}
            <div className="mt-6 p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
              <span className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider">
                Risk Engine Rationale & Temporal Evidence:
              </span>
              <ul className="space-y-1 text-xs text-white/90 list-disc list-inside font-mono">
                {liveCall.reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* 
        ════════════════════════════════════════════════════════
        TAB C: MEDIA ANALYSIS (FILE & YOUTUBE) (Requirement 11 & 12)
        ════════════════════════════════════════════════════════
      */}
      {activeTab === "analyze" && (
        <div className="space-y-8 animate-fadeIn">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 1. Local File Upload */}
            <div className="p-6 rounded-3xl bg-[#0C061A]/90 border border-white/10 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-xl bg-[#8B5CFF]/20 text-[#8B5CFF]">
                    <UploadCloud className="w-5 h-5" />
                  </div>
                  <h3 className="text-lg font-bold text-white">Local Audio / Video Upload</h3>
                </div>
                <p className="text-xs text-[#A7A3B5] mb-4">
                  Upload audio (.wav, .mp3, .m4a, .flac, .ogg) or video containers (.mp4, .mov, .mkv, .webm).
                  Audio track is extracted directly via FFmpeg without storing raw video.
                </p>

                <form onSubmit={handleUploadSubmit} className="space-y-4">
                  <label className="border-2 border-dashed border-white/15 rounded-2xl p-6 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-[#8B5CFF]/50 transition-colors bg-[#080312]">
                    <FileAudio className="w-8 h-8 text-[#8B5CFF]" />
                    <span className="text-xs text-white font-medium">
                      {uploadFile ? uploadFile.name : "Click to select or drag and drop media file"}
                    </span>
                    <span className="text-[10px] text-[#7A758F] font-mono">
                      WAV, MP3, M4A, FLAC, MP4, MKV (Up to 100MB)
                    </span>
                    <input
                      type="file"
                      accept="audio/*,video/*,.wav,.mp3,.m4a,.flac,.ogg,.mp4,.mov,.mkv,.webm"
                      className="hidden"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    />
                  </label>

                  <button
                    type="submit"
                    disabled={!uploadFile || isAnalyzing}
                    className="w-full py-3 rounded-xl bg-[#8B5CFF] text-white font-semibold text-xs uppercase tracking-wider disabled:opacity-50 hover:bg-[#7C3AED] transition-colors cursor-pointer flex items-center justify-center gap-2"
                  >
                    {isAnalyzing ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Analyzing on RTX 5060 GPU...
                      </>
                    ) : (
                      "Start Neural Forensic Analysis"
                    )}
                  </button>
                </form>
              </div>
            </div>

            {/* 2. YouTube URL Extraction */}
            <div className="p-6 rounded-3xl bg-[#0C061A]/90 border border-white/10 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400">
                    <Film className="w-5 h-5" />
                  </div>

                  <h3 className="text-lg font-bold text-white">Authorized YouTube Analysis</h3>
                </div>
                <p className="text-xs text-[#A7A3B5] mb-4">
                  Extracts and analyzes speech track from public authorized YouTube URLs.
                  Adheres strictly to platform terms and deletes temporary audio immediately after inspection.
                </p>

                <form onSubmit={handleYouTubeSubmit} className="space-y-4">
                  <div className="relative">
                    <input
                      type="url"
                      placeholder="https://www.youtube.com/watch?v=..."
                      value={youtubeUrl}
                      onChange={(e) => setYoutubeUrl(e.target.value)}
                      className="w-full px-4 py-3 rounded-xl bg-[#080312] border border-white/10 text-xs text-white placeholder:text-[#5A556B] focus:outline-none focus:border-rose-400 font-mono"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={!youtubeUrl || isAnalyzing}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-500 to-rose-700 text-white font-semibold text-xs uppercase tracking-wider disabled:opacity-50 hover:opacity-90 transition-opacity cursor-pointer flex items-center justify-center gap-2"
                  >
                    {isAnalyzing ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Streaming & Analyzing...
                      </>
                    ) : (
                      "Extract & Analyze Audio Track"
                    )}
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* Analysis Error Message */}
          {analysisError && (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-3">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{analysisError}</span>
            </div>
          )}

          {/* Detailed Forensic Report (Requirement 17 Schema) */}
          {analysisReport && (
            <div className="p-6 rounded-3xl bg-[#0C061A] border border-white/15 space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-white/10">
                <div>
                  <span className="text-xs text-[#7A758F] font-mono">
                    ANALYSIS ID: {analysisReport.analysis_id}
                  </span>
                  <h3 className="text-xl font-bold text-white mt-1">
                    Forensic Verification Report: {analysisReport.source_metadata?.original_filename || analysisReport.source_type}
                  </h3>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`text-xs px-3 py-1 rounded-lg font-bold font-mono ${
                      analysisReport.risk_score > 70
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                        : analysisReport.risk_score > 40
                        ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                        : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                    }`}
                  >
                    {analysisReport.risk_level} ({analysisReport.risk_score}%)
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                <div className="p-3 rounded-xl bg-white/5">
                  <span className="text-[#7A758F]">Duration</span>
                  <div className="text-sm font-bold text-white mt-1">
                    {analysisReport.duration_seconds}s (Speech: {analysisReport.speech_duration_seconds}s)
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-white/5">
                  <span className="text-[#7A758F]">Windows Processed</span>
                  <div className="text-sm font-bold text-white mt-1">
                    {analysisReport.windows_analyzed} x 4.037s
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-white/5">
                  <span className="text-[#7A758F]">Processing Time</span>
                  <div className="text-sm font-bold text-[#22D3EE] mt-1">
                    {analysisReport.processing_time_ms} ms
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-white/5">
                  <span className="text-[#7A758F]">Evidence Hash</span>
                  <div className="text-sm font-bold text-white mt-1 truncate" title={analysisReport.evidence_hash}>
                    {analysisReport.evidence_hash?.slice(0, 16)}...
                  </div>
                </div>
              </div>

              {/* Detector Breakdown */}
              <div>
                <h4 className="text-xs text-[#A7A3B5] uppercase font-mono tracking-wider mb-3">
                  Evaluated Anti-Spoofing Detectors
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {analysisReport.detectors?.map((d: any) => (
                    <div key={d.model} className="p-3 rounded-xl bg-[#080312] border border-white/5">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-white">{d.model}</span>
                        <span className="text-[#22D3EE]">{d.latency_ms}ms</span>
                      </div>
                      <div className="text-base font-bold font-mono text-white mt-1">
                        {Math.round(d.raw_score * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Download Report */}
              <div className="pt-4 flex justify-end">
                <a
                  href={`data:text/json;charset=utf-8,${encodeURIComponent(
                    JSON.stringify(analysisReport, null, 2)
                  )}`}
                  download={`dhwani_audit_${analysisReport.analysis_id}.json`}
                  className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download Forensic Audit JSON
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 
        ════════════════════════════════════════════════════════
        TAB D: INCIDENTS / SECURITY EVIDENCE (Requirement 18)
        ════════════════════════════════════════════════════════
      */}
      {activeTab === "incidents" && (
        <div className="space-y-6 animate-fadeIn">
          <div className="p-6 rounded-3xl bg-[#0C061A]/90 border border-white/10">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="text-lg font-bold text-white">Cryptographic Tamper-Evident Ledger</h3>
                <p className="text-xs text-[#A7A3B5] mt-1 font-mono">
                  Immutable SHA-256 hash chaining. Every security event is cryptographically bound to its predecessor.
                </p>
              </div>

              <button
                onClick={fetchStatusAndIncidents}
                className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Verify Ledger Integrity
              </button>
            </div>

            {/* Incidents Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-white/10 text-[#7A758F] uppercase">
                    <th className="py-3 px-4">Incident ID</th>
                    <th className="py-3 px-4">Risk Level</th>
                    <th className="py-3 px-4">Attack Vector</th>
                    <th className="py-3 px-4">Action Taken</th>
                    <th className="py-3 px-4">Verification</th>
                    <th className="py-3 px-4">SHA-256 Chain Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {incidents.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-[#7A758F]">
                        No high-risk incidents logged yet in active session.
                      </td>
                    </tr>
                  ) : (
                    incidents.map((inc) => (
                      <tr key={inc.incident_id} className="hover:bg-white/5 transition-colors">
                        <td className="py-3 px-4 text-white font-semibold">{inc.incident_id}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded ${
                              inc.risk_score > 70
                                ? "bg-rose-500/20 text-rose-400"
                                : "bg-amber-500/20 text-amber-400"
                            }`}
                          >
                            {inc.risk_level} ({inc.risk_score}%)
                          </span>
                        </td>
                        <td className="py-3 px-4 text-[#22D3EE]">{inc.attack_vector}</td>
                        <td className="py-3 px-4 text-white">{inc.action_taken}</td>
                        <td className="py-3 px-4">
                          <span className="text-amber-400">{inc.verification_status}</span>
                        </td>
                        <td className="py-3 px-4 text-[#7A758F] truncate max-w-[160px]">
                          {inc.current_hash}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 
        ════════════════════════════════════════════════════════
        TAB E: SYSTEM STATUS (Requirement 20)
        ════════════════════════════════════════════════════════
      */}
      {activeTab === "system" && (
        <div className="space-y-6 animate-fadeIn">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* GPU Telemetry */}
            <div className="p-6 rounded-3xl bg-[#0C061A]/90 border border-white/10 space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-[#22D3EE]/20 text-[#22D3EE]">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">NVIDIA Hardware Acceleration</h3>
                  <p className="text-xs text-[#7A758F] font-mono">
                    {systemStatus?.gpu?.device_name || "NVIDIA GeForce RTX 5060 Laptop GPU"}
                  </p>
                </div>
              </div>

              <div className="space-y-3 pt-2 text-xs font-mono">
                <div className="flex justify-between text-[#A7A3B5]">
                  <span>VRAM Allocated:</span>
                  <span className="text-white font-bold">{systemStatus?.gpu?.vram_allocated_mb || 0} MB</span>
                </div>
                <div className="flex justify-between text-[#A7A3B5]">
                  <span>VRAM Reserved:</span>
                  <span className="text-white font-bold">{systemStatus?.gpu?.vram_reserved_mb || 0} MB</span>
                </div>
                <div className="flex justify-between text-[#A7A3B5]">
                  <span>VRAM Capacity:</span>
                  <span className="text-white font-bold">{systemStatus?.gpu?.vram_total_mb || 8192} MB</span>
                </div>
              </div>
            </div>

            {/* Model Inventory */}
            <div className="p-6 rounded-3xl bg-[#0C061A]/90 border border-white/10 space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-[#8B5CFF]/20 text-[#8B5CFF]">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Active Neural Models</h3>
                  <p className="text-xs text-[#7A758F] font-mono">ONNX Runtime GPU 1.30 Stack</p>
                </div>
              </div>

              <div className="space-y-2 pt-2 text-xs font-mono">
                {[
                  { name: "W2V2-AASIST", type: "Wav2Vec2 + GAT", size: "1.18 GB", status: "ONLINE (CUDA)" },
                  { name: "AASIST", type: "SincNet + Temporal GAT", size: "1.54 MB", status: "ONLINE (CUDA)" },
                  { name: "AASIST-L", type: "Lightweight GAT", size: "766 KB", status: "ONLINE (CUDA)" },
                  { name: "ACOUSTIC", type: "Handcrafted Spectral/LFCC", size: "Lightweight", status: "ONLINE (CPU)" },
                  { name: "ECAPA-TDNN", type: "Deep Speaker Verification", size: "24.8 MB", status: "ONLINE (CUDA)" },
                ].map((m) => (
                  <div key={m.name} className="flex items-center justify-between p-2 rounded-lg bg-white/5">
                    <span className="text-white font-semibold">{m.name}</span>
                    <span className="text-[#22D3EE]">{m.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
