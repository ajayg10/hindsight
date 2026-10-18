"use client";

import React, { useRef } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { media } from "@/lib/media";
import { MediaBlock } from "../ui/MediaBlock";

export const PhilosophySection: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const reducedMotion = useReducedMotion();

  return (
    <section id="graph" className="bg-black py-28 md:py-40 px-6 overflow-hidden">
      <div className="max-w-6xl mx-auto" ref={ref}>
        {/* Section Heading */}
        <motion.h2
          initial={reducedMotion ? {} : { opacity: 0, y: 40 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8 }}
          className="text-5xl md:text-7xl lg:text-8xl text-white tracking-tight mb-16 md:mb-24 font-display"
        >
          Memory <em className="italic text-white/40">x</em> Judgment
        </motion.h2>

        {/* 2-Column Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
          {/* Left Media Block */}
          <motion.div
            initial={reducedMotion ? {} : { opacity: 0, x: -40 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="rounded-3xl overflow-hidden aspect-[4/3] relative"
          >
            <MediaBlock
              poster={media.philosophy.poster}
              video={media.philosophy.video}
              alt="Memory Strata Knowledge Layering"
            />
          </motion.div>

          {/* Right Narrative Blocks */}
          <motion.div
            initial={reducedMotion ? {} : { opacity: 0, x: 40 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="flex flex-col justify-center"
          >
            {/* Block 1 */}
            <div>
              <p className="text-white/40 text-xs tracking-widest uppercase mb-4">
                Remembers everything
              </p>
              <p className="text-white/70 text-base md:text-lg leading-relaxed">
                Episodic memory of every incident, architectural memory of every
                ADR, RFC and migration, and social memory of who actually knows
                what. All of it lives in one live operational graph, not a pile of
                text chunks.
              </p>
            </div>

            {/* Divider */}
            <div className="w-full h-px bg-white/10 my-8" />

            {/* Block 2 */}
            <div>
              <p className="text-white/40 text-xs tracking-widest uppercase mb-4">
                Knows when to refuse
              </p>
              <p className="text-white/70 text-base md:text-lg leading-relaxed">
                When a runbook has been invalidated by an architecture change,
                Hindsight says no. When a fix would touch more than five services
                or put over $1,000 a minute at risk, it stops and asks a human.
                When the expert is on leave, it pages the next best peer.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
