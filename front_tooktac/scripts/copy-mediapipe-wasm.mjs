// @mediapipe/tasks-vision의 wasm 런타임을 public/으로 복사한다.
// 33MB라 저장소에 커밋하지 않고, dev/build 직전에 node_modules에서 가져온다.
import { cpSync, existsSync, mkdirSync } from 'node:fs';

const SRC = 'node_modules/@mediapipe/tasks-vision/wasm';
const DEST = 'public/mediapipe/wasm';

if (!existsSync(SRC)) {
  console.error(`[mediapipe] ${SRC} 가 없습니다. npm install 을 먼저 실행하세요.`);
  process.exit(1);
}

mkdirSync(DEST, { recursive: true });
cpSync(SRC, DEST, { recursive: true });
console.log(`[mediapipe] wasm 런타임 복사 완료 -> ${DEST}`);
