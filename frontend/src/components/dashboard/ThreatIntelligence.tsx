"use client";

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { ShieldAlert, ShieldCheck, AlertTriangle, Radio, Shield, ExternalLink } from "lucide-react";
import { threatTimelineData, securityEvents, SecurityEvent } from "@/data/dashboardData";

export default function ThreatIntelligence() {
  const getSeverityBadge = (severity: SecurityEvent["severity"]) => {
    switch (severity) {
      case "HIGH":
        return "bg-red-500/15 border-red-500/30 text-red-400";
      case "MEDIUM":
        return "bg-amber-500/15 border-amber-500/30 text-amber-400";
      case "LOW":
        return "bg-emerald-500/15 border-emerald-500/30 text-emerald-400";
      default:
        return "bg-[#8B5CFF]/15 border-[#8B5CFF]/30 text-[#C084FC]";
    }
  };

  return (
    <section id="threat-intelligence" className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 py-16">
      {/* Section Heading */}
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#8B5CFF]/10 border border-[#8B5CFF]/25 text-[#C084FC] text-xs font-mono font-semibold mb-3">
          <ShieldAlert className="w-3.5 h-3.5" />
          GLOBAL VOICE SECURITY RADAR
        </div>
        <h2 className="text-3xl sm:text-4xl font-black text-[#F8F7FF] tracking-tight">
          Threat Intelligence & Attack Telemetry
        </h2>
        <p className="text-[#B8B0C9] text-sm sm:text-base mt-2 max-w-2xl">
          Multi-layer acoustic trend analysis tracking adversarial diffusion models,
          generative vocoders, and intercepted impersonation attempts.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        {/* Left (7 cols): Recharts Area Chart */}
        <div className="lg:col-span-7 flex flex-col justify-between rounded-[24px] bg-[rgba(20,10,40,0.6)] border border-[rgba(160,100,255,0.2)] backdrop-blur-[20px] p-6 sm:p-8 shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-white/[0.06] gap-3">
            <div>
              <h3 className="text-sm font-bold font-mono text-[#F8F7FF] tracking-wider uppercase">
                24H INCIDENT DISTRIBUTION
              </h3>
              <p className="text-xs text-[#777083] mt-0.5">
                Synthetic vs. Genuine voice streams across active endpoints
              </p>
            </div>

            {/* Legend */}
            <div className="flex items-center gap-4 text-xs font-mono">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#22D3EE]" />
                <span className="text-[#B8B0C9]">Genuine</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#8B5CFF]" />
                <span className="text-[#B8B0C9]">Suspicious</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
                <span className="text-[#B8B0C9]">Synthetic</span>
              </div>
            </div>
          </div>

          {/* Chart Container */}
          <div className="w-full h-72 sm:h-80 pt-6">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={threatTimelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorGenuine" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22D3EE" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#22D3EE" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorSuspicious" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8B5CFF" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#8B5CFF" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorSynthetic" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.5} />
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#777083" fontSize={11} tickLine={false} />
                <YAxis stroke="#777083" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0C0618",
                    borderColor: "rgba(160, 100, 255, 0.3)",
                    borderRadius: "12px",
                    color: "#F8F7FF",
                    fontSize: "12px",
                    boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
                  }}
                />
                <Area type="monotone" dataKey="genuine" stroke="#22D3EE" strokeWidth={2} fillOpacity={1} fill="url(#colorGenuine)" />
                <Area type="monotone" dataKey="suspicious" stroke="#8B5CFF" strokeWidth={2} fillOpacity={1} fill="url(#colorSuspicious)" />
                <Area type="monotone" dataKey="synthetic" stroke="#EF4444" strokeWidth={2} fillOpacity={1} fill="url(#colorSynthetic)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right (5 cols): Recent Security Events */}
        <div className="lg:col-span-5 rounded-[24px] bg-[rgba(20,10,40,0.6)] border border-[rgba(160,100,255,0.2)] backdrop-blur-[20px] p-6 sm:p-8 shadow-[0_20px_60px_rgba(0,0,0,0.4)] flex flex-col justify-between">
          <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
            <div>
              <h3 className="text-sm font-bold font-mono text-[#F8F7FF] tracking-wider uppercase">
                RECENT SECURITY EVENTS
              </h3>
              <p className="text-xs text-[#777083] mt-0.5">Live neural discriminator log</p>
            </div>
            <span className="text-[10px] font-mono text-[#22D3EE] font-semibold">STREAMING</span>
          </div>

          <div className="space-y-3 my-4 overflow-y-auto max-h-[320px] pr-1">
            {securityEvents.map((evt) => (
              <div
                key={evt.id}
                className="p-3.5 rounded-xl bg-[#080312]/70 border border-white/[0.06] hover:border-[#8B5CFF]/30 transition-colors flex items-start justify-between gap-3"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${getSeverityBadge(evt.severity)}`}>
                      {evt.severity}
                    </span>
                    <h4 className="text-xs font-semibold text-[#F8F7FF] truncate">
                      {evt.type}
                    </h4>
                  </div>
                  <div className="text-[11px] text-[#777083] font-mono truncate">
                    {evt.source}
                  </div>
                </div>

                <div className="text-right flex-shrink-0">
                  <div className="text-[10px] font-mono text-[#B8B0C9]">{evt.timestamp}</div>
                  <div className="text-[10px] font-mono text-emerald-400 font-semibold">{evt.confidence}% match</div>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-[#B8B0C9]">
            <span>Automated edge mitigation active</span>
            <span className="text-[#8B5CFF] hover:text-[#C084FC] cursor-pointer flex items-center gap-1 font-mono text-[11px]">
              Full Audit Log <ExternalLink className="w-3 h-3" />
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
