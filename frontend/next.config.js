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