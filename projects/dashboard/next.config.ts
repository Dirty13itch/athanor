import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.PLAYWRIGHT_NEXT_DIST_DIR || undefined,
  output: "standalone",
};

export default nextConfig;
