"use client";

import React, { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { motion, useReducedMotion } from "framer-motion";

interface HeroBackgroundProps {
  poster: string;
  video: string | null;
}

export const HeroBackground: React.FC<HeroBackgroundProps> = ({
  poster,
  video,
}) => {
  const [hasError, setHasError] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const cancelRafRef = useRef<(() => void) | null>(null);
  const isFadingOutRef = useRef(false);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (!video || hasError) return;

    const vid = videoRef.current;
    if (!vid) return;

    const fade = (
      startVal: number,
      targetVal: number,
      duration: number,
      cb?: () => void
    ) => {
      if (cancelRafRef.current) {
        cancelRafRef.current();
        cancelRafRef.current = null;
      }
      if (reducedMotion) {
        vid.style.opacity = targetVal.toString();
        if (cb) cb();
        return;
      }

      let startTs: number | null = null;
      let rafId: number;

      const step = (ts: number) => {
        if (!startTs) startTs = ts;
        const elapsed = ts - startTs;
        const progress = Math.min(elapsed / duration, 1);
        const curr = startVal + (targetVal - startVal) * progress;
        vid.style.opacity = curr.toFixed(3);

        if (progress < 1) {
          rafId = requestAnimationFrame(step);
        } else {
          vid.style.opacity = targetVal.toString();
          if (cb) cb();
        }
      };

      rafId = requestAnimationFrame(step);
      cancelRafRef.current = () => cancelAnimationFrame(rafId);
    };

    const handleCanPlay = () => {
      vid.play().catch(() => {});
      fade(0, 1, 500);
    };

    const handleTimeUpdate = () => {
      if (!vid.duration || isNaN(vid.duration)) return;
      const remaining = vid.duration - vid.currentTime;
      if (!isFadingOutRef.current && remaining <= 0.55 && remaining > 0) {
        isFadingOutRef.current = true;
        const currentOpacity = parseFloat(vid.style.opacity) || 1;
        fade(currentOpacity, 0, 500);
      }
    };

    const handleEnded = () => {
      isFadingOutRef.current = false;
      vid.style.opacity = "0";
      setTimeout(() => {
        if (!videoRef.current) return;
        videoRef.current.currentTime = 0;
        videoRef.current
          .play()
          .then(() => {
            if (videoRef.current) fade(0, 1, 500);
          })
          .catch(() => {});
      }, 100);
    };

    vid.addEventListener("canplay", handleCanPlay);
    vid.addEventListener("timeupdate", handleTimeUpdate);
    vid.addEventListener("ended", handleEnded);

    return () => {
      vid.removeEventListener("canplay", handleCanPlay);
      vid.removeEventListener("timeupdate", handleTimeUpdate);
      vid.removeEventListener("ended", handleEnded);
      if (cancelRafRef.current) {
        cancelRafRef.current();
      }
    };
  }, [video, hasError, reducedMotion]);

  const showOnlyPoster = !video || hasError;

  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden bg-black pointer-events-none select-none">
      {/* Fallback & Loading Poster under bg-black/40 */}
      <div className="absolute inset-0 w-full h-full z-0">
        {showOnlyPoster ? (
          <motion.div
            className="w-full h-full relative"
            animate={
              reducedMotion
                ? {}
                : {
                    scale: [1, 1.04, 1],
                  }
            }
            transition={{
              duration: 20,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          >
            <Image
              src={poster}
              alt=""
              fill
              priority
              className="object-cover object-bottom"
            />
          </motion.div>
        ) : (
          <Image
            src={poster}
            alt=""
            fill
            priority
            className="object-cover object-bottom"
          />
        )}
      </div>

      {/* Crossfade Black Layer */}
      <div className="absolute inset-0 bg-black/40 z-[1]" />

      {/* Video Element */}
      {!showOnlyPoster && (
        <video
          ref={videoRef}
          src={video}
          poster={poster}
          muted
          autoPlay
          playsInline
          preload="auto"
          onError={() => setHasError(true)}
          className="absolute inset-0 w-full h-full object-cover object-bottom z-[2]"
          style={{ opacity: 0 }}
        />
      )}

      {/* Legibility Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black z-[3]" />
    </div>
  );
};
