# OCR Policy – 본문 텍스트 레이어 생성 및 PDF 삽입

본 문서는 **텍스트 레이어가 없거나 품질이 불량한 PDF**에 대해,
본문 OCR을 수행하여 **검색 가능한 텍스트 레이어(PDF/A 또는 Searchable PDF)** 를 생성하는 정책(spec)이다.

> 범위: **본문 OCR 전용**
>
> - PDFResolve: 서지정보 확보(메타데이터/비전/LLM/외부 DB)까지
> - 본 OCR 프로세스: 별도 배치/워크로커로 실행 (대량 처리 최적화)

---

## 1. Goals (목표)

1. 원본 이미지/레이아웃을 최대한 보존한 채, 텍스트 레이어만 추가한다.
2. 페이지별 텍스트 및 (선택) 바운딩 박스 결과를 함께 저장한다.
3. 대량 처리(10k+)에서 자동 품질 평가와 재시도 경로를 제공한다.
4. 모든 결과는 **재현 가능**하도록 설정과 로그를 남긴다.

---

## 2. Inputs / Outputs

### 입력
- PDF 원본
- (선택) 문서 언어 힌트 (예: `eng`, `fra`, `rus`)

### 출력
- `*_ocr.pdf`: 원본 위에 텍스트 레이어를 얹은 PDF
- `ocr_text/`: 페이지별 텍스트
  - `ocr_text/p0001.txt`
- `ocr_boxes/`: 페이지별 좌표 결과(선택)
  - `ocr_boxes/p0001.json` 또는 `p0001.hocr`
- `ocr_run.json`: 실행 설정 스냅샷(언어, dpi, 전처리, 엔진 버전)
- `ocr_quality.json`: 품질 점수 및 판정

---

## 3. When to OCR (OCR 대상 판정)

### 3.1 문서 단위 판정
- 텍스트 레이어가 없거나(`scanned`)
- 텍스트 레이어는 있으나 품질이 깨짐(무의미 문자 비율 높음)

### 3.2 페이지 단위 판정 (hybrid 대응)
- 페이지 텍스트 길이 < 임계값(예: 50자)
- 비정상 문자(�) 또는 제어문자 비율 과다
- 추출 텍스트 엔트로피/다양성 지나치게 낮음

> 판정 결과는 페이지별로 기록한다: `needs_ocr_pages[]`

---

## 4. Rendering Policy (이미지 렌더링)

OCR 품질의 대부분은 렌더링에서 결정된다.

### 4.1 DPI
- 기본: **300 dpi**
- 작은 글자/2단/표/각주 과다: 400 dpi (비용 증가 고려)
- 대형 도면/포스터형: 200 dpi (타협)

### 4.2 Color Mode
- 기본: grayscale
- 컬러 배경/노이즈가 심하면 RGB 유지 후 조건부 전처리

### 4.3 Rotation / Skew
- 90/180/270 회전 감지 시 정규화
- 기울기(skew) 보정은 품질 저하 시에만 조건부 적용

---

## 5. Preprocessing Policy (조건부 전처리)

전처리는 항상 적용하지 않고, **품질 평가가 낮은 경우에만 단계적으로 강화**한다.

### 5.1 Preprocess Levels
- Level 0: 없음
- Level 1: 약한 denoise + 대비 보정
- Level 2: 배경 제거 + adaptive threshold(보수적으로)

> Level 2는 글자 깨짐을 유발할 수 있으므로 재시도 단계에서만 사용한다.

---

## 6. OCR Engine Policy (엔진 선택)

### 6.1 Two-Tier Strategy (권장)
- Tier A (기본): 오픈소스 OCR (예: Tesseract 계열)
- Tier B (승격): 고품질 OCR 엔진(클라우드/상용/강한 모델)

### 6.2 승격 조건
- 품질 점수(Q) < T2
- 또는 특정 reason_code 발생(예: `OCR_POOR_QUALITY` 지속)

---

## 7. Language Policy (언어 정책)

### 7.1 원칙
- 과도한 다국어 동시 지정은 정확도를 떨어뜨릴 수 있다.
- 가능한 한 **문서/페이지 단위로 언어를 제한**한다.

### 7.2 추천 흐름
1) 샘플 텍스트로 문자 스크립트 판정: Latin / Cyrillic / Mixed
2) Latin: `eng` 기본 + 필요시 `fra` 추가
3) Cyrillic: `rus` 기본
4) Mixed: 2회 실행(라틴/키릴) 후 품질 점수 우수 결과 채택

---

## 8. Searchable PDF Composition (텍스트 레이어 삽입)

### 8.1 원칙
- 원본 페이지 이미지는 유지
- OCR 텍스트는 투명/비가시적 레이어로 오버레이

### 8.2 검증 체크리스트
- 페이지 크기/좌표 정합
- 텍스트 선택 시 위치가 원문과 대략 일치
- 회전 페이지에서 텍스트 방향 일치

---

## 9. Quality Scoring (자동 품질 평가)

### 9.1 Metrics
- 문자 다양성/엔트로피
- 알파뉴메릭 비율 vs 기호 비율
- 언어별 단어 사전 매칭(가능한 경우)
- 페이지별 단어 수/줄 수 정상 범위 여부

### 9.2 Output
- `ocr_quality.json`에 페이지별:
  - `Q` (0~1)
  - `flags[]`
  - `suggested_action` (accept / retry_L1 / retry_L2 / promote_TierB)

---

## 10. Retry Policy (재시도 정책)

### 10.1 단계적 재시도
1) Tier A + Preprocess Level 0
2) 실패/저품질이면 Level 1
3) 여전히 저품질이면 Level 2
4) 그래도 저품질이면 Tier B 승격

### 10.2 제한
- 페이지당 최대 재시도 횟수: 3
- 문서당 Tier B 승격 페이지 비율 상한: 예) 20%

---

## 11. Logging & Reproducibility (로그/재현성)

각 OCR 실행은 반드시 다음을 저장한다.

- OCR 엔진 및 버전
- dpi, color mode
- 전처리 레벨
- 언어 설정
- 페이지별 Q 점수

파일:
- `ocr_run.json`

---

## 12. Reason Codes (OCR 관련)

다음 reason_code는 verification-policy.md와 호환되며,
OCR 파이프라인이 직접 발생시킬 수 있다.

- OCR_POOR_QUALITY
- IMAGE_QUALITY_LOW
- TEXT_ENCODING_BROKEN
- ROTATION_UNHANDLED
- LANGUAGE_UNCERTAIN
- TABLE_HEAVY_LAYOUT

---

## 13. Integration Notes (PDFResolve와의 분리)

- PDFResolve는 **서지정보 확보 및 레코드 생성**까지만 담당한다.
- 본 OCR 프로세스는 비동기/배치로 실행하며,
  결과 PDF(`*_ocr.pdf`)는 원본과 1:1로 연결되어 저장된다.

---

(End of ocr-policy.md)

