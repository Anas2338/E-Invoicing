# FBR Invoice Portal Frontend

This is the frontend application for the FBR Invoice Portal, built with Next.js 16+ using the App Router architecture.

## Features

- Secure authentication with Better Auth
- Environment selection (Sandbox/Production)
- Dashboard with invoice statistics
- Invoice creation (Sale/Purchase)
- Invoice validation and posting
- Invoice history with search and filtering
- PDF download functionality
- Fully responsive design
- WCAG 2.1 AA compliant accessibility

## Tech Stack

- Next.js 16+ with App Router
- React 18+
- TypeScript
- Tailwind CSS for styling
- Zod for validation
- React Hook Form for form handling
- TanStack Query for data fetching
- Better Auth for authentication

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create a `.env.local` file in the frontend directory:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

3. Run the development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── (auth)/             # Authentication routes (login, register)
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (protected)/        # Protected routes for authenticated users
│   │   │   ├── dashboard/      # Dashboard with summary cards
│   │   │   ├── invoices/       # Invoice management pages
│   │   │   │   ├── create/     # Invoice creation forms
│   │   │   │   ├── validated/  # Validated invoices for posting
│   │   │   │   └── history/    # Invoice history and search
│   │   │   ├── settings/       # User settings and environment selection
│   │   │   └── layout.tsx      # Main protected layout
│   │   ├── globals.css         # Global styles
│   │   ├── layout.tsx          # Root layout
│   │   └── page.tsx            # Home page
│   ├── components/             # Reusable UI components
│   │   ├── ui/                 # Base UI components (buttons, inputs, etc.)
│   │   ├── forms/              # Form components and hooks
│   │   ├── auth/               # Authentication-related components
│   │   ├── invoices/           # Invoice-specific components
│   │   ├── dashboard/          # Dashboard widgets
│   │   └── common/             # Shared/common components
│   ├── hooks/                  # Custom React hooks
│   ├── lib/                    # Utility functions and constants
│   │   ├── auth/               # Authentication utilities
│   │   ├── api/                # API client and request utilities
│   │   ├── validation/         # Validation schemas and utilities
│   │   ├── types/              # TypeScript type definitions
│   │   └── utils/              # General utility functions
│   ├── providers/              # React context providers
│   │   ├── auth-provider.tsx   # Authentication context
│   │   └── theme-provider.tsx  # Theme/context provider
│   └── services/               # Business logic services
│       ├── auth-service.ts     # Authentication API service
│       ├── invoice-service.ts  # Invoice API service
│       └── user-service.ts     # User management service
├── public/                     # Static assets
├── types/                      # Global TypeScript definitions
├── tests/                      # Test files
├── package.json
├── tsconfig.json
├── next.config.js
└── tailwind.config.js
```

## Environment Variables

- `NEXT_PUBLIC_API_BASE_URL`: Base URL for the backend API
- `NEXT_PUBLIC_BACKEND_URL`: Base URL for the backend server

## Scripts

- `npm run dev` - Start the development server
- `npm run build` - Build the application for production
- `npm run start` - Start the production server
- `npm run lint` - Run ESLint
- `npm run test` - Run tests

## API Integration

The frontend communicates with the backend through a centralized API service layer located in `src/lib/api/api-client.ts`. All API calls follow RESTful conventions and include proper error handling.

## Authentication

Authentication is handled through the AuthProvider context. Protected routes check for authentication status and redirect unauthenticated users to the login page.

## License

This project is part of the FBR Invoice Portal system.