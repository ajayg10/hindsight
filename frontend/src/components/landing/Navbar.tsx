"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Globe } from "lucide-react";
import { REPO_URL } from "@/lib/site";

export const Navbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    // fixed = always pinned to the viewport, independent of any parent's overflow.
    // pointer-events-none on the full-width strip so it never blocks clicks beside the pill.
    <nav className="fixed top-0 inset-x-0 z-50 px-4 sm:px-6 py-4 pointer-events-none">
      <div
        className="liquid-glass pointer-events-auto rounded-full max-w-5xl mx-auto px-4 sm:px-6 py-2.5 sm:py-3 flex items-center justify-between"
        // Inline style so it beats the unlayered .liquid-glass rule in globals.css
        style={
          scrolled
            ? {
                backdropFilter: "blur(16px)",
                WebkitBackdropFilter: "blur(16px)",
              }
            : undefined
        }
      >
        {/* Tint layer: fades in after scrolling so the links stay readable over any section */}
        <span
          aria-hidden="true"
          className={`pointer-events-none absolute inset-0 rounded-full bg-black/55 transition-opacity duration-300 ${
            scrolled ? "opacity-100" : "opacity-0"
          }`}
        />

        {/* Left: Brand + Navigation Links */}
        <div className="relative flex items-center">
          <Link
            href="/"
            className="flex items-center gap-2.5 text-white hover:opacity-90 transition-opacity"
          >
            <Globe className="w-6 h-6 text-white" />
            <span className="font-semibold text-lg tracking-tight">
              Hindsight
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-8 ml-8">
            <a
              href="#problem"
              className="text-white/80 hover:text-white text-sm font-medium transition-colors"
            >
              Problem
            </a>
            <a
              href="#graph"
              className="text-white/80 hover:text-white text-sm font-medium transition-colors"
            >
              Graph
            </a>
            <a
              href="#crew"
              className="text-white/80 hover:text-white text-sm font-medium transition-colors"
            >
              Crew
            </a>
          </div>
        </div>

        {/* Right: GitHub & Launch App */}
        <div className="relative flex items-center gap-3 sm:gap-6">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-white text-sm font-medium hover:text-white/80 transition-colors"
          >
            GitHub
          </a>
          <Link
            href="/app"
            className="liquid-glass rounded-full px-5 sm:px-6 py-2 text-white text-sm font-medium hover:bg-white/10 transition-colors"
          >
            Launch App
          </Link>
        </div>
      </div>
    </nav>
  );
};