"use client";

import React from "react";
import { Radio } from "lucide-react";

export default function Footer() {
  return (
    <footer className="w-full border-t border-[rgba(160,100,255,0.12)] bg-[#05020D] py-12 px-4 sm:px-6 text-xs text-[#777083]">
      <div className="max-w-[1360px] mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-[#160B29] border border-[#8B5CFF]/30 flex items-center justify-center">
            <Radio className="w-3.5 h-3.5 text-[#22D3EE]" />
          </div>
          <div>
            <div className="font-bold text-sm tracking-wider text-[#F8F7FF] flex items-center gap-2">
              <span>DHWANI</span>
              <span className="text-[10px] font-mono text-[#8B5CFF] font-medium">ECHOSHIELD AI</span>
            </div>
            <p className="text-[11px] text-[#777083]">
              AI-powered protection against voice impersonation and synthetic speech fraud.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-6 font-mono text-[11px]">
          <a href="#dashboard" className="text-[#B8B0C9] hover:text-[#F8F7FF] transition">
            Dashboard
          </a>
          <a href="#live-analysis" className="text-[#B8B0C9] hover:text-[#F8F7FF] transition">
            Live Security
          </a>
          <a href="#threat-intelligence" className="text-[#B8B0C9] hover:text-[#F8F7FF] transition">
            Analytics
          </a>
          <a href="#workflow" className="text-[#B8B0C9] hover:text-[#F8F7FF] transition">
            Workflow
          </a>
          <a href="#features" className="text-[#B8B0C9] hover:text-[#F8F7FF] transition">
            Documentation
          </a>
        </div>

        <div className="text-[11px] text-[#777083] font-mono">
          © {new Date().getFullYear()} DHWANI Research Lab. Zero-Trust Voice Defense.
        </div>
      </div>
    </footer>
  );
}
