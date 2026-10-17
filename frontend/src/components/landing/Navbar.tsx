"use client";

import React from "react";
import Link from "next/link";
import { Globe } from "lucide-react";
import { REPO_URL } from "@/lib/site";

export const Navbar: React.FC = () => {
  return (
    <nav className="relative z-20 px-6 py-6 w-full">
      <div className="liquid-glass rounded-full max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
        {/* Left: Brand + Navigation Links */}
        <div className="flex items-center">
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
        <div className="flex items-center gap-6">
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
            className="liquid-glass rounded-full px-6 py-2 text-white text-sm font-medium hover:bg-white/10 transition-colors"
          >
            Launch App
          </Link>
        </div>
      </div>
    </nav>
  );
};
