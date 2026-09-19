"use client";

import React, { useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";

interface WaveformProps {
  isAnalyzing?: boolean;
  variant?: "hero" | "compact";
}

export default function WaveformVisualizer({
  isAnalyzing = true,
  variant = "hero",
}: WaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [activeFrequency, setActiveFrequency] = useState(48.2);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;
    const barCount = variant === "compact" ? 24 : 48;

    const render = () => {
      time += 0.04;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;
      const barWidth = (width / barCount) * 0.65;
      const gap = (width / barCount) * 0.35;

      for (let i = 0; i < barCount; i++) {
        const wave1 = Math.sin(time * 2.5 + i * 0.22);
        const wave2 = Math.cos(time * 1.8 + i * 0.45) * 0.5;
        const wave3 = Math.sin(time * 3.8 + i * 0.12) * 0.3;
        const jitter = isAnalyzing ? Math.sin(time * 8 + i) * 0.15 : 0;
        const rawAmp = Math.abs(wave1 + wave2 + wave3 + jitter);
        const barHeight = Math.max(6, rawAmp * (height * 0.44));

        const x = i * (barWidth + gap) + gap / 2;

        // Gradient using DHWANI palette: Cyber Blue → Neon Purple
        const gradient = ctx.createLinearGradient(0, centerY - barHeight, 0, centerY + barHeight);
        gradient.addColorStop(0, "#22D3EE");   // --dhwani-cyber
        gradient.addColorStop(0.5, "#A855F7"); // --dhwani-purple
        gradient.addColorStop(1, "#0EA5E9");   // --dhwani-deep-blue

        ctx.fillStyle = gradient;
        ctx.shadowColor = "#A855F7";
        ctx.shadowBlur = 6;

        const topY = centerY - barHeight / 2;
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(x, topY, barWidth, barHeight, 3);
        } else {
          ctx.rect(x, topY, barWidth, barHeight);
        }
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    const interval = setInterval(() => {
      setActiveFrequency(+(47 + Math.random() * 2.4).toFixed(1));
    }, 1500);

    return () => {
      cancelAnimationFrame(animationFrameId);
      clearInterval(interval);
    };
  }, [isAnalyzing, variant]);

  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="flex items-center justify-between text-xs text-[#94A3B8] px-1 font-mono">
        <span className="flex items-center gap-1.5 text-[#22D3EE] font-semibold tracking-wide uppercase">
          <Activity className="w-3.5 h-3.5 text-[#22D3EE] animate-pulse" />
          Acoustic Spectrum Stream
        </span>
        <span className="text-[#A855F7]/80 font-mono">
          {activeFrequency} kHz / 24-bit Flac
        </span>
      </div>

      <div className="relative w-full h-16 rounded-xl bg-[#080F1A] border border-[#22D3EE]/15 px-3 py-1 overflow-hidden backdrop-blur-md">
        {/* Scan line */}
        <div className="absolute inset-y-0 w-0.5 bg-[#22D3EE]/70 blur-[1px] shadow-[0_0_10px_#22D3EE] animate-scan pointer-events-none" />

        <canvas
          ref={canvasRef}
          width={480}
          height={64}
          className="w-full h-full block"
        />
      </div>
    </div>
  );
}
