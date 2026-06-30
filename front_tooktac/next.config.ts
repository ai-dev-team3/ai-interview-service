import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: false,
  output: "standalone",
  images: {
    unoptimized: true,
  },
  typescript: {
    // ignoreBuildErrors: true,
  },
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    config.module.rules.push({
      test: /pdf\.worker(\.min)?\.mjs$/,
      type: 'asset/resource',
      generator: { filename: 'static/chunks/[name][ext]' },
    });
    return config;
  },
};

export default nextConfig;
