import type { Config } from 'tailwindcss';
import animate from 'tailwindcss-animate';

/**
 * GovLink — Tailwind theme
 * ------------------------------------------------------------------
 * Colors are wired through CSS custom properties (defined in
 * tokens.css) so the dark-mode toggle on <html data-theme="..."> is
 * authoritative. Don't add hard-coded hex values to className strings;
 * extend this config instead.
 *
 * Pairs with shadcn/ui — see handoff.html for the per-component
 * primitive mapping.
 */
const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: 'var(--gutter-mobile)',
        md: 'var(--gutter-tablet)',
        lg: 'var(--gutter-desktop)',
      },
      screens: {
        '2xl': 'var(--content-max)',
      },
    },
    screens: {
      // CSS variables aren't valid inside @media queries — keep these
      // as literal values; mirror the --bp-* tokens from tokens.css.
      sm: '640px',
      md: '768px',     // --bp-tablet
      lg: '1024px',    // --bp-desktop
      xl: '1280px',    // --bp-wide
      '2xl': '1440px',
    },
    extend: {
      colors: {
        canvas:    'var(--canvas)',
        surface:   'var(--surface)',
        'surface-2': 'var(--surface-2)',
        ink:       'var(--ink)',
        'ink-2':   'var(--ink-2)',
        'ink-3':   'var(--ink-3)',
        rule:      'var(--rule)',
        'rule-2':  'var(--rule-2)',
        accent: {
          DEFAULT: 'var(--accent)',
          hover:   'var(--accent-hover)',
          tint:    'var(--accent-tint)',
        },
        success: 'var(--success)',
        warning: 'var(--warning)',
        danger:  'var(--danger)',
        ramp: {
          1: 'var(--ramp-1)',
          2: 'var(--ramp-2)',
          3: 'var(--ramp-3)',
          4: 'var(--ramp-4)',
          5: 'var(--ramp-5)',
        },
        cat: {
          1: 'var(--cat-1)',
          2: 'var(--cat-2)',
          3: 'var(--cat-3)',
          4: 'var(--cat-4)',
          5: 'var(--cat-5)',
          6: 'var(--cat-6)',
        },
        // shadcn-compatible aliases — lets shadcn primitives "just work"
        background: 'var(--canvas)',
        foreground: 'var(--ink)',
        muted: {
          DEFAULT:    'var(--surface-2)',
          foreground: 'var(--ink-3)',
        },
        primary: {
          DEFAULT:    'var(--accent)',
          foreground: 'var(--surface)',
        },
        secondary: {
          DEFAULT:    'var(--surface-2)',
          foreground: 'var(--ink)',
        },
        destructive: {
          DEFAULT:    'var(--danger)',
          foreground: 'var(--surface)',
        },
        border: 'var(--rule)',
        input:  'var(--rule-2)',
        ring:   'var(--accent)',
        card: {
          DEFAULT:    'var(--surface)',
          foreground: 'var(--ink)',
        },
      },
      fontFamily: {
        display: ['Fraunces', 'Iowan Old Style', 'Georgia', 'serif'],
        sans:    ['Geist', 'Inter Tight', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'ui-monospace', 'Menlo', 'monospace'],
      },
      fontSize: {
        eyebrow: ['11px', { lineHeight: '1.25', letterSpacing: '0.14em' }],
        xs:      ['12px', { lineHeight: '1.4'  }],
        sm:      ['13px', { lineHeight: '1.5'  }],
        base:    ['15px', { lineHeight: '1.6'  }],
        md:      ['17px', { lineHeight: '1.55' }],
        lg:      ['21px', { lineHeight: '1.4',  letterSpacing: '-0.01em' }],
        xl:      ['32px', { lineHeight: '1.2',  letterSpacing: '-0.01em' }],
        display: ['56px', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
      },
      spacing: {
        1:  '4px',
        2:  '8px',
        3:  '12px',
        4:  '16px',
        6:  '24px',
        8:  '32px',
        12: '48px',
        16: '64px',
        24: '96px',
      },
      borderRadius: {
        none: '0',
        chip: '2px',
        DEFAULT: '4px',
        md:   '4px',
        lg:   '6px',
        xl:   '8px',
      },
      transitionTimingFunction: {
        ease:    'cubic-bezier(0.2, 0, 0, 1)',
        'ease-in': 'cubic-bezier(0.4, 0, 1, 1)',
      },
      transitionDuration: {
        1: '120ms',
        2: '180ms',
        3: '280ms',
      },
      boxShadow: {
        1: 'var(--shadow-1)',
        2: 'var(--shadow-2)',
        3: 'var(--shadow-3)',
      },
      maxWidth: {
        prose: '680px',         // long-form article body
        content: 'var(--content-max)',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)'  },
        },
      },
      animation: {
        'fade-up': 'fade-up 280ms cubic-bezier(0.2, 0, 0, 1) both',
      },
    },
  },
  plugins: [animate],
};

export default config;
