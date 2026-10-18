import type { Metadata } from "next";
import "@/warroom/war-room.css";

export const metadata: Metadata = {
  title: "Hindsight War Room",
  description:
    "Autonomous incident coordination and organizational memory powered by FalkorDB. Connected Data, Memory & Coordination, Company Brain.",
};

export default function WarRoomLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
