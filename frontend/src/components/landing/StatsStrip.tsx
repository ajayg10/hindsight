"use client";

import React, { useRef } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { DOCS_URL } from "@/lib/site";

export const StatsStrip: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });
  const reducedMotion = useReducedMotion();

  const stats = [
    {
      value: "58",
      label: "microservices modeled",
    },
    {
      value: "0.385 ms",
      label: "p50 multi-hop traversal",
    },
    {
      value: "0",
      label: "double-claims under race",
    },
    {
      value: "100%",
      label: "top-3 root-cause accuracy (N=18)",
    },
  ];

  return (
    <section className="bg-black py-16 md:py-24 px-6 overflow-hidden">
      <div className="max-w-6xl mx-auto" ref={ref}>
        {/* 4 Stat Tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mb-8">
          {stats.map((stat, idx) => (
            <motion.div
              key={stat.label}
              initial={reducedMotion ? {} : { opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: idx * 0.1 }}
              className="liquid-glass rounded-2xl p-6 md:p-8 flex flex-col justify-center"
            >
              <div className="text-4xl md:text-5xl text-white font-display mb-2 tracking-tight">
                {stat.value}
              </div>
              <div className="text-white/40 text-xs tracking-widest uppercase">
                {stat.label}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Footnote */}
        <motion.p
          initial={reducedMotion ? {} : { opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-white/30 text-xs text-center md:text-left"
        >
          Benchmarks run on a synthetic topology and synthetic incident storms (seed=42). See{" "}
          <a
            href={`${DOCS_URL}/VERIFIED.md`}
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-white/60 transition-colors"
          >
            docs/VERIFIED.md
          </a>
          .
        </motion.p>
      </div>
    </section>
  );
};
