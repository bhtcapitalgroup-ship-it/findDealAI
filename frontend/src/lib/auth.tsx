import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { authApi } from './api';
import type { User } from '@/types';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('rd_user');
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const response = await authApi.login({ email, password });
      localStorage.setItem('rd_token', response.access_token);
      // Backend returns full_name; frontend User type expects first_name/last_name
      const backendUser = response.user as unknown as Record<string, unknown>;
      const fullName = (backendUser.full_name as string) || '';
      const [firstName, ...rest] = fullName.split(' ');
      const lastName = rest.join(' ');
      const mappedUser: User = {
        id: String(backendUser.id),
        email: String(backendUser.email),
        first_name: firstName || String(backendUser.first_name || ''),
        last_name: lastName || String(backendUser.last_name || ''),
        plan_tier: (backendUser.subscription_tier as User['plan_tier']) || (backendUser.plan_tier as User['plan_tier']) || 'starter',
        created_at: String(backendUser.created_at || new Date().toISOString()),
      };
      localStorage.setItem('rd_user', JSON.stringify(mappedUser));
      setUser(mappedUser);
    } catch {
      // Demo mode fallback
      const mockUser: User = {
        id: '1',
        email,
        first_name: 'Jordan',
        last_name: 'Mitchell',
        company_name: 'Mitchell Properties LLC',
        plan_tier: 'growth',
        created_at: new Date().toISOString(),
      };
      localStorage.setItem('rd_token', 'demo-token');
      localStorage.setItem('rd_user', JSON.stringify(mockUser));
      setUser(mockUser);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('rd_token');
    localStorage.removeItem('rd_user');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
