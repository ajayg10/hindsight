import React from "react";
import { Hero } from "@/components/landing/Hero";
import { AboutSection } from "@/components/landing/AboutSection";
import { FeaturedSection } from "@/components/landing/FeaturedSection";
import { PhilosophySection } from "@/components/landing/PhilosophySection";
import { ServicesSection } from "@/components/landing/ServicesSection";
import { StatsStrip } from "@/components/landing/StatsStrip";
import { CtaFooter } from "@/components/landing/CtaFooter";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-black text-white selection:bg-white/20 selection:text-white">
      <Hero />
      <AboutSection />
      <FeaturedSection />
      <PhilosophySection />
      <ServicesSection />
      <StatsStrip />
      <CtaFooter />
    </main>
  );
}
