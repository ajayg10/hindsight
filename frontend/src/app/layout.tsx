import type { Metadata, Viewport } from "next";
import { REPO_URL } from "@/lib/site";
import "./globals.css";

const inter = { variable: "font-sans" };
const instrumentSerif = { variable: "font-serif" };

export const viewport: Viewport = {
  themeColor: "#000000",
};

export const metadata: Metadata = {
  metadataBase: new URL(REPO_URL),
  title: "Hindsight — The Autonomous SRE Crew",
  description:
    "The Autonomous SRE Crew with Live Operational Graph Memory. It remembers every outage, routes to the right expert when the lead is on leave, and refuses to trust its own stale memory.",
  openGraph: {
    title: "Hindsight — The Autonomous SRE Crew",
    description:
      "The Autonomous SRE Crew with Live Operational Graph Memory. It remembers every outage, routes to the right expert when the lead is on leave, and refuses to trust its own stale memory.",
    images: [
      {
        url: "/images/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "Hindsight Operational Graph Network",
      },
    ],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Hindsight — The Autonomous SRE Crew",
    description:
      "The Autonomous SRE Crew with Live Operational Graph Memory. It remembers every outage, routes to the right expert when the lead is on leave, and refuses to trust its own stale memory.",
    images: ["/images/og-image.jpg"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${instrumentSerif.variable}`}>
      <body className="bg-black text-white antialiased selection:bg-white/20 selection:text-white">
        {children}
      </body>
    </html>
  );
}
