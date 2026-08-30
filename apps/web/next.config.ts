import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output lets the Docker image ship only the traced server
  // bundle and its production dependencies, not the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
