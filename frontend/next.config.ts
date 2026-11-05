/**
 * Next.js configuration. `standalone` output keeps the Docker image small.
 */
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Small self-contained server bundle for Docker
  output: "standalone",
  // The resume page moved into the profile page.
  async redirects() {
    return [{ source: "/resume", destination: "/profile#resume", permanent: false }];
  },
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
