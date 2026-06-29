// app/utils/auth.ts

export const isLoggedIn = (): boolean => {
  if (typeof document === 'undefined') return false;
  return document.cookie.includes('access_token=');
};
