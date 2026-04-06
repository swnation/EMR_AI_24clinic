# EMR_AI_24clinic

24시 열린의원 의사랑 EMR 보조 도구

## 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python main.py
```

브라우저에서 `http://localhost:8080` 열기

## 최초 설정

처음 실행 시 의사랑 화면 4개 영역을 마우스로 지정합니다.
- 증상 탭
- 특이증상 탭  
- 상병 목록
- 오더 목록

이후 **F12** 키로 즉시 스캔

## 구조

- `knowledge/` : 질환별 처방 가이드 (노션 인수인계)
- `data/` : 묶음처방 코드 데이터
- `rules/` : 체크 룰
- `ocr/` : 화면 캡처 및 OCR
- `app/` : FastAPI 백엔드
- `frontend/` : 브라우저 UI
