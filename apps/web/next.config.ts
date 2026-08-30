import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output lets the Docker image ship only the traced server
  // bundle and its production dependencies, not the full node_modules tree.
  // Vercel performs its own tracing and fails if standalone output replaces
  // the files its packaging step expects.
  output: process.env.VERCEL === "1" ? undefined : "standalone",
};

export default nextConfig;
