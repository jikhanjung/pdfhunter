# 프로젝트 초기화

**날짜**: 2025-01-24
**작업**: 프로젝트 구조 생성 및 핵심 모듈 구현

---

## 완료된 작업

### 1. 문서 검토 및 보완

#### OCR_STRATEGY.md 보완
- 목차 페이지 탐지 방법 추가 (레이아웃 분석, 키워드 매칭, 휴리스틱)
- 런닝 헤더 탐색 적용 조건 명시 (저널 논문 + 누락 필드 + 5페이지 이상)
- OCR 엔진 비교표 추가 (PaddleOCR, Tesseract 5.x, EasyOCR)
- Confidence 임계값 튜닝 가이드 추가
- 에러 처리 및 엣지 케이스 섹션 추가

#### 구현 계획 작성
- `devlog/20250124_P01_implementation_plan.md` 생성
- 6단계 Phase 정의 (기반 구축 → UI까지)
- 기술 스택, 프로젝트 구조, MVP 범위 정의

---

### 2. 프로젝트 초기화

#### pyproject.toml 생성
```toml
[project]
name = "pdfhunter"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pypdf>=4.0",
    "pdfplumber>=0.10",
    "pdf2image>=1.16",
    "Pillow>=10.0",
    "opencv-python>=4.8",
    "paddleocr>=2.7",
    "paddlepaddle>=2.5",
    "pydantic>=2.0",
    "typer>=0.9",
    "openai>=1.0",
    "rich>=13.0",
]
```

#### 디렉토리 구조 생성
```
src/pdfhunter/
├── core/
├── extraction/
├── parsing/
├── validation/
├── enrichment/
├── export/
├── models/
└── utils/

tests/
data/
├── records/
└── evidence/
```

---

### 3. 핵심 모듈 구현

#### core/config.py
- `OCRConfig`: OCR 엔진, 언어, DPI, confidence 임계값
- `ExtractionConfig`: 기본 페이지, 확장 제한
- `LLMConfig`: 프로바이더, 모델, 파라미터
- `Config`: 통합 설정 클래스

#### core/document.py
- `Document` 클래스: PDF/이미지 래퍼
- `DocumentType` enum: TEXT_PDF, SCANNED_PDF, IMAGE
- `DocumentMetadata`: 파일 정보, 페이지 정보
- 주요 기능:
  - PDF 텍스트 레이어 감지
  - 페이지 렌더링 (pdf2image)
  - 텍스트 추출 (pdfplumber)
  - 페이지 선택 전략

#### extraction/page_selector.py
- `PageSelector` 클래스
- `PageRole` enum: TITLE, TITLE_VERSO, BODY_START, COLOPHON, TOC, RUNNING_HEADER
- 기본 페이지 선택: 문서 유형별 전략
- 확장 페이지 선택: 누락 필드 기반

#### models/bibliography.py
- `Author`: 저자 정보 (family/given/literal)
- `DateParts`: 날짜 정보 (year/month/day)
- `BibliographyRecord`: CSL-JSON 호환 서지 레코드
  - CSL-JSON 변환 (`to_csl_json()`)
  - Confidence 계산 (`calculate_confidence()`)
  - 상태 결정 (`determine_status()`)

#### models/evidence.py
- `EvidenceType` enum: OCR_TEXT, PDF_TEXT, IMAGE_CAPTURE, WEB_SEARCH, USER_INPUT
- `BoundingBox`: bbox 좌표
- `Evidence`: 추출 근거 데이터

#### cli.py
- `pdfhunter version`: 버전 표시
- `pdfhunter info <file>`: 문서 정보 표시
- `pdfhunter extract <file>`: 추출 (TODO)

#### utils/logging.py
- `setup_logging()`: 로깅 설정
- `get_logger()`: 로거 인스턴스

---

### 4. 테스트

#### tests/test_models.py
- Author 테스트 (CSL 변환)
- DateParts 테스트
- BibliographyRecord 테스트 (CSL 변환, confidence 계산, 상태 결정)
- Evidence 테스트

---

### 5. 문서 업데이트

#### CLAUDE.md 업데이트
- 개발 명령어 추가 (pip install, pytest, ruff)
- 프로젝트 구조 추가
- CLI 사용법 추가

---

## 다음 작업

1. 의존성 설치 및 테스트 실행
2. OCR 추출기 구현 (`extraction/ocr_extractor.py`)
3. 텍스트 추출기 구현 (`extraction/text_extractor.py`)
4. 규칙 기반 파싱 구현 (`parsing/rule_based.py`)

---

## 파일 목록

```
pyproject.toml
src/pdfhunter/__init__.py
src/pdfhunter/cli.py
src/pdfhunter/core/__init__.py
src/pdfhunter/core/config.py
src/pdfhunter/core/document.py
src/pdfhunter/extraction/__init__.py
src/pdfhunter/extraction/page_selector.py
src/pdfhunter/models/__init__.py
src/pdfhunter/models/bibliography.py
src/pdfhunter/models/evidence.py
src/pdfhunter/utils/__init__.py
src/pdfhunter/utils/logging.py
tests/__init__.py
tests/test_models.py
```
