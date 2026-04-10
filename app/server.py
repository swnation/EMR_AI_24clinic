from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json, os, base64, io, sys

from app.checker import run_check
from app.templates import get_all_templates, get_template_by_id, get_templates_by_category

app = FastAPI()

# 프론트엔드 정적 파일
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def root():
    return FileResponse("frontend/index.html")

class OrderItem(BaseModel):
    code: str                    # 약코드 "aug2"
    dose: Optional[float] = None # 투여량 (1회분)
    days: Optional[int] = None   # 투여일수
    freq: Optional[int] = None   # 일투수 (1일 몇 회)

class ScanRequest(BaseModel):
    dx: List[str] = []        # 상병코드 목록 ["j0390", "k297"]
    orders: List[str] = []    # 오더코드 목록 ["aug2", "dexi", "loxo"] (하위호환)
    order_details: List[OrderItem] = []  # 용량 포함 오더 (Phase 2+)
    symptoms: str = ""        # 증상 텍스트
    patient_type: str = "성인"  # "성인" | "소아"
    age: Optional[int] = None # 나이 (세)

class CheckResult(BaseModel):
    level: str   # err | warn | info | ok
    message: str
    sub: str = ""
    source: str = ""

@app.post("/check", response_model=List[CheckResult])
def check(req: ScanRequest):
    # order_details가 있으면 코드 목록 자동 추출 (하위호환)
    order_codes = req.orders
    if req.order_details:
        order_codes = [o.code for o in req.order_details]
    # order_details를 dict 리스트로 변환
    order_detail_dicts = [o.dict() for o in req.order_details] if req.order_details else None
    results = run_check(req.dx, order_codes, req.symptoms, req.patient_type,
                        order_details=order_detail_dicts, age=req.age)
    return results

# ── 템플릿 API ──

@app.get("/templates")
def templates(category: Optional[str] = None):
    """템플릿 목록 반환. ?category=진단서 로 필터 가능"""
    if category:
        return get_templates_by_category(category)
    return get_all_templates()

@app.get("/templates/{template_id}")
def template_detail(template_id: str):
    """특정 템플릿 반환"""
    t = get_template_by_id(template_id)
    if t:
        return t
    return {"error": "not found"}

# ── knowledge API ──

@app.get("/knowledge/{filename}")
def get_knowledge(filename: str):
    """노션 파일 내용 반환"""
    filename = os.path.basename(filename)  # Path Traversal 방지
    path = os.path.join("knowledge", filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return {"content": f.read()}
    return {"content": ""}

@app.get("/knowledge")
def list_knowledge():
    """knowledge 파일 목록"""
    files = []
    kdir = "knowledge"
    if os.path.isdir(kdir):
        for f in sorted(os.listdir(kdir)):
            if f.endswith(".md"):
                files.append(f)
    return {"files": files}

# ── OCR API (클립보드 이미지 → 텍스트) ──

class OcrRequest(BaseModel):
    image_base64: str   # base64 인코딩된 PNG 이미지
    region: str = ""    # "dx" | "orders" | ""

@app.post("/ocr")
def ocr_image(req: OcrRequest):
    """base64 이미지 → OCR → 텍스트 + 파싱된 코드 반환"""
    try:
        from PIL import Image
        img_bytes = base64.b64decode(req.image_base64)
        img = Image.open(io.BytesIO(img_bytes))

        # Windows OCR 시도
        text = ""
        if sys.platform == "win32":
            try:
                from ocr.reader import ocr_image as win_ocr
                text = win_ocr(img)
            except Exception:
                text = "[Windows OCR 실패]"
        else:
            text = "[OCR는 Windows에서만 동작]"

        # 파싱
        from ocr.parser import parse_dx, parse_orders
        codes = []
        order_details = []
        if req.region == "dx":
            codes = parse_dx(text)
        elif req.region == "orders":
            order_details = parse_orders(text)
            codes = [o["code"] for o in order_details]
        elif req.region in ("symptoms", "special"):
            # 증상/특이증상은 텍스트 그대로 반환
            pass
        else:
            codes = parse_dx(text)

        return {
            "text": text,
            "codes": codes,
            "order_details": order_details,
        }
    except Exception as e:
        return {"text": "", "codes": [], "order_details": [], "error": str(e)}

@app.get("/health")
def health():
    return {"status": "ok"}
