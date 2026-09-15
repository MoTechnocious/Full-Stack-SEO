/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: {
    // `npm run lint` still runs the full ESLint config; kept out of the
    // production build so a style-only rule can never block a deploy.
    ignoreDuringBuilds: true,
  },
};

module.exports = nextConfig;
