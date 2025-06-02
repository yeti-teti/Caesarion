// /** @type {import('next').NextConfig} */
// const nextConfig = {
//   rewrites: async () => {
//     return [
//       {
//         source: "/api/:path*",
//         destination:
//           process.env.NODE_ENV === "development"
//             ? "http://127.0.0.1:8000/api/:path*"
//             : "/api/",
//       },
//       {
//         source: "/docs",
//         destination:
//           process.env.NODE_ENV === "development"
//             ? "http://127.0.0.1:8000/docs"
//             : "/api/docs",
//       },
//       {
//         source: "/openapi.json",
//         destination:
//           process.env.NODE_ENV === "development"
//             ? "http://127.0.0.1:8000/openapi.json"
//             : "/api/openapi.json",
//       },
//     ];
//   },
// };

// module.exports = nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable resource-intensive features during build
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  
  // Disable source maps in production (saves memory & time)
  productionBrowserSourceMaps: false,
  
  // Disable telemetry
  telemetry: false,
  
  // Optimize images (but disable during build if causing issues)
  images: {
    unoptimized: true, // Disable image optimization during build
  },
  
  // Disable SWC minification if causing issues (use terser instead)
  swcMinify: false,
  
  // Reduce bundle analysis
  experimental: {
    optimizeCss: false, // Disable CSS optimization if using Tailwind
  },
  
  rewrites: async () => {
    return [
      {
        source: "/api/:path*",
        destination:
          process.env.NODE_ENV === "development"
            ? "http://127.0.0.1:8000/api/:path*"
            : "http://api:8000/api/:path*",  // Use internal service
      },
      {
        source: "/docs",
        destination:
          process.env.NODE_ENV === "development"
            ? "http://127.0.0.1:8000/docs"
            : "http://api:8000/docs",  // Use internal service
      },
      {
        source: "/openapi.json",
        destination:
          process.env.NODE_ENV === "development"
            ? "http://127.0.0.1:8000/openapi.json"
            : "http://api:8000/openapi.json",  // Use internal service
      },
    ];
  },
};

module.exports = nextConfig;