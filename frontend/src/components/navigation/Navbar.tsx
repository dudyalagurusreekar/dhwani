"use client";

import React, { useState, useEffect } from "react";
import { Radio, Terminal, ChevronRight, Menu, X, Shield, Activity, Layers, Cpu, Sparkles } from "lucide-react";

interface NavbarProps {
  onOpenConnectModal?: () => void;
  onOpenUpload?: () => void;
  connectedModelName?: string | null;
}

const navLinks = [
  { name: "Dashboard", href: "#dashboard" },
  { name: "Live Detection", href: "#live-analysis" },
  { name: "Threats", href: "#threat-intelligence" },
  { name: "Workflow", href: "#workflow" },
  { name: "Features", href: "#features" },
];

export default function Navbar({
  onOpenConnectModal,
  onOpenUpload,
  connectedModelName,
}: NavbarProps) {
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close mobile menu on link click
  const handleNavClick = (name: string) => {
    setActiveTab(name);
    setMobileOpen(false);
  };

  return (
    <>
      <header
        className={`fixed top-4 sm:top-5 inset-x-0 z-50 max-w-[1360px] mx-auto px-4 sm:px-6 pointer-events-none transition-all duration-300`}
      >
        <div
          className={`w-full flex items-center justify-between px-4 sm:px-5 py-2.5 rounded-[20px] border backdrop-blur-[24px] pointer-events-auto transition-all duration-300 ${
            scrolled
              ? "bg-[rgba(10,5,22,0.88)] border-[rgba(150,80,255,0.22)] shadow-[0_12px_48px_rgba(0,0,0,0.6),0_0_30px_rgba(124,60,255,0.1)]"
              : "bg-[rgba(15,8,30,0.72)] border-[rgba(150,80,255,0.16)] shadow-[0_10px_36px_rgba(0,0,0,0.4)]"
          }`}
        >
          {/* Left: DHWANI Brand */}
          <a href="#dashboard" className="flex items-center gap-3 group cursor-pointer flex-shrink-0">
            <div className="relative flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-[#8B5CFF] to-[#22D3EE] p-[1.5px] shadow-[0_0_18px_rgba(139,92,255,0.4)]">
              <div className="w-full h-full bg-[#080312] rounded-[10px] flex items-center justify-center">
                <Radio className="w-3.5 h-3.5 text-[#22D3EE] group-hover:scale-110 transition-transform" />
              </div>
            </div>
            <div className="flex flex-col leading-none">
              <div className="flex items-center gap-1.5">
                <span className="text-[13px] font-black tracking-wider text-[#F8F7FF]">
                  DHWANI
                </span>
                <span className="text-[8px] font-mono font-bold px-1.5 py-0.5 rounded bg-[#8B5CFF]/15 border border-[#8B5CFF]/30 text-[#C084FC]">
                  v2.4
                </span>
              </div>
              <span className="text-[8px] font-mono tracking-[0.15em] text-[#777083] font-medium uppercase mt-0.5">
                ECHOSHIELD AI
              </span>
            </div>
          </a>

          {/* Center: Navigation Pill (desktop only) */}
          <nav className="hidden md:flex items-center gap-0.5 px-2 py-1 rounded-full bg-white/[0.03] border border-white/[0.05]">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => handleNavClick(link.name)}
                className={`px-3 py-1 rounded-full text-[12px] font-medium transition-all duration-200 cursor-pointer ${
                  activeTab === link.name
                    ? "bg-[#8B5CFF]/22 text-[#F8F7FF] border border-[#8B5CFF]/35 shadow-[0_0_10px_rgba(139,92,255,0.25)] font-semibold"
                    : "text-[#B8B0C9] hover:text-[#F8F7FF] hover:bg-white/[0.05] border border-transparent"
                }`}
              >
                {link.name}
              </a>
            ))}
          </nav>

          {/* Right: System Status & Actions */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* System Status Pill */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/22 text-emerald-400 text-[10px] font-mono">
              <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-semibold tracking-wide">ACTIVE</span>
            </div>

            {/* Connect Engine Button */}
            {onOpenConnectModal && (
              <button
                type="button"
                onClick={onOpenConnectModal}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#160B29] hover:bg-[#1C0D32] border border-[#8B5CFF]/28 hover:border-[#8B5CFF]/55 text-[11px] font-mono text-[#C084FC] hover:text-[#F8F7FF] transition cursor-pointer"
              >
                <Terminal className="w-3 h-3 text-[#22D3EE]" />
                <span className="hidden lg:inline">
                  {connectedModelName ? "APK Linked" : "Connect Engine"}
                </span>
              </button>
            )}

            {/* Primary CTA */}
            <a
              href="#live-analysis"
              className="px-4 sm:px-5 py-2 rounded-full text-[12px] font-semibold text-white bg-gradient-to-r from-[#8B5CFF] via-[#7C3CFF] to-[#D946EF] hover:brightness-110 shadow-[0_0_22px_rgba(139,92,255,0.4)] hover:shadow-[0_0_28px_rgba(217,70,239,0.5)] transition-all duration-300 flex items-center gap-1.5 cursor-pointer"
            >
              <span className="hidden sm:inline">Launch Studio</span>
              <span className="sm:hidden">Studio</span>
              <ChevronRight className="w-3.5 h-3.5 text-white/90" />
            </a>

            {/* Mobile Menu Toggle */}
            <button
              type="button"
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg bg-white/[0.05] border border-white/[0.08] text-[#B8B0C9] hover:text-white transition cursor-pointer"
            >
              {mobileOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        <div
          className={`md:hidden mt-2 rounded-[16px] bg-[rgba(10,5,22,0.95)] border border-[rgba(150,80,255,0.22)] backdrop-blur-[24px] shadow-[0_20px_60px_rgba(0,0,0,0.6)] overflow-hidden transition-all duration-300 pointer-events-auto ${
            mobileOpen ? "max-h-[400px] opacity-100" : "max-h-0 opacity-0 pointer-events-none"
          }`}
        >
          <nav className="p-3 flex flex-col gap-1">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => handleNavClick(link.name)}
                className={`px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer flex items-center justify-between ${
                  activeTab === link.name
                    ? "bg-[#8B5CFF]/20 text-[#F8F7FF] border border-[#8B5CFF]/30"
                    : "text-[#B8B0C9] hover:bg-white/[0.04] hover:text-[#F8F7FF] border border-transparent"
                }`}
              >
                <span>{link.name}</span>
                {activeTab === link.name && (
                  <span className="w-1.5 h-1.5 rounded-full bg-[#22D3EE]" />
                )}
              </a>
            ))}

            <div className="mt-2 pt-2 border-t border-white/[0.06] flex flex-col gap-2">
              {onOpenConnectModal && (
                <button
                  type="button"
                  onClick={() => { onOpenConnectModal(); setMobileOpen(false); }}
                  className="px-4 py-3 rounded-xl text-sm font-medium text-[#C084FC] bg-[#160B29] border border-[#8B5CFF]/25 flex items-center gap-2 cursor-pointer hover:bg-[#1C0D32] transition"
                >
                  <Terminal className="w-4 h-4 text-[#22D3EE]" />
                  {connectedModelName ? "APK Linked" : "Connect Engine"}
                </button>
              )}
              <a
                href="#live-analysis"
                onClick={() => setMobileOpen(false)}
                className="px-4 py-3 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-[#8B5CFF] to-[#D946EF] flex items-center justify-center gap-2 cursor-pointer"
              >
                Launch Studio
                <ChevronRight className="w-4 h-4" />
              </a>
            </div>
          </nav>
        </div>
      </header>
    </>
  );
}
