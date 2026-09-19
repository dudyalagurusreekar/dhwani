import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DHWANI EchoShield AI — Real-Time Voice Deepfake & Synthetic Speech Detection",
  description:
    "Enterprise AI voice security platform. Detect synthetic voices, voice cloning, and deepfake audio in under 15ms with military-grade acoustic forensics.",
  keywords: "voice deepfake detection, AI voice security, synthetic speech detection, voice clone protection, EchoShield",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full scroll-smooth">
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-full flex flex-col bg-[#05020D] text-[#F8F7FF] antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
