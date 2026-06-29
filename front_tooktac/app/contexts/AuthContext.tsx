
'use client';

import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import api from '@/api/api';

interface AuthContextType {
  /** 로그인 여부: 로딩 중에는 undefined */
  isLoggedIn: boolean | undefined;
  /** 로그인 여부 수동 변경(로그인/로그아웃 직후 호출) */
  setIsLoggedIn: (v: boolean) => void;
  /** /me 를 다시 호출하여 인증 상태를 재검증 */
  refreshAuth: () => Promise<void>;
  /** 클라이언트 측 강제 로그아웃(401 등 비정상 세션 종료 시) */
  clientSignOut: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | undefined>(undefined);

  /** /me 재검증 */
  const refreshAuth = useCallback(async () => {
    try {
      await api.get('/me');      // 서버 쿠키 기반 인증 확인
      setIsLoggedIn(true);       // 성공 → 로그인 상태
    } catch {
      setIsLoggedIn(false);      // 실패 → 비로그인 상태
    }
  }, []);

  /** 비정상 세션(401 등)에서 클라이언트 상태만 정리 */
  const clientSignOut = useCallback(() => {
    setIsLoggedIn(false);                                 // 전역 로그인 플래그 false
    localStorage.setItem('auth:event', 'logout');         // 다중 탭 동기화
    // Bearer 헤더를 사용하는 프로젝트라면 즉시 제거(쿠키 인증만 사용 시 생략 가능)
    // @ts-ignore
    delete api.defaults?.headers?.common?.Authorization;
  }, []);

  // 다중 탭/창에서 login/logout 브로드캐스트를 감지 → /me 재검증
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'auth:event') {
        refreshAuth();
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [refreshAuth]);

  // 응답 인터셉터: 401이면 즉시 클라이언트 로그아웃 처리
  useEffect(() => {
    const id = api.interceptors.response.use(
      (res) => res,
      async (err) => {
        if (err?.response?.status === 401) {
          clientSignOut();       // 세션 만료/무효 → 상태 정리
        }
        return Promise.reject(err);
      }
    );
    return () => api.interceptors.response.eject(id);
  }, [clientSignOut]);

  // 최초 마운트 시 현재 인증 상태 확인
  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  const value = useMemo(
    () => ({ isLoggedIn, setIsLoggedIn, refreshAuth, clientSignOut }),
    [isLoggedIn, refreshAuth, clientSignOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within <AuthProvider>');
  }
  return ctx;
}
