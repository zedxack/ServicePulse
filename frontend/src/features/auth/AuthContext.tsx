import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../../shared/api/auth';
import { LoginCredentials, User } from '../../shared/types/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  logout: () => Promise<void>;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('servicepulse_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('servicepulse_token');
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Validate and load fresh user profile on startup if token exists
  useEffect(() => {
    let isMounted = true;

    const initAuth = async () => {
      const storedToken = localStorage.getItem('servicepulse_token');
      if (storedToken) {
        try {
          const profile = await authApi.getMe();
          if (isMounted) {
            setUser(profile);
            localStorage.setItem('servicepulse_user', JSON.stringify(profile));
          }
        } catch {
          if (isMounted) {
            setUser(null);
            setToken(null);
            localStorage.removeItem('servicepulse_token');
            localStorage.removeItem('servicepulse_user');
          }
        }
      }
      if (isMounted) {
        setIsLoading(false);
      }
    };

    initAuth();

    // Listen to global 401 unauthorized event
    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
      localStorage.removeItem('servicepulse_token');
      localStorage.removeItem('servicepulse_user');
    };

    window.addEventListener('servicepulse_unauthorized', handleUnauthorized);
    return () => {
      isMounted = false;
      window.removeEventListener('servicepulse_unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (credentials: LoginCredentials): Promise<User> => {
    setIsLoading(true);
    try {
      const tokenResp = await authApi.login(credentials);
      localStorage.setItem('servicepulse_token', tokenResp.access_token);
      setToken(tokenResp.access_token);

      // Fetch authoritative user profile with roles and permissions
      const profile = await authApi.getMe();
      localStorage.setItem('servicepulse_user', JSON.stringify(profile));
      setUser(profile);
      return profile;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      localStorage.removeItem('servicepulse_token');
      localStorage.removeItem('servicepulse_user');
      setUser(null);
      setToken(null);
    }
  };

  const hasRole = (roleName: string): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return user.roles.some((r) => r.name === roleName);
  };

  const hasAnyRole = (roles: string[]): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    const userRoleNames = user.roles.map((r) => r.name);
    return roles.some((role) => userRoleNames.includes(role));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token && !!user,
        login,
        logout,
        hasRole,
        hasAnyRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
