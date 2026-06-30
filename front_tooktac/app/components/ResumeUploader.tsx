'use client';

import { useRef, useState } from 'react';
import { extractTextFromPDF, PageResult } from '@/lib/pdfExtractor';

interface Props {
  onExtracted: (text: string) => void;
}

type ExtractionStatus = 'idle' | 'extracting' | 'review' | 'done';

export default function ResumeUploader({ onExtracted }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const [status, setStatus] = useState<ExtractionStatus>('idle');
  const [progress, setProgress] = useState({ current: 0, total: 0, usingOCR: false });
  const [pages, setPages] = useState<PageResult[]>([]);
  const [editedTexts, setEditedTexts] = useState<Record<number, string>>({});
  const [reviewed, setReviewed] = useState<Record<number, boolean>>({});
  const [fileName, setFileName] = useState('');

  const ocrPages = pages.filter((p) => p.usedOCR);
  const allReviewed =
    ocrPages.length === 0 || ocrPages.every((p) => reviewed[p.pageNumber]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setStatus('extracting');
    setPages([]);
    setEditedTexts({});
    setReviewed({});

    const results = await extractTextFromPDF(file, (current: number, total: number, usingOCR: boolean) => {
      setProgress({ current, total, usingOCR });
    });

    const initialTexts: Record<number, string> = {};
    results.forEach((p: PageResult) => { initialTexts[p.pageNumber] = p.text; });

    setPages(results);
    setEditedTexts(initialTexts);
    setStatus('review');
  };

  const handleTextChange = (pageNumber: number, value: string) => {
    setEditedTexts((prev) => ({ ...prev, [pageNumber]: value }));
    // 수정 시 해당 페이지 검수 완료 해제
    setReviewed((prev) => ({ ...prev, [pageNumber]: false }));
  };

  const toggleReviewed = (pageNumber: number) => {
    setReviewed((prev) => ({ ...prev, [pageNumber]: !prev[pageNumber] }));
  };

  const scrollToPage = (pageNumber: number) => {
    pageRefs.current[pageNumber]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleSubmit = () => {
    const fullText = pages
      .map((p) => editedTexts[p.pageNumber] ?? '')
      .filter(Boolean)
      .join('\n\n');
    onExtracted(fullText);
    setStatus('done');
  };

  return (
    <div className="w-full space-y-4">
      {/* 파일 업로드 버튼 */}
      <div
        onClick={() => fileInputRef.current?.click()}
        className="w-full px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-[#6ce5e8] hover:bg-blue-50/50 transition-colors cursor-pointer"
      >
        <div className="flex flex-col items-center justify-center">
          <div className="w-12 h-12 flex items-center justify-center bg-gray-100 rounded-full mb-3">
            <span className="text-2xl text-gray-400">📄</span>
          </div>
          <p className="text-sm font-medium text-gray-700 mb-1">
            {fileName || '이력서 PDF를 선택하세요'}
          </p>
          <p className="text-xs text-gray-500">PDF 파일 (최대 10MB)</p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {/* 추출 진행 상황 */}
      {status === 'extracting' && (
        <div className="p-4 bg-blue-50 rounded-lg space-y-2">
          <div className="flex justify-between text-sm text-blue-700 font-medium">
            <span>
              {progress.usingOCR
                ? `📷 페이지 ${progress.current} OCR 처리 중...`
                : `📄 페이지 ${progress.current} 텍스트 추출 중...`}
            </span>
            <span>{progress.current} / {progress.total}</span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(progress.current / (progress.total || 1)) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* 검수 UI */}
      {status === 'review' && (
        <div className="space-y-4">
          {/* OCR 페이지 알림 */}
          {ocrPages.length > 0 && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm font-medium text-amber-800 mb-2">
                ⚠️ 아래 페이지는 OCR로 추출되었습니다. 내용을 검수해주세요.
              </p>
              <div className="flex flex-wrap gap-2">
                {ocrPages.map((p) => (
                  <button
                    key={p.pageNumber}
                    onClick={() => scrollToPage(p.pageNumber)}
                    className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                      reviewed[p.pageNumber]
                        ? 'bg-green-100 border-green-400 text-green-700'
                        : 'bg-white border-amber-400 text-amber-700 hover:bg-amber-50'
                    }`}
                  >
                    {reviewed[p.pageNumber] ? '✓ ' : ''}페이지 {p.pageNumber}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 페이지별 텍스트 */}
          <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
            {pages.map((page) => (
              <div
                key={page.pageNumber}
                ref={(el) => { pageRefs.current[page.pageNumber] = el; }}
                className={`border rounded-lg overflow-hidden ${
                  page.usedOCR ? 'border-amber-300' : 'border-gray-200'
                }`}
              >
                {/* 페이지 헤더 */}
                <div
                  className={`flex items-center justify-between px-4 py-2 text-sm font-medium ${
                    page.usedOCR ? 'bg-amber-50 text-amber-800' : 'bg-gray-50 text-gray-700'
                  }`}
                >
                  <span>
                    {page.usedOCR
                      ? `📄 페이지 ${page.pageNumber} - OCR 추출`
                      : `페이지 ${page.pageNumber}`}
                  </span>
                  {page.usedOCR && (
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!reviewed[page.pageNumber]}
                        onChange={() => toggleReviewed(page.pageNumber)}
                        className="w-4 h-4 accent-green-500"
                      />
                      <span className="text-xs">검수 완료</span>
                    </label>
                  )}
                </div>

                {/* 텍스트 에디터 */}
                <textarea
                  value={editedTexts[page.pageNumber] ?? ''}
                  onChange={(e) => handleTextChange(page.pageNumber, e.target.value)}
                  className="w-full px-4 py-3 text-sm text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#6ce5e8]"
                  rows={6}
                  placeholder="추출된 텍스트가 없습니다."
                />
              </div>
            ))}
          </div>

          {/* 전송 버튼 */}
          <button
            onClick={handleSubmit}
            disabled={!allReviewed}
            className={`w-full py-3 rounded-lg font-semibold text-sm transition-colors ${
              allReviewed
                ? 'bg-[#27386d] text-white hover:bg-opacity-90 cursor-pointer'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {allReviewed
              ? '✓ 이력서 텍스트 확정'
              : `OCR 페이지 검수 후 확정 가능 (${ocrPages.filter((p) => reviewed[p.pageNumber]).length}/${ocrPages.length} 완료)`}
          </button>
        </div>
      )}

      {status === 'done' && (
        <p className="text-sm text-green-600 font-medium text-center py-2">
          ✓ 이력서 텍스트가 확정되었습니다.
        </p>
      )}
    </div>
  );
}
