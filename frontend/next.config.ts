import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  turbopack: {
    root: import.meta.dirname,
  },
  // Hide the floating Next.js dev indicator so it does not cover the UI.
  devIndicators: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

export default nextConfig;
