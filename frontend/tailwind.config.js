/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'hsl(222.2 47.4% 11.2%)', // slate-900 equivalent
          foreground: 'hsl(0 0% 98%)' // slate-50 equivalent
        },
        secondary: {
          DEFAULT: 'hsl(210 40% 96.1%)', // slate-100 equivalent
          foreground: 'hsl(222.2 47.4% 11.2%)' // slate-900 equivalent
        },
        destructive: {
          DEFAULT: 'hsl(0 84.2% 60.2%)', // red-500 equivalent
          foreground: 'hsl(0 0% 98%)' // red-50 equivalent
        },
        muted: {
          DEFAULT: 'hsl(210 40% 96.1%)', // slate-100 equivalent
          foreground: 'hsl(215.4 16.3% 46.9%)' // slate-500 equivalent
        },
        accent: {
          DEFAULT: 'hsl(210 40% 96.1%)', // slate-100 equivalent
          foreground: 'hsl(222.2 47.4% 11.2%)' // slate-900 equivalent
        },
        card: {
          DEFAULT: 'hsl(0 0% 100%)', // white
          foreground: 'hsl(222.2 47.4% 11.2%)' // slate-900 equivalent
        },
        popover: {
          DEFAULT: 'hsl(0 0% 100%)', // white
          foreground: 'hsl(222.2 47.4% 11.2%)' // slate-900 equivalent
        },
        border: 'hsl(214.3 31.8% 91.4%)', // slate-200 equivalent
        input: {
          DEFAULT: 'hsl(214.3 31.8% 91.4%)', // slate-200 equivalent
          placeholder: 'hsl(215.4 16.3% 46.9%)' // slate-500 equivalent for placeholder
        },
        ring: 'hsl(222.2 47.4% 11.2%)', // slate-900 equivalent
        background: 'hsl(0 0% 100%)', // white
        foreground: 'hsl(222.2 47.4% 11.2%)', // slate-900 equivalent
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}