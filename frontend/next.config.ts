import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  turbopack: {
    root: import.meta.dirname,
  },
  // Hide the floating Next.js dev indicator so it does not cover the UI.
  devIndicators: false,
  // Let phones/laptops on the local network use the dev server (otherwise buttons do nothing).
  allowedDevOrigins: ["192.168.0.*"],
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

export default nextConfig;
