const MIN_QUALITY_THRESHOLD = 0.3;
const MIN_TEXT_LENGTH = 30;

export interface PageResult {
  pageNumber: number;
  text: string;
  usedOCR: boolean;
}

export function calculateTextQuality(text: string): number {
  if (!text || text.length < MIN_TEXT_LENGTH) return 0;
  const validChars = text.match(/[가-힣a-zA-Z0-9]/g)?.length ?? 0;
  return validChars / text.length;
}

function filterLowQualitySentences(text: string): string {
  return text
    .split('\n')
    .filter((sentence) => calculateTextQuality(sentence) >= MIN_QUALITY_THRESHOLD)
    .join('\n')
    .trim();
}

export async function extractTextFromPDF(
  file: File,
  onProgress?: (current: number, total: number, usingOCR: boolean) => void
): Promise<PageResult[]> {
  const pdfjsLib = await import('pdfjs-dist');
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
  ).toString();

  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const results: PageResult[] = [];

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);

    // 1단계: 텍스트 레이어 추출
    const textContent = await page.getTextContent();
    const rawText = textContent.items
      .map((item) => ('str' in item ? (item as { str: string }).str : ''))
      .join(' ');

    let finalText = rawText;
    let usedOCR = false;

    const isLowQuality =
      rawText.length < MIN_TEXT_LENGTH ||
      calculateTextQuality(rawText) < MIN_QUALITY_THRESHOLD;

    if (isLowQuality) {
      // 2단계: OCR 폴백 (Lazy Load)
      onProgress?.(i, pdf.numPages, true);
      const Tesseract = await import('tesseract.js');

      const viewport = page.getViewport({ scale: 2.0 });
      const canvas = document.createElement('canvas');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const ctx = canvas.getContext('2d')!;

      await page.render({ canvasContext: ctx, viewport, canvas }).promise;

      const { data: { text: ocrText } } = await Tesseract.default.recognize(canvas, 'kor+eng');

      if (calculateTextQuality(ocrText) >= MIN_QUALITY_THRESHOLD) {
        finalText = ocrText;
        usedOCR = true;
      } else {
        finalText = '';
      }
    } else {
      onProgress?.(i, pdf.numPages, false);
    }

    // 3단계: 문장 단위 정제
    const cleanedText = filterLowQualitySentences(finalText);
    results.push({ pageNumber: i, text: cleanedText, usedOCR });
  }

  return results;
}
