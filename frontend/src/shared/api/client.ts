import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Strict in-memory token storage (never persisted to localStorage or sessionStorage)
let memoryAccessToken: string | null = null;

export const setAuthToken = (token: string | null): void => {
  memoryAccessToken = token;
};

export const getAuthToken = (): string | null => {
  return memoryAccessToken;
};

export const clearAuthToken = (): void => {
  memoryAccessToken = null;
};

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Request interceptor to attach in-memory bearer token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (memoryAccessToken && config.headers) {
      config.headers.Authorization = `Bearer ${memoryAccessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor:
// - 401: Clears in-memory token and notifies AuthContext
// - 403: Preserves authentication state (403 is an authorization rejection, not session expiration)
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearAuthToken();
      window.dispatchEvent(new Event('servicepulse_unauthorized'));
    }
    return Promise.reject(error);
  }
);
