import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  ...(isProd
    ? {
        output: "export",
      }
    : {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: "http://localhost:8000/api/:path*",
            },
            {
              source: "/mcp/:path*",
              destination: "http://localhost:8000/mcp/:path*",
            },
            {
              source: "/mcp",
              destination: "http://localhost:8000/mcp",
            },
            {
              source: "/health",
              destination: "http://localhost:8000/health",
            },
          ];
        },
      }),
};

export default nextConfig;
