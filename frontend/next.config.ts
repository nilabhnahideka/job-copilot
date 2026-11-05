/**
 * Next.js configuration. `standalone` output keeps the Docker image small.
 */
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Small self-contained server bundle for Docker
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
