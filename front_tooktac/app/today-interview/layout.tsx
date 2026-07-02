import { ReactNode } from 'react';
import ResumeGuard from '@/components/ResumeGuard';

export default function TodayInterviewLayout({ children }: { children: ReactNode }) {
  return <ResumeGuard>{children}</ResumeGuard>;
}
