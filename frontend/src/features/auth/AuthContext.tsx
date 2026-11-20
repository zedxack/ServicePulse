import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../../shared/api/auth';
import { clearAuthToken, setAuthToken } from '../../shared/api/client';
import { JoinOrganizationRequest, LoginCredentials, User } from '../../shared/types/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  joinOrganization?: (data: JoinOrganizationRequest) => Promise<User>;
  logout: () => Promise<void>;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Purely in-memory authentication state (never stored in localStorage or sessionStorage)
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    // Listen to global 401 unauthorized event (triggered by Axios response interceptor)
    const handleUnauthorized = () => {
      clearAuthToken();
      setUser(null);
      setToken(null);
    };

    window.addEventListener('servicepulse_unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('servicepulse_unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (credentials: LoginCredentials): Promise<User> => {
    setIsLoading(true);
    try {
      const tokenResp = await authApi.login(credentials);
      // Store access token in-memory only
      setAuthToken(tokenResp.access_token);
      setToken(tokenResp.access_token);

      // Fetch authoritative user profile with roles and permissions
      const profile = await authApi.getMe();
      setUser(profile);
      return profile;
    } finally {
      setIsLoading(false);
    }
  };

  const joinOrganization = async (data: JoinOrganizationRequest): Promise<User> => {
    setIsLoading(true);
    try {
      const tokenResp = await authApi.joinOrganization(data);
      setAuthToken(tokenResp.access_token);
      setToken(tokenResp.access_token);

      const profile = await authApi.getMe();
      setUser(profile);
      return profile;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore network errors during logout
    } finally {
      clearAuthToken();
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
        joinOrganization,
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
