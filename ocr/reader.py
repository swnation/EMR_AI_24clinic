"""
Windows OCR (WinRT) 텍스트 추출 모듈
PIL Image → 한국어 OCR → 텍스트
"""
import asyncio
import sys
import io

try:
    from PIL import Image
except ImportError:
    print("필요: pip install Pillow")
    sys.exit(1)


def _is_windows():
    return sys.platform == "win32"


async def _ocr_winrt(image: Image.Image) -> str:
    """Windows WinRT OCR (한국어, 별도 설치 불필요)"""
    from winsdk.windows.media.ocr import OcrEngine
    from winsdk.windows.globalization import Language
    from winsdk.windows.graphics.imaging import (
        SoftwareBitmap, BitmapPixelFormat, BitmapAlphaMode
    )
    from winsdk.windows.storage.streams import (
        InMemoryRandomAccessStream, DataWriter
    )

    # PIL → BMP bytes
    buf = io.BytesIO()
    image.save(buf, format="BMP")
    bmp_bytes = buf.getvalue()

    # BMP → SoftwareBitmap
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(bmp_bytes)
    await writer.store_async()
    stream.seek(0)

    decoder = await __import__(
        'winsdk.windows.graphics.imaging', fromlist=['BitmapDecoder']
    ).BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()

    # 한국어 OCR
    lang = Language("ko")
    engine = OcrEngine.try_create_from_language(lang)
    if engine is None:
        raise RuntimeError("한국어 OCR 엔진을 찾을 수 없습니다")

    result = await engine.recognize_async(bitmap)
    return result.text


def ocr_image(image: Image.Image) -> str:
    """이미지에서 텍스트 추출 (동기 래퍼)"""
    if _is_windows():
        return asyncio.run(_ocr_winrt(image))
    else:
        # Windows가 아닌 환경에서는 더미 반환 (개발/테스트용)
        return "[OCR는 Windows에서만 동작합니다]"


def ocr_all(images: dict) -> dict:
    """4개 영역 이미지 dict → 텍스트 dict 반환"""
    result = {}
    for name, img in images.items():
        result[name] = ocr_image(img)
    return result


if __name__ == "__main__":
    # 테스트: 캡처 파일에서 OCR
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
