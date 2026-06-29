'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function InterviewSetupPage() {
  const [cameraConnected, setCameraConnected] = useState(false);
  const [micConnected, setMicConnected] = useState(false);
  const [speakerConnected, setSpeakerConnected] = useState(false);

  useEffect(() => {
    const video = document.getElementById('webcam-video') as HTMLVideoElement;
    if (!video) return;

    // 카메라 확인
    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
          video.srcObject = stream;
          setCameraConnected(true);
        })
        .catch(() => setCameraConnected(false));

    // 마이크 확인
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(() => setMicConnected(true))
        .catch(() => setMicConnected(false));

    // 스피커 확인 (출력 장치 존재 여부)
    navigator.mediaDevices.enumerateDevices()
        .then((devices) => {
          const hasOutput = devices.some(device => device.kind === 'audiooutput');
          setSpeakerConnected(hasOutput);
        });

    return () => {
      const tracks = (video.srcObject as MediaStream)?.getTracks?.();
      tracks?.forEach(track => track.stop());
    };
  }, []);

  const renderStatus = (connected: boolean) => (
      <div className="flex items-center mt-1">
        <i className={`ri-${connected ? 'check-circle-fill text-green-500' : 'close-circle-fill text-red-400'} text-sm mr-1`} />
        <span className={`${connected ? 'text-green-500' : 'text-red-400'} text-xs`}>
        {connected ? '연결됨' : '연결안됨'}
      </span>
      </div>
  );

  const isAllConnected = cameraConnected && micConnected && speakerConnected;

  return (
      <div className="min-h-screen bg-[#e7f8ff] flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-4xl mx-auto text-center">
          <h1 className="text-3xl font-bold text-[#27386d] mb-12">
            정확한 분석을 위해 면접 환경을 체크해볼게요!
          </h1>

          {/* 웹캠 영상 */}
          <div className="relative mb-12">
            <div className="w-[800px] h-[600px] mx-auto bg-black rounded-2xl relative overflow-hidden shadow-lg">
              <video
                  id="webcam-video"
                  autoPlay
                  playsInline
                  muted
                  className="absolute inset-0 w-full h-full object-cover z-0 rounded-2xl"
              />
              {/*<div className="absolute inset-0 flex items-center justify-center z-10">*/}
              {/*  <img*/}
              {/*      src="https://static.readdy.ai/image/bd8e14006923dac60f3dc1d58d6a7430/1d052a3e5af734642f9c36f0bbe2f921.png"*/}
              {/*      alt="면접 자세 가이드"*/}
              {/*      className="w-[90%] h-[90%] object-cover opacity-60 pointer-events-none"*/}
              {/*  />*/}
              {/*  <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2">*/}
              {/*    <p className="text-white/90 text-lg font-medium bg-black/30 px-4 py-2 rounded-lg">*/}
              {/*      얼굴을 가이드 안에 맞추세요*/}
              {/*    </p>*/}
              {/*  </div>*/}
              {/*</div>*/}
            </div>
          </div>

          {/* 장치 상태 */}
          <div className="flex justify-center gap-8 mb-12">
            {/* 카메라 */}
            <div className="flex flex-col items-center">
              <div className="w-20 h-20 bg-[#6ce5e8] rounded-2xl flex items-center justify-center shadow-lg">
                <i className="ri-camera-fill text-white text-2xl" />
              </div>
              <span className="text-[#27386d] font-medium mt-3">카메라 연결</span>
              {renderStatus(cameraConnected)}
            </div>

            {/* 마이크 */}
            <div className="flex flex-col items-center">
              <div className="w-20 h-20 bg-[#6ce5e8] rounded-2xl flex items-center justify-center shadow-lg">
                <i className="ri-mic-fill text-white text-2xl" />
              </div>
              <span className="text-[#27386d] font-medium mt-3">마이크 연결</span>
              {renderStatus(micConnected)}
            </div>

            {/* 스피커 */}
            <div className="flex flex-col items-center">
              <div className="w-20 h-20 bg-[#6ce5e8] rounded-2xl flex items-center justify-center shadow-lg">
                <i className="ri-volume-up-fill text-white text-2xl" />
              </div>
              <span className="text-[#27386d] font-medium mt-3">스피커 연결</span>
              {renderStatus(speakerConnected)}
            </div>
          </div>

          {/* 이동 버튼 */}
          <div className="flex justify-center gap-4">
            <Link href="/today-interview">
              <button className="px-8 py-3 bg-gray-200 hover:bg-gray-300 text-[#27386d] font-medium rounded-xl transition-colors">
                이전으로
              </button>
            </Link>
            <Link href="/today-interview/icebreaking">
              <button
                  className={`px-8 py-3 rounded-xl font-medium transition-colors ${isAllConnected
                      ? 'bg-[#27386d] hover:bg-[#1e2a5a] text-white'
                      : 'bg-gray-400 text-white cursor-not-allowed opacity-50'}`}
                  disabled={!isAllConnected}
              >
                시작하기
              </button>
            </Link>
          </div>
        </div>
      </div>
  );
}
