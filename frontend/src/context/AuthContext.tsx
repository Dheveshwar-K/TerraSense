import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { User, UserRole } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  demoMode: boolean;
  environment: string;
  loading: boolean;
  selectedLine: string;
  setSelectedLine: (line: string) => void;
  selectedShift: number;
  setSelectedShift: (shift: number) => void;
  openAlertsCount: number;
  refreshAlertsCount: (lineOverride?: string) => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  switchRole: (role: UserRole, userId?: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('ps010_token'));
  const [demoMode, setDemoMode] = useState<boolean>(false);
  const [environment, setEnvironment] = useState<string>('development');
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedLine, setSelectedLine] = useState<string>('ALL');
  const [selectedShift, setSelectedShift] = useState<number>(1);
  const [openAlertsCount, setOpenAlertsCount] = useState<number>(0);

  const selectedLineRef = useRef(selectedLine);
  selectedLineRef.current = selectedLine;

  const refreshAlertsCount = useCallback(async (lineOverride?: string) => {
    const activeLine = lineOverride ?? selectedLineRef.current;
    try {
      const alerts = await api.getAlerts(activeLine !== 'ALL' ? activeLine : undefined, 'OPEN');
      setOpenAlertsCount(alerts.length);
    } catch {
      // ignore in offline/unauthenticated state
    }
  }, []);

  const applyAuthSession = useCallback(
    (res: { access_token: string; refresh_token?: string; user: User }) => {
      localStorage.setItem('ps010_token', res.access_token);
      if (res.refresh_token) {
        localStorage.setItem('ps010_refresh_token', res.refresh_token);
      }
      setToken(res.access_token);
      setUser(res.user);
    },
    []
  );

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await api.login(username, password);
      applyAuthSession(res);
      await refreshAlertsCount();
    },
    [applyAuthSession, refreshAlertsCount]
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // proceed with client sign-out even if token already expired
    } finally {
      localStorage.removeItem('ps010_token');
      localStorage.removeItem('ps010_refresh_token');
      setToken(null);
      setUser(null);
      setOpenAlertsCount(0);
    }
  }, []);

  const switchRole = useCallback(
    async (role: UserRole, userId?: string) => {
      setLoading(true);
      try {
        const res = await api.demoSwitch(role, userId);
        applyAuthSession(res);
        await refreshAlertsCount();
      } finally {
        setLoading(false);
      }
    },
    [applyAuthSession, refreshAlertsCount]
  );

  useEffect(() => {
    let mounted = true;
    const initAuth = async () => {
      let isDemo = false;
      try {
        const cfg = await api.getAuthConfig();
        if (mounted) {
          isDemo = Boolean(cfg.demo_mode);
          setDemoMode(isDemo);
          setEnvironment(cfg.environment || 'development');
        }
      } catch {
        // Fallback when backend is unreachable
      }

      const storedToken = localStorage.getItem('ps010_token');
      if (storedToken) {
        try {
          const me = await api.getMe();
          if (mounted) {
            setUser(me);
            await refreshAlertsCount('ALL');
          }
        } catch {
          localStorage.removeItem('ps010_token');
          localStorage.removeItem('ps010_refresh_token');
          if (mounted) {
            setToken(null);
          }
        }
      }

      if (mounted) {
        setLoading(false);
      }
    };

    initAuth();
    return () => {
      mounted = false;
    };
  }, [refreshAlertsCount]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        demoMode,
        environment,
        loading,
        selectedLine,
        setSelectedLine,
        selectedShift,
        setSelectedShift,
        openAlertsCount,
        refreshAlertsCount,
        login,
        logout,
        switchRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
