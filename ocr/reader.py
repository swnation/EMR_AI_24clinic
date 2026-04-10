"""
Windows OCR 텍스트 추출 모듈
winocr 패키지 사용 (Python 3.12+ 호환)
PIL Image → 전처리 → 한국어 OCR → 텍스트
"""
import sys
import io

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    print("필요: pip install Pillow")
    sys.exit(1)


def _is_windows():
    return sys.platform == "win32"


def _preprocess(image: Image.Image) -> Image.Image:
    """OCR 정확도를 위한 이미지 전처리"""
    # 1. 4배 확대 (크롭된 영역이라 충분히 커져야 OCR 정확도 확보)
    w, h = image.size
    image = image.resize((w * 4, h * 4), Image.LANCZOS)

    # 2. 그레이스케일 변환
    image = image.convert("L")

    # 3. 대비 강화
    image = ImageEnhance.Contrast(image).enhance(2.0)

    # 4. 선명도 강화
    image = ImageEnhance.Sharpness(image).enhance(2.0)

    # 5. 이진화 (흑백) — 배경은 흰색, 글자는 검정
    threshold = 140
    image = image.point(lambda p: 255 if p > threshold else 0)

    # 6. RGB로 변환 (winocr 호환)
    image = image.convert("RGB")

    return image


def ocr_image(image: Image.Image) -> str:
    """이미지에서 텍스트 추출 (전처리 + OCR)"""
    if _is_windows():
        try:
            from winocr import recognize_pil_sync
            processed = _preprocess(image)
            result = recognize_pil_sync(processed, 'ko')
            return result['text']
        except Exception as e:
            return f"[Windows OCR 실패: {e}]"
    else:
        return "[OCR는 Windows에서만 동작합니다]"


def ocr_all(images: dict) -> dict:
    """4개 영역 이미지 dict → 텍스트 dict 반환"""
    result = {}
    for name, img in images.items():
        result[name] = ocr_image(img)
    return result


if __name__ == "__main__":
    import os
    captures_dir = "ocr/captures"
    if os.path.isdir(captures_dir):
        for f in sorted(os.listdir(captures_dir)):
            if f.endswith(".png"):
                img = Image.open(os.path.join(captures_dir, f))
                text = ocr_image(img)
                print(f"=== {f} ===")
                print(text[:200])
                print()
    else:
        print("캡처 파일 없음. 먼저 python ocr/capture.py 실행하세요.")
