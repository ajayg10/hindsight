"use client";

import React, { useRef } from "react";
import Link from "next/link";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { media } from "@/lib/media";
import { MediaBlock } from "../ui/MediaBlock";

export const FeaturedSection: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const reducedMotion = useReducedMotion();

  return (
    <section className="bg-black pt-6 md:pt-10 pb-20 md:pb-32 px-6 overflow-hidden">
      <div className="max-w-6xl mx-auto" ref={ref}>
        <motion.div
          initial={reducedMotion ? {} : { opacity: 0, y: 60 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.9 }}
          className="relative rounded-3xl overflow-hidden aspect-video"
        >
          {/* Media Player / Fallback */}
          <MediaBlock
            poster={media.featured.poster}
            video={media.featured.video}
            className="w-full h-full object-cover"
            alt="The Stale Memory Trap Topology"
          />

          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent pointer-events-none" />

          {/* Bottom Card & Action */}
          <div className="absolute bottom-0 left-0 right-0 p-6 md:p-10 flex flex-col md:flex-row md:items-end md:justify-between gap-6 z-10">
            {/* Left Stale Memory Card */}
            <div className="liquid-glass rounded-2xl p-6 md:p-8 max-w-md">
              <p className="text-white/50 text-xs tracking-widest uppercase mb-3">
                The Stale Memory Trap
              </p>
              <p className="text-white text-sm md:text-base leading-relaxed">
                Keyword search recommends runbook R-7 at a 94% match, but ADR-17
                retired its cache cluster six days ago. Hindsight&apos;s graph
                sees the INVALIDATED_BY edge and refuses to run it.
              </p>
            </div>

            {/* Right Action Button */}
            <motion.div
              whileHover={reducedMotion ? {} : { scale: 1.05 }}
              whileTap={reducedMotion ? {} : { scale: 0.95 }}
            >
              <Link
                href="/app"
                className="liquid-glass rounded-full px-8 py-3 text-white text-sm font-medium inline-block hover:bg-white/10 transition-colors"
              >
                Open the War Room
              </Link>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};
