"use client";

import dynamic from "next/dynamic";

const WarRoomView = dynamic(() => import("@/warroom/WarRoomView"), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen bg-[#070a11] text-[#94a3b8] flex flex-col items-center justify-center font-mono text-sm">
      <div className="flex items-center gap-3">
        <span className="w-2.5 h-2.5 rounded-full bg-[#10b981] animate-ping" />
        <span>Initializing FalkorDB Operational Graph War Room...</span>
      </div>
    </div>
  ),
});

export default function WarRoomClientWrapper() {
  return <WarRoomView />;
}
