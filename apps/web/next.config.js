const apiPort = process.env.API_PORT || "8042";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `http://127.0.0.1:${apiPort}/v1/:path*`,
      },
      {
        source: "/api/admin/:path*",
        destination: `http://127.0.0.1:${apiPort}/admin/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
