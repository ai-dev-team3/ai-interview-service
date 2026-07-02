'use client';

import { ReactNode, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getResumeStatus } from '@/api/api';

/**
 * 이력서 등록이 선행되어야 하는 기능(AI 면접 등)의 라우터 가드.
 * 미등록 상태면 마이페이지 이력서 업로드 섹션으로 리다이렉트한다.
 */
export default function ResumeGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const { has_resume } = await getResumeStatus();
        if (cancelled) return;
        if (has_resume) {
          setAllowed(true);
        } else {
          router.replace('/mypage?resume=required');
        }
      } catch (err: any) {
        if (cancelled) return;
        if (err?.response?.status === 401) {
          router.replace('/login');
        } else {
          // 상태 확인 실패(네트워크 등) 시에는 기능 진입을 막지 않는다
          setAllowed(true);
        }
      }
    };

    check();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!allowed) return null;
  return <>{children}</>;
}
