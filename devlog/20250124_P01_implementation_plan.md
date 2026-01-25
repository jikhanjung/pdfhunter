# PDFHunter 구현 계획

**작성일**: 2025-01-24
**버전**: P01 (초기 계획)

---

## 1. 프로젝트 개요

PDF 및 이미지에서 서지 정보를 자동 추출하는 에이전트 시스템.
- 입력: 스캔 PDF, 텍스트 PDF, 단일 이미지
- 출력: CSL-JSON / RIS / BibTeX + evidence(근거)

---

## 2. 기술 스택

### 핵심 라이브러리
| 영역 | 라이브러리 | 용도 |
|------|-----------|------|
| PDF 처리 | `pypdf`, `pdfplumber` | 텍스트 추출, 메타데이터, 페이지 수 |
| 이미지 렌더링 | `pdf2image` (poppler) | PDF → 이미지 변환 |
| 이미지 처리 | `Pillow`, `opencv-python` | 전처리, 크롭, 회전 |
| OCR | `paddleocr` (기본), `pytesseract` (폴백) | 텍스트 인식 |
| LLM | `openai` 또는 `anthropic` | 구조화 추출 |
| 웹 검색 | `requests`, `scholarly` | 서지 보강 |
| 데이터 검증 | `pydantic` | 스키마 정의 및 검증 |
| CLI | `typer` | 명령줄 인터페이스 |
| UI (추후) | `streamlit` 또는 `gradio` | 사용자 검수 인터페이스 |

### 개발 환경
- Python 3.11+
- Poetry 또는 uv (의존성 관리)
- pytest (테스트)
- ruff (린팅/포매팅)

---

## 3. 프로젝트 구조

```
pdfhunter/
├── src/
│   └── pdfhunter/
│       ├── __init__.py
│       ├── cli.py                 # CLI 진입점
│       ├── core/
│       │   ├── __init__.py
│       │   ├── document.py        # Document 클래스 (PDF/이미지 래퍼)
│       │   ├── pipeline.py        # 메인 파이프라인 오케스트레이션
│       │   └── config.py          # 설정 관리
│       ├── extraction/
│       │   ├── __init__.py
│       │   ├── text_extractor.py  # 텍스트 PDF 추출
│       │   ├── ocr_extractor.py   # OCR 파이프라인
│       │   ├── page_selector.py   # 페이지 샘플링 전략
│       │   └── preprocessor.py    # 이미지 전처리
│       ├── parsing/
│       │   ├── __init__.py
│       │   ├── rule_based.py      # 규칙 기반 추출 (연도, 페이지, 권호)
│       │   ├── llm_extractor.py   # LLM 구조화 추출
│       │   └── patterns.py        # 정규식 패턴 모음
│       ├── validation/
│       │   ├── __init__.py
│       │   ├── validator.py       # 필드 검증
│       │   └── scorer.py          # confidence 점수 계산
│       ├── enrichment/
│       │   ├── __init__.py
│       │   ├── web_search.py      # 웹 검색 보강
│       │   └── expansion.py       # 누락 필드 확장 탐색
│       ├── export/
│       │   ├── __init__.py
│       │   ├── csl_json.py        # CSL-JSON 출력
│       │   ├── ris.py             # RIS 출력
│       │   └── bibtex.py          # BibTeX 출력
│       ├── models/
│       │   ├── __init__.py
│       │   ├── bibliography.py    # 서지 레코드 스키마
│       │   └── evidence.py        # 근거 데이터 스키마
│       └── utils/
│           ├── __init__.py
│           ├── language.py        # 언어 감지
│           └── logging.py         # 로깅 설정
├── tests/
│   ├── fixtures/                  # 테스트용 PDF/이미지
│   ├── test_ocr.py
│   ├── test_parsing.py
│   └── test_pipeline.py
├── data/
│   ├── records/                   # 출력 레코드
│   └── evidence/                  # 근거 이미지/텍스트
├── pyproject.toml
├── CLAUDE.md
├── WORKFLOW.md
├── OCR_STRATEGY.md
└── devlog/
```

---

## 4. 구현 단계

### Phase 1: 기반 구축 (MVP 핵심)

**목표**: 단일 PDF → CSL-JSON 출력 파이프라인 완성

#### 1.1 프로젝트 초기화
- [ ] pyproject.toml 설정
- [ ] 의존성 설치
- [ ] 기본 디렉토리 구조 생성
- [ ] 로깅 설정

#### 1.2 Document 모듈
- [ ] PDF 로드 및 메타데이터 추출 (페이지 수, 텍스트 레이어 여부)
- [ ] 이미지 로드 지원
- [ ] 페이지 렌더링 (저해상도/고해상도)

#### 1.3 페이지 선택기
- [ ] 기본 전략: p1, p2, last
- [ ] 텍스트 PDF 전략: p1-p3, last

#### 1.4 텍스트 추출
- [ ] 텍스트 PDF: pdfplumber로 직접 추출
- [ ] 스캔 PDF: PaddleOCR 기본 파이프라인
- [ ] bbox + confidence 저장

#### 1.5 규칙 기반 추출
- [ ] 연도 패턴 (19xx, 20xx)
- [ ] 페이지 범위 (p. 123–456, pp. 12-34)
- [ ] 권호 (Vol. X, No. Y, tome IX)
- [ ] 시리즈 (Выпуск, Bulletin No.)

#### 1.6 데이터 모델
- [ ] BibliographyRecord (Pydantic)
- [ ] Evidence 모델
- [ ] 상태 enum (confirmed, needs_review, failed)

#### 1.7 기본 출력
- [ ] CSL-JSON 내보내기
- [ ] evidence 파일 저장

---

### Phase 2: LLM 통합

**목표**: 규칙으로 추출 불가능한 필드를 LLM으로 보완

#### 2.1 LLM 추출기
- [ ] 프롬프트 설계 (저자, 제목, 컨테이너)
- [ ] JSON 스키마 강제 출력
- [ ] OpenAI / Anthropic 클라이언트 래퍼

#### 2.2 추출 조합
- [ ] 규칙 결과 + LLM 결과 병합
- [ ] 충돌 해소 로직

#### 2.3 Confidence 점수화
- [ ] 필드별 가중치
- [ ] 전체 confidence 계산
- [ ] 상태 자동 결정 (confirmed / needs_review / failed)

---

### Phase 3: 에이전트 루프

**목표**: 누락 필드 자동 확장 탐색

#### 3.1 확장 탐색
- [ ] pages 누락 → 런닝 헤더 탐색
- [ ] publisher/place 누락 → last-1 추가
- [ ] volume/issue 누락 → 목차 탐색

#### 3.2 루프 제어
- [ ] 최대 반복 횟수 제한
- [ ] 개선 없으면 조기 종료

---

### Phase 4: 웹 검색 보강

**목표**: 내부 추출 불충분 시 외부 검색으로 보완

#### 4.1 검색 쿼리 생성
- [ ] title + author + year 조합
- [ ] 원어 제목 검색

#### 4.2 결과 파싱
- [ ] Google Scholar / Crossref / OpenAlex
- [ ] 결과 매칭 및 병합

#### 4.3 Evidence 저장
- [ ] 웹 출처 URL 기록

---

### Phase 5: 사용자 검수 UI

**목표**: 사람이 최종 확인/수정할 수 있는 인터페이스

#### 5.1 UI 구현 (Streamlit)
- [ ] 좌측: 근거 페이지 이미지
- [ ] 우측: 서지 필드 폼
- [ ] 상단: confidence 표시

#### 5.2 액션
- [ ] 승인
- [ ] 수정 후 저장
- [ ] 웹검색 재시도
- [ ] 추가 OCR 요청

---

### Phase 6: 다중 포맷 및 배치

**목표**: 다양한 출력 포맷 및 대량 처리

#### 6.1 추가 출력 포맷
- [ ] RIS 내보내기
- [ ] BibTeX 내보내기

#### 6.2 배치 처리
- [ ] 디렉토리 입력
- [ ] 진행 상황 표시
- [ ] 실패 건 리포트

---

## 5. MVP 범위 (Phase 1-2)

첫 번째 작동 가능한 버전:

```bash
# CLI 사용 예시
pdfhunter extract paper.pdf -o output.json
pdfhunter extract ./papers/ -o ./records/ --format csl-json
```

**MVP 포함 기능**:
- PDF/이미지 입력
- 텍스트/OCR 자동 분기
- p1/p2/last 페이지 처리
- 규칙 기반 + LLM 추출
- CSL-JSON 출력
- evidence 저장

**MVP 제외 기능**:
- 웹 검색 보강
- 에이전트 확장 루프
- 사용자 검수 UI
- RIS/BibTeX 출력

---

## 6. 의존성 설치 예시

```toml
# pyproject.toml
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
    "paddlepaddle>=2.5",  # CPU 버전
    "pydantic>=2.0",
    "typer>=0.9",
    "openai>=1.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1",
]
ui = [
    "streamlit>=1.30",
]
```

---

## 7. 테스트 전략

### 단위 테스트
- 각 모듈별 독립 테스트
- fixtures/에 샘플 PDF (EN/FR/RU 각 2-3건)

### 통합 테스트
- 전체 파이프라인 end-to-end
- 예상 출력과 비교

### 벤치마크
- OCR 엔진 비교 (PaddleOCR vs Tesseract)
- 필드별 정확도 측정

---

## 8. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| PaddleOCR 키릴 문자 오인식 | 러시아어 문서 정확도 저하 | Tesseract 폴백, 언어별 엔진 선택 |
| LLM API 비용 | 대량 처리 시 비용 증가 | 규칙 기반 우선, LLM은 보조적 사용 |
| 다양한 PDF 레이아웃 | 페이지 선택 실패 | 휴리스틱 점진 개선, 실패 로그 분석 |
| Poppler 설치 의존성 | 환경 설정 복잡 | Docker 이미지 제공 |

---

## 9. 다음 단계

1. **즉시**: pyproject.toml 생성 및 의존성 설치
2. **이번 주**: Phase 1.1 ~ 1.4 완료 (Document, 페이지 선택, 텍스트/OCR 추출)
3. **다음 주**: Phase 1.5 ~ 1.7 완료 (규칙 추출, 데이터 모델, 출력)
4. **2주 후**: Phase 2 완료 (LLM 통합)

---

## 10. 참고 문서

- `WORKFLOW.md`: 전체 워크플로우 명세
- `OCR_STRATEGY.md`: OCR 전략 상세
- `CLAUDE.md`: Claude Code 가이드
