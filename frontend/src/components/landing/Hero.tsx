"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight, Book, Globe } from "lucide-react";
import { media } from "@/lib/media";
import { REPO_URL, DOCS_URL } from "@/lib/site";
import { Navbar } from "./Navbar";
import { HeroBackground } from "../ui/HeroBackground";

export const Hero: React.FC = () => {
  return (
    <section className="min-h-screen relative flex flex-col overflow-hidden justify-between">
      {/* Background with video/poster + rAF fade */}
      <HeroBackground poster={media.hero.poster} video={media.hero.video} />

      {/* Navbar */}
      <Navbar />

      {/* Center Hero Content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 py-12 text-center -translate-y-[20%] max-w-5xl mx-auto my-auto">
        <h1 className="text-6xl sm:text-7xl md:text-8xl lg:text-9xl text-white tracking-tight md:whitespace-nowrap font-display mb-8">
          Remember it <em className="italic">all</em>.
        </h1>

        {/* CTA Pill */}
        <Link
          href="/app"
          className="liquid-glass rounded-full pl-6 pr-2 py-2 flex items-center gap-3 max-w-xl w-full group hover:bg-white/5 transition-all mb-6"
        >
          <span className="text-white flex-1 text-left text-sm sm:text-base font-medium">
            Launch the War Room
          </span>
          <div className="bg-white rounded-full p-3 text-black transition-transform duration-300 group-hover:translate-x-1">
            <ArrowRight className="w-5 h-5" />
          </div>
        </Link>

        {/* Subtitle */}
        <p className="text-white text-sm leading-relaxed px-4 max-w-xl mb-6 opacity-90">
          The autonomous SRE crew with live operational graph memory. It
          remembers every outage, routes to the right expert when the lead is on
          leave, and refuses to trust its own stale memory.
        </p>

        {/* Secondary Scroll Button */}
        <a
          href="#problem"
          className="liquid-glass rounded-full px-8 py-3 text-white text-sm font-medium hover:bg-white/5 transition-colors"
        >
          See the stale-memory trap
        </a>
      </div>

      {/* Social Footer */}
      <div className="relative z-10 flex justify-center gap-4 pb-12">
        <a
          href={REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          title="GitHub Repository"
          className="liquid-glass rounded-full p-4 text-white/80 hover:text-white hover:bg-white/5 transition-all"
        >
          <svg
            className="w-5 h-5 fill-current"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            />
          </svg>
        </a>
        <a
          href={DOCS_URL}
          target="_blank"
          rel="noopener noreferrer"
          title="Documentation"
          className="liquid-glass rounded-full p-4 text-white/80 hover:text-white hover:bg-white/5 transition-all"
        >
          <Book className="w-5 h-5" />
        </a>
        <Link
          href="/app"
          title="War Room"
          className="liquid-glass rounded-full p-4 text-white/80 hover:text-white hover:bg-white/5 transition-all"
        >
          <Globe className="w-5 h-5" />
        </Link>
      </div>
    </section>
  );
};
