'use client';

import { useEffect } from 'react';
import api from '@/api/api'; // axios 인스턴스 (withCredentials 포함)

export default function AutoLogoutProvider({ children }: { children: React.ReactNode }) {
    useEffect(() => {
        let timeoutId: NodeJS.Timeout;

        const logout = async () => {
            try {
                await api.post('/logout'); // 서버에 쿠키 삭제 요청
                location.href = '/login';  // 로그인 페이지로 이동
            } catch (err) {
                console.error('자동 로그아웃 실패:', err);
            }
        };

        const resetTimer = () => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(logout, 60 * 60 * 1000); // 1시간 후 자동 로그아웃
        };

        const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'];
        events.forEach(event => window.addEventListener(event, resetTimer));

        resetTimer(); // 초기 타이머 시작

        return () => {
            clearTimeout(timeoutId);
            events.forEach(event => window.removeEventListener(event, resetTimer));
        };
    }, []);

    return <>{children}</>;
}
