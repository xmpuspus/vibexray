// Production configuration settings

export const PRODUCTION_CONFIG = {
  // Performance settings
  MAX_AGENTS_PER_PAGE: 50,
  SEARCH_DEBOUNCE_MS: 300,
  SCROLL_THROTTLE_MS: 100,
  
  // Data fetching
  STALE_TIME_MS: 5 * 60 * 1000, // 5 minutes
  CACHE_TIME_MS: 10 * 60 * 1000, // 10 minutes
  
  // Error handling
  MAX_RETRIES: 3,
  RETRY_DELAY_MS: 1000,
  
  // Analytics
  ENABLE_ANALYTICS: true,
  
  // Features flags
  ENABLE_VOICE_FEATURES: true,
  ENABLE_COLLABORATIVE_MODE: true,
  ENABLE_ADVANCED_SEARCH: true,
  
  // Security
  RATE_LIMIT_REQUESTS: 100, // per hour
  MAX_MESSAGE_LENGTH: 2000,
  
  // UI/UX
  TOAST_DURATION_MS: 5000,
  LOADING_TIMEOUT_MS: 30000,
  
  // Contact form
  ADMIN_EMAIL: 'admin@lovable.dev'
} as const;

export const isDevelopment = import.meta.env.MODE === 'development';
export const isProduction = import.meta.env.MODE === 'production';