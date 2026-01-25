# 개발일지: 2025-01-24

**작업자**: Gemini
**파일**: `devlog/20250124_003_pipeline_and_ui_implementation.md`
**제목**: 핵심 파이프라인, 웹 연동 및 기본 UI 구현

---

## 1. 개요

핵심 모듈 구현 이후, 각 컴포넌트를 통합하고 실제 작동하는 워크플로우를 구축하는 데 집중했다. 주요 작업은 데이터 처리 파이프라인을 완성하고, LLM 연동 테스트를 구현했으며, 웹 검색을 통한 데이터 보강 기능과 사용자 검수 UI의 프로토타입을 제작한 것이다.

---

## 2. 주요 작업 내용

### 2.1. 메인 파이프라인 구현 (`core/pipeline.py`)

- 각 추출 단계(텍스트, OCR, 규칙 기반, LLM)를 순서대로 오케스트레이션하는 `Pipeline` 클래스를 구현했다.
- 문서 유형(`TEXT_PDF` 또는 `SCANNED_PDF`)에 따라 적절한 추출기(TextExtractor 또는 OCRExtractor)를 사용하도록 분기 처리 로직을 추가했다.
- `Document` 객체로부터 페이지를 선택하고, 텍스트 또는 이미지로 변환하여 각 추출기에 전달하는 로직을 구현했다.
- 규칙 기반 결과와 LLM 결과를 병합하여 최종 `BibliographyRecord`를 생성하는 과정을 구현했다.
- Pydantic 모델의 `id` 필드 누락으로 인한 `ValidationError`를 해결하기 위해 `uuid`를 사용하여 레코드 ID를 생성하도록 수정했다.

### 2.2. LLM 추출기 연동 테스트 (`tests/test_parsing.py`)

- 실제 OpenAI API를 호출하여 LLM 추출기의 유효성을 검증하는 통합 테스트(`TestLLMExtractorIntegration`)를 구현했다.
- `OPENAI_API_KEY` 환경 변수가 없을 경우 테스트를 건너뛰도록 `pytest.mark.skipif`를 적용했다.
- `scholarly` 라이브러리 사용법 오류로 인해 발생했던 `AttributeError`를 해결하고, `httpx`와의 버전 충돌 문제를 우회하기 위해 프록시 설정을 임시 비활성화했다.

### 2.3. 데이터 모델 불일치 해결

- 파이프라인 개발 과정에서 발견된 여러 데이터 모델 간의 필드명 불일치 문제를 해결했다.
  - `BibliographyRecord`의 `authors` 필드가 실제로는 `author`인 점을 수정했다.
  - `document_type` 필드를 CSL-JSON 표준에 맞는 `type`으로 통일했다.
  - `year` 필드가 `issued` 객체 내에 포함되도록 파이프라인의 데이터 변환 로직을 수정했다.
- 위 수정사항을 `llm_extractor.py`, `test_parsing.py`, `test_pipeline.py` 등 관련 모든 파일에 일관되게 적용했다.

### 2.4. 웹 검색 연동 (`enrichment/web_search.py`)

- `scholarly` 라이브러리를 사용하여 Google Scholar 검색으로 서지 정보를 보강하는 `WebSearchEnricher` 클래스의 기본 구조를 구현했다.
- `pyproject.toml`에 `scholarly` 의존성을 추가하고 설치했다.
- 제목과 저자명을 기반으로 검색 쿼리를 생성하고, 검색 결과를 파싱하여 기존 레코드에 부족한 정보(`pub_year`, `venue` 등)를 채우는 기본 병합 로직을 구현했다.
- `unittest.mock`을 사용하여 실제 웹 요청 없이도 테스트가 가능하도록 `tests/test_enrichment.py`를 작성했다.

### 2.5. 사용자 검수 UI 프로토타입 (`ui/review_ui.py`)

- `streamlit`을 사용하여 추출된 메타데이터를 검토하고 수정할 수 있는 기본 UI 프로토타입을 구현했다.
- `pyproject.toml`의 선택적 의존성에 `streamlit`을 추가하고 설치했다.
- UI는 더미 `BibliographyRecord`를 사용하여 필드를 표시하며, 향후 실제 파이프라인과 연동될 수 있는 기반을 마련했다.

---

## 3. 발생했던 문제 및 해결

- **`TypeError` 및 `AttributeError`**: 파이프라인 및 테스트 코드 작성 초기 단계에서 각 모듈의 메서드 시그니처(인자)나 모델 속성명을 잘못 사용하여 다수의 오류가 발생했다. 이는 각 모듈(`document.py`, `ocr_extractor.py` 등)의 코드를 직접 읽고 명세에 맞게 호출 방식을 수정하여 해결했다.
- **Pydantic `ValidationError`**: `BibliographyRecord` 생성 시 필수 필드인 `id`가 누락되어 오류가 발생했다. `uuid`를 이용해 고유 ID를 생성하여 문제를 해결했다.
- **필드명 불일치**: `LLMExtractionResult`와 `BibliographyRecord` 간에 `author`/`authors`, `type`/`document_type` 등 필드명이 달라 데이터가 누락되는 문제가 있었다. CSL-JSON 표준에 맞춰 `BibliographyRecord` 기준으로 필드명을 통일하여 해결했다.
- **`scholarly` 라이브러리 사용 오류**: 초기 `AttributeError`는 `from scholarly import scholarly` 구문을 잘못 이해하여 발생했으며, `dir()` 함수로 패키지 구조를 확인하여 올바른 사용법을 파악했다. `httpx`와의 호환성 문제로 인한 `TypeError`는 프록시 기능을 임시 비활성화하여 우회했다.

---

## 4. 다음 단계

- **에이전트 루프 구현**: 누락된 필드를 채우기 위해 지능적으로 추가 페이지를 처리하거나 다른 전략을 시도하는 에이전트 로직을 구현한다.
- **UI와 파이프라인 연동**: 사용자가 UI에서 직접 PDF 파일을 업로드하고, 파이프라인을 실행하여 결과를 바로 검토할 수 있도록 연동한다.
- **데이터 병합 로직 고도화**: 현재의 단순 병합 로직을 개선하여, 각 소스(규칙, LLM, 웹)의 신뢰도 점수를 기반으로 더 정확한 데이터를 선택하는 로GIC을 구현한다.
- **UI에 근거(Evidence) 표시**: 추출된 데이터가 문서의 어느 부분에서 왔는지 시각적으로(이미지 및 바운딩 박스) 표시하는 기능을 UI에 추가한다.
