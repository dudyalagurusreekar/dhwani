"use client";

import React, { useState } from "react";
import {
    X,
    Smartphone,
    Cpu,
    CheckCircle2,
    AlertCircle,
    Wifi,
    Download,
    Key,
    Globe,
    Radio,
    Copy,
    Check,
    Layers,
    ArrowRight,
} from "lucide-react";

interface ConnectModelModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConnectSuccess?: (modelInfo: { name: string; type: string }) => void;
}

export default function ConnectModelModal({
    isOpen,
    onClose,
    onConnectSuccess,
}: ConnectModelModalProps) {
    const [activeTab, setActiveTab] = useState<"apk" | "ai_model">("apk");
    const [apkConnected, setApkConnected] = useState(false);
    const [copiedCode, setCopiedCode] = useState(false);

    // AI Model form states
    const [endpointUrl, setEndpointUrl] = useState("https://api.dhwani.ai/v1/infer");
    const [apiKey, setApiKey] = useState("");
    const [modelType, setModelType] = useState("rawnet3");
    const [isTestingConnection, setIsTestingConnection] = useState(false);
    const [modelConnected, setModelConnected] = useState(false);
    const [testResult, setTestResult] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleCopyPairCode = () => {
        navigator.clipboard.writeText("DHWANI-9942-SEC");
        setCopiedCode(true);
        setTimeout(() => setCopiedCode(false), 2000);
    };

    const handleTestAiConnection = () => {
        setIsTestingConnection(true);
        setTestResult(null);
        setTimeout(() => {
            setIsTestingConnection(false);
            setModelConnected(true);
            setTestResult("Connected successfully! Model latency: 11.4ms (99.8% precision)");
            if (onConnectSuccess) {
                onConnectSuccess({
                    name: modelType === "rawnet3" ? "RawNet3 AASIST Engine" : "WavLM Biometric Heavy",
                    type: "Custom Neural Model",
                });
            }
        }, 1200);
    };

    const handleSimulateApkPair = () => {
        setApkConnected(true);
        if (onConnectSuccess) {
            onConnectSuccess({
                name: "DHWANI Guardian Android (SM-S928B)",
                type: "Mobile Telemetry APK",
            });
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
            <div className="relative w-full max-w-2xl bg-[#0F172A] border border-[#334155] rounded-2xl shadow-2xl overflow-hidden text-[#E2E8F0]">
                {/* Modal Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-[#1E293B] bg-[#111827]/60">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-gradient-to-br from-[#A855F7]/20 to-[#22D3EE]/20 border border-[#A855F7]/30 text-[#22D3EE]">
                            <Cpu className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white tracking-wide flex items-center gap-2">
                                Connect Engine & Telemetry
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#22D3EE]/20 border border-[#22D3EE]/40 text-[#22D3EE] font-mono font-semibold">
                                    v2.4 Live
                                </span>
                            </h3>
                            <p className="text-xs text-[#94A3B8]">
                                Link your Android Guardian APK or connect custom AI deepfake inference models.
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        type="button"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition cursor-pointer"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Tab Selector */}
                <div className="flex border-b border-[#1E293B] bg-[#0A101D] px-6 pt-3 gap-2">
                    <button
                        type="button"
                        onClick={() => setActiveTab("apk")}
                        className={`flex items-center gap-2 pb-3 px-3 text-xs font-semibold tracking-wide border-b-2 transition cursor-pointer ${activeTab === "apk"
                                ? "border-[#22D3EE] text-[#22D3EE]"
                                : "border-transparent text-slate-400 hover:text-slate-200"
                            }`}
                    >
                        <Smartphone className="w-4 h-4" />
                        Android Guardian APK
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveTab("ai_model")}
                        className={`flex items-center gap-2 pb-3 px-3 text-xs font-semibold tracking-wide border-b-2 transition cursor-pointer ${activeTab === "ai_model"
                                ? "border-[#A855F7] text-[#A855F7]"
                                : "border-transparent text-slate-400 hover:text-slate-200"
                            }`}
                    >
                        <Cpu className="w-4 h-4" />
                        Custom AI Inference Model
                    </button>
                </div>

                {/* Modal Body */}
                <div className="p-6 max-h-[70vh] overflow-y-auto">
                    {activeTab === "apk" ? (
                        /* APK Tab */
                        <div className="space-y-6">
                            <div className="p-4 rounded-xl bg-[#111827] border border-[#1E293B] flex flex-col sm:flex-row items-center gap-5">
                                {/* QR Code Placeholder Graphic */}
                                <div className="relative w-28 h-28 bg-white p-2 rounded-lg flex-shrink-0 flex items-center justify-center shadow-lg">
                                    <div className="w-full h-full border-4 border-slate-900 grid grid-cols-4 grid-rows-4 gap-1 p-1 bg-slate-900">
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-transparent" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-transparent" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-transparent" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-transparent" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-transparent" />
                                        <div className="bg-white rounded-[2px]" />
                                        <div className="bg-white rounded-[2px]" />
                                    </div>
                                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                        <span className="p-1 bg-[#080F1A] rounded text-[9px] font-bold text-[#22D3EE] border border-[#22D3EE]">
                                            DHWANI
                                        </span>
                                    </div>
                                </div>

                                <div className="flex-1 text-center sm:text-left space-y-2">
                                    <div className="inline-flex items-center gap-1.5 text-xs text-[#22D3EE] font-mono font-medium">
                                        <Radio className="w-3.5 h-3.5 animate-pulse" />
                                        REAL-TIME MOBILE AUDIO INTERCEPTION
                                    </div>
                                    <h4 className="text-sm font-semibold text-white">
                                        Pair DHWANI Mobile Guardian (Android)
                                    </h4>
                                    <p className="text-xs text-[#94A3B8] leading-relaxed">
                                        Scan this QR code from the DHWANI Android App to stream incoming phone audio
                                        and microphone telemetry directly into the live neural classification engine.
                                    </p>
                                </div>
                            </div>

                            {/* Pairing Code Row */}
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-slate-300">
                                    Manual Pairing Security Key
                                </label>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 px-4 py-2.5 bg-[#080F1A] border border-[#1E293B] rounded-lg font-mono text-sm text-[#22D3EE] tracking-widest">
                                        DHWANI-9942-SEC
                                    </div>
                                    <button
                                        type="button"
                                        onClick={handleCopyPairCode}
                                        className="px-3.5 py-2.5 rounded-lg bg-[#1E293B] hover:bg-[#334155] border border-[#334155] text-xs font-medium text-white flex items-center gap-1.5 transition cursor-pointer"
                                    >
                                        {copiedCode ? (
                                            <>
                                                <Check className="w-4 h-4 text-[#10B981]" />
                                                <span>Copied</span>
                                            </>
                                        ) : (
                                            <>
                                                <Copy className="w-4 h-4" />
                                                <span>Copy</span>
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>

                            {/* Status and Action */}
                            <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
                                <div className="flex items-center gap-2 text-xs">
                                    <span
                                        className={`w-2.5 h-2.5 rounded-full ${apkConnected ? "bg-[#10B981] animate-pulse" : "bg-[#F59E0B]"
                                            }`}
                                    />
                                    <span className="text-[#94A3B8]">
                                        Status:{" "}
                                        <strong className={apkConnected ? "text-[#10B981]" : "text-[#F59E0B]"}>
                                            {apkConnected ? "Connected (SM-S928B Active)" : "Awaiting Pairing"}
                                        </strong>
                                    </span>
                                </div>

                                <div className="flex items-center gap-2 w-full sm:w-auto">
                                    <button
                                        type="button"
                                        onClick={handleSimulateApkPair}
                                        className="flex-1 sm:flex-initial px-4 py-2 text-xs font-semibold rounded-lg bg-gradient-to-r from-[#22D3EE] to-[#0EA5E9] text-[#080F1A] hover:brightness-110 transition cursor-pointer flex items-center justify-center gap-1.5"
                                    >
                                        <Wifi className="w-3.5 h-3.5" />
                                        {apkConnected ? "Re-pair Android APK" : "Simulate APK Link"}
                                    </button>

                                    <a
                                        href="#download-apk"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            alert("DHWANI Guardian v2.4.1 APK build download ready in artifacts.");
                                        }}
                                        className="flex-1 sm:flex-initial px-3.5 py-2 text-xs font-medium rounded-lg bg-[#1E293B] hover:bg-[#334155] border border-[#334155] text-white flex items-center justify-center gap-1.5 transition"
                                    >
                                        <Download className="w-3.5 h-3.5 text-[#22D3EE]" />
                                        Get APK (.apk)
                                    </a>
                                </div>
                            </div>
                        </div>
                    ) : (
                        /* Custom AI Model Tab */
                        <div className="space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                                    <Globe className="w-3.5 h-3.5 text-[#A855F7]" />
                                    Model Inference Endpoint URL
                                </label>
                                <input
                                    type="text"
                                    value={endpointUrl}
                                    onChange={(e) => setEndpointUrl(e.target.value)}
                                    placeholder="https://api.your-domain.com/v1/voice-detect"
                                    className="w-full px-3.5 py-2.5 rounded-lg bg-[#080F1A] border border-[#1E293B] focus:border-[#A855F7] text-xs font-mono text-white focus:outline-none transition"
                                />
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                                        <Key className="w-3.5 h-3.5 text-[#22D3EE]" />
                                        API Authorization Token
                                    </label>
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder="dhw_live_sk_..."
                                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#080F1A] border border-[#1E293B] focus:border-[#22D3EE] text-xs font-mono text-white focus:outline-none transition"
                                    />
                                </div>

                                <div className="space-y-1.5">
                                    <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                                        <Layers className="w-3.5 h-3.5 text-[#A855F7]" />
                                        Model Architecture / Pipeline
                                    </label>
                                    <select
                                        value={modelType}
                                        onChange={(e) => setModelType(e.target.value)}
                                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#080F1A] border border-[#1E293B] focus:border-[#A855F7] text-xs text-white focus:outline-none transition"
                                    >
                                        <option value="rawnet3">RawNet3 AASIST (Sub-15ms SOTA)</option>
                                        <option value="wavlm">WavLM Large Biometric Embeddings</option>
                                        <option value="conformer">Conformer Spectral Discriminator</option>
                                        <option value="custom_onnx">Custom ONNX / TensorRT Endpoint</option>
                                    </select>
                                </div>
                            </div>

                            {testResult && (
                                <div className="p-3 rounded-lg bg-[#10B981]/10 border border-[#10B981]/30 text-xs text-[#10B981] flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                                    <span>{testResult}</span>
                                </div>
                            )}

                            <div className="pt-3 flex items-center justify-between border-t border-[#1E293B]">
                                <span className="text-[11px] text-[#94A3B8]">
                                    Supports REST, gRPC streaming, and WebSocket bi-directional formats.
                                </span>

                                <button
                                    type="button"
                                    onClick={handleTestAiConnection}
                                    disabled={isTestingConnection}
                                    className="px-5 py-2.5 rounded-lg text-xs font-semibold text-white bg-gradient-to-r from-[#A855F7] to-[#7C3AED] hover:brightness-110 transition cursor-pointer flex items-center gap-2 shadow-[var(--dhwani-glow-purple)] disabled:opacity-50"
                                >
                                    {isTestingConnection ? (
                                        <>
                                            <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            <span>Validating Handshake...</span>
                                        </>
                                    ) : (
                                        <>
                                            <Cpu className="w-3.5 h-3.5 text-[#22D3EE]" />
                                            <span>{modelConnected ? "Re-Test & Save" : "Test & Connect Model"}</span>
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
