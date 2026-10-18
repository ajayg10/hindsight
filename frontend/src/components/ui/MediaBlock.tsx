"use client";

import React, { useState } from "react";
import Image from "next/image";

interface MediaBlockProps {
  poster: string;
  video: string | null;
  className?: string;
  alt?: string;
}

export const MediaBlock: React.FC<MediaBlockProps> = ({
  poster,
  video,
  className = "w-full h-full object-cover",
  alt = "Hindsight media asset",
}) => {
  const [hasError, setHasError] = useState(false);

  if (!video || hasError) {
    return (
      <div className="relative w-full h-full overflow-hidden">
        <Image
          src={poster}
          alt={alt}
          fill
          className={className}
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 80vw, 1200px"
        />
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-black">
      <video
        src={video}
        poster={poster}
        muted
        autoPlay
        loop
        playsInline
        preload="auto"
        onError={() => setHasError(true)}
        className={className}
      />
    </div>
  );
};
