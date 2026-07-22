import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["*.agent.alibaba-inc.com"],

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8002/api/:path*",
      },
    ];
  },
};

export default nextConfig;
