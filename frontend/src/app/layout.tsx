import type { Metadata, Viewport } from "next";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

const inter = { variable: "font-sans" };
const instrumentSerif = { variable: "font-serif" };

export const viewport: Viewport = {
  themeColor: "#000000",
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Hindsight — The Autonomous SRE Crew",
  description:
    "The Autonomous SRE Crew with live operational graph memory. Remembers every outage, routes to the right expert, and avoids stale-memory traps.",
  openGraph: {
    siteName: "Hindsight",
    title: "Hindsight — The Autonomous SRE Crew",
    description:
      "The Autonomous SRE Crew with live operational graph memory. Remembers every outage, routes to the right expert, and avoids stale-memory traps.",
    url: SITE_URL,
    images: [
      {
        url: "/images/og-image.jpg",
        width: 1024,
        height: 464,
        alt: "Hindsight — Remember it all",
      },
    ],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Hindsight — The Autonomous SRE Crew",
    description:
      "The Autonomous SRE Crew with live operational graph memory. Remembers every outage, routes to the right expert, and avoids stale-memory traps.",
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
