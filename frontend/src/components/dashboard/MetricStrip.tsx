"use client";

import React, { useEffect, useRef, useState } from "react";
import { ShieldCheck, Cpu, Zap, ShieldAlert, Activity } from "lucide-react";

interface Metric {
  value: string;
  label: string;
  subtext: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  numericValue?: number;
  suffix?: string;
  prefix?: string;
}

function useCountUp(target: number, duration: number = 1400, enabled: boolean = true) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let start = 0;
    const step = target / (duration / 16);
    const timer = setInterval(() => {
      start = Math.min(start + step, target);
      setCount(Math.floor(start));
      if (start >= target) clearInterval(timer);
    }, 16);
    return () => clearInterval(timer);
  }, [target, duration, enabled]);
  return count;
}

function MetricItem({ item, index, visible }: { item: Metric; index: number; visible: boolean }) {
  const count = useCountUp(item.numericValue ?? 0, 1600, visible && !!item.numericValue);
  const Icon = item.icon;
  const displayValue = item.numericValue
    ? `${item.prefix ?? ""}${count.toLocaleString()}${item.suffix ?? ""}`
    : item.value;

  return (
    <div
      className={`flex flex-col justify-center transition-all duration-700 ${
        index === 0
          ? "md:pr-6"
          : index === 4
          ? "md:pl-6"
          : "md:px-6"
      }`}
      style={{ transitionDelay: `${index * 80}ms` }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <Icon className={`w-4 h-4 ${item.color}`} />
        <span className="text-[10px] font-mono font-bold tracking-widest text-[#B8B0C9] uppercase">
          {item.label}
        </span>
      </div>
      <div className="text-2xl sm:text-3xl lg:text-[2.15rem] font-black text-[#F8F7FF] tracking-tight font-sans tabular-nums">
        {displayValue}
      </div>
      <div className="text-[11px] text-[#777083] font-medium mt-1">
        {item.subtext}
      </div>
    </div>
  );
}

export default function MetricStrip() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); observer.disconnect(); } },
      { threshold: 0.25 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  const metrics: Metric[] = [
    {
      value: "12.5K+",
      label: "VOICES ANALYZED",
      subtext: "Continuous acoustic telemetry",
      icon: Activity,
      color: "text-[#22D3EE]",
      numericValue: 12500,
      suffix: "+",
    },
    {
      value: "98.7%",
      label: "DETECTION CONFIDENCE",
      subtext: "Biological glottal precision",
      icon: ShieldCheck,
      color: "text-[#22C55E]",
      numericValue: 987,
      suffix: "%",
      prefix: "",
    },
    {
      value: "<15ms",
      label: "AVERAGE LATENCY",
      subtext: "Sub-audible edge inference",
      icon: Zap,
      color: "text-[#C084FC]",
    },
    {
      value: "347",
      label: "THREATS FLAGGED",
      subtext: "Synthetic clones blocked",
      icon: ShieldAlert,
      color: "text-[#F59E0B]",
      numericValue: 347,
    },
    {
      value: "99.9%",
      label: "SYSTEM AVAILABILITY",
      subtext: "Enterprise zero-trust SLA",
      icon: Cpu,
      color: "text-[#8B5CFF]",
    },
  ];

  // Fix display for percentage metrics
  const fixedMetrics = metrics.map(m => {
    if (m.numericValue === 987) {
      return { ...m, value: visible ? "98.7%" : "0%" };
    }
    return m;
  });

  return (
    <div ref={ref} className="w-full max-w-[1360px] mx-auto px-4 sm:px-6 my-10 sm:my-12">
      <div
        className={`w-full rounded-[22px] bg-[rgba(20,10,40,0.55)] border border-[rgba(160,100,255,0.18)] backdrop-blur-[18px] shadow-[0_20px_60px_rgba(0,0,0,0.35)] p-6 sm:p-8 transition-all duration-700 ${
          visible ? "opacity-100" : "opacity-0"
        }`}
      >
        <div className="grid grid-cols-2 md:grid-cols-5 gap-6 md:gap-0 md:divide-x md:divide-[rgba(160,100,255,0.12)]">
          {fixedMetrics.map((item, idx) => (
            <MetricItem key={idx} item={item} index={idx} visible={visible} />
          ))}
        </div>
      </div>
    </div>
  );
}
