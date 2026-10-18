"use client";

import React, { useRef } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { media } from "@/lib/media";
import { MediaBlock } from "../ui/MediaBlock";

export const ServicesSection: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const reducedMotion = useReducedMotion();

  const services = [
    {
      media: media.serviceA,
      tag: "Connected data",
      title: "Operational Graph Reasoning",
      description:
        "Multi-hop dependency traversal across 58 microservices in under a millisecond, with betweenness and PageRank flagging choke points and WCC splitting alert storms into separate failure domains.",
      alt: "Operational Graph Reasoning Visualization",
    },
    {
      media: media.serviceB,
      tag: "Coordination",
      title: "Zero-Mutex Agent Crew",
      description:
        "Six agents claim tasks through atomic Cypher state machines with zero double-claims under 32 concurrent workers, resolve disagreements by graph subsumption, and pause at a human approval gate for risky actions.",
      alt: "Zero-Mutex Agent Crew Consensus Visualization",
    },
  ];

  return (
    <section id="crew" className="relative bg-black py-28 md:py-40 px-6 overflow-hidden">
      {/* Radial overlay */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(255,255,255,0.02)_0%,_transparent_60%)] pointer-events-none" />

      <div className="relative z-10 max-w-6xl mx-auto" ref={ref}>
        {/* Header Row */}
        <motion.div
          initial={reducedMotion ? {} : { opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="flex items-end justify-between mb-12 md:mb-16"
        >
          <h2 className="text-3xl md:text-5xl text-white tracking-tight font-display">
            What the crew does
          </h2>
          <span className="text-white/40 text-sm hidden md:block">
            Autonomous SRE crew
          </span>
        </motion.div>

        {/* 2-Card Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
          {services.map((service, idx) => (
            <motion.div
              key={service.tag}
              initial={reducedMotion ? {} : { opacity: 0, y: 50 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.8, delay: idx * 0.15 }}
              className="liquid-glass rounded-3xl overflow-hidden group flex flex-col justify-between"
            >
              {/* Media Area */}
              <div className="relative aspect-video overflow-hidden">
                <MediaBlock
                  poster={service.media.poster}
                  video={service.media.video}
                  className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                  alt={service.alt}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent pointer-events-none" />
              </div>

              {/* Body */}
              <div className="p-6 md:p-8 flex flex-col justify-between flex-1">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="uppercase tracking-widest text-white/40 text-xs">
                      {service.tag}
                    </span>
                    <div className="liquid-glass rounded-full p-2 text-white/80 group-hover:text-white transition-colors">
                      <ArrowUpRight className="w-4 h-4" />
                    </div>
                  </div>
                  <h3 className="text-white text-xl md:text-2xl mb-3 tracking-tight font-display">
                    {service.title}
                  </h3>
                  <p className="text-white/50 text-sm leading-relaxed">
                    {service.description}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
