'use client';

import { createContext, useContext, useState, useCallback, useMemo, ReactNode, useEffect } from 'react';
import api from '@/api/api';

export type UserInfo = {
  user_id: number;
  nickname: string;
  desired_job: string;
};

type UserContextValue = {
  user: UserInfo | null;
  refreshUser: () => Promise<void>;
  clearUser: () => void;
};

const UserContext = createContext<UserContextValue | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);

  const refreshUser = useCallback(async () => {
    try {
      const res = await api.get<UserInfo>('/me');
      setUser(res.data);
    } catch {
      setUser(null);
    }
  }, []);

  const clearUser = useCallback(() => {
    setUser(null);
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // UserContext.tsx 일부
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
        if (e.key === 'auth:event' && e.newValue === 'logout') {
        clearUser();         // 사용자 스냅샷 즉시 제거
        }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
   }, [clearUser]);

  const value = useMemo(() => ({ user, refreshUser, clearUser }), [user, refreshUser, clearUser]);

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error('useUser must be used within <UserProvider>');
  }
  return ctx;
}

