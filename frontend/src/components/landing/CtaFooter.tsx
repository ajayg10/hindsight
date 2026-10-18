"use client";

import React, { useRef } from "react";
import Link from "next/link";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { REPO_URL } from "@/lib/site";

export const CtaFooter: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });
  const reducedMotion = useReducedMotion();

  return (
    <footer className="bg-black pt-20 md:pt-32 pb-12 px-6 overflow-hidden border-t border-white/5">
      <div className="max-w-6xl mx-auto flex flex-col items-center text-center" ref={ref}>
        {/* Call to Action */}
        <motion.h2
          initial={reducedMotion ? {} : { opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8 }}
          className="text-4xl sm:text-5xl md:text-7xl text-white font-display tracking-tight mb-8"
        >
          Watch it refuse the wrong runbook.
        </motion.h2>

        <motion.div
          initial={reducedMotion ? {} : { opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.15 }}
          className="mb-20 md:mb-28"
        >
          <Link
            href="/app"
            className="liquid-glass rounded-full px-8 py-3 text-white text-sm font-medium hover:bg-white/10 transition-colors inline-block"
          >
            Launch the War Room
          </Link>
        </motion.div>

        {/* Slim Footer */}
        <div className="w-full flex flex-col md:flex-row items-center justify-between gap-4 text-white/40 text-xs pt-8 border-t border-white/10">
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
            <span className="font-semibold text-white/70">Hindsight</span>
            <span aria-hidden="true">&bull;</span>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white transition-colors underline"
            >
              View on GitHub
            </a>
            <span aria-hidden="true">&bull;</span>
            <span>Open source under Apache 2.0</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-2 text-center md:text-right">
            <span>
              Built with{" "}
              <a
                href="https://www.falkordb.com"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-white transition-colors underline"
              >
                FalkorDB
              </a>
            </span>
          </div>
        </div>

        {/* Attribution Footnote */}
        <p className="text-white/25 text-[11px] leading-relaxed mt-4 max-w-3xl text-center">
          Topology adapted from Google Online Boutique and Weaveworks Sock Shop (Apache 2.0).
          All incidents, ADRs and people are synthetic.
        </p>
      </div>
    </footer>
  );
};