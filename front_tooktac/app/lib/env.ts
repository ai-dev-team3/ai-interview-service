// NEXT_PUBLIC_* 값은 빌드 시점에 번들로 인라인되므로 process.env[name] 동적 조회가 불가능하다.
// 호출부에서 process.env.NEXT_PUBLIC_X 를 그대로 넘긴다.
//
// 값이 없을 때 하드코딩된 주소로 폴백하면 잘못된 서버에 조용히 붙어 원인 파악이 어려우므로,
// 즉시 실패시킨다.
export function requireEnv(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(
      `${name} 환경변수가 설정되지 않았습니다. front_tooktac/.env.local 을 확인하세요.`
    );
  }
  return value;
}
