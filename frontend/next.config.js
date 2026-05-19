// @ts-check

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  typedRoutes: true,
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
    NEXT_PUBLIC_AI_AGENT_API_URL: process.env.NEXT_PUBLIC_AI_AGENT_API_URL,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'http',
        hostname: '127.0.0.1',
      },
    ],
  },
  // Proxy API requests to backend to avoid CORS and cookie issues
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';
    const aiAgentUrl = process.env.NEXT_PUBLIC_AI_AGENT_API_URL || 'http://localhost:8002/api/v1';
    return [
      {
        source: '/api/v1/automation/:path*',
        destination: `${aiAgentUrl}/automation/:path*`,
      },
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
  // SECURITY: Add security headers including Content Security Policy
  async headers() {
    const isDevelopment = process.env.NODE_ENV === 'development';
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';

    // Extract AI agent origin for CSP (CSP path matching can fail with proxies/redirects)
    const aiAgentUrl = process.env.NEXT_PUBLIC_AI_AGENT_API_URL || 'http://localhost:8002/api/v1';
    const aiAgentOrigin = (() => {
      try { return new URL(aiAgentUrl).origin; } catch { return aiAgentUrl; }
    })();

    // CSP directives
    const cspDirectives = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' 'unsafe-inline'", // Next.js requires unsafe-eval and unsafe-inline
      "style-src 'self' 'unsafe-inline'", // Tailwind requires unsafe-inline
      "img-src 'self' data: https:",
      "font-src 'self' data:",
      "media-src 'self' data:", // Allow audio/video data URIs
      `connect-src 'self' https://localhost:8001 http://localhost:8001 https://localhost:8002 http://localhost:8002 ${backendUrl} ${aiAgentOrigin}`, // API connections to both backends
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ];

    // Only upgrade to HTTPS in production
    if (!isDevelopment) {
      cspDirectives.push("upgrade-insecure-requests");
    }

    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: cspDirectives.join('; ')
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()'
          }
        ],
      },
    ];
  },
};

module.exports = nextConfig;