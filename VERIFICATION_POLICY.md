# Verification Policy – 서지 정보 검증 및 사용자 확인 규약

본 문서는 **서지 정보 자동 추출 에이전트**에서 생성된 결과를
어떤 기준으로 자동 확정하고, 어떤 경우에 사용자 확인(confirmation)을 요구할지 정의한다.

목표는 대규모 처리(예: 10,000 PDF 이상) 환경에서
**사람의 개입을 최소화하면서도 품질을 통제**하는 것이다.

---

## 1. Verification의 기본 철학

* 사용자 확인은 **전수 검사**가 아니라 **리스크 기반 예외 처리**이다
* 확인 대상은 "불확실성"이 아니라 **"결정 실패 가능성"** 이다
* 자동 확정 결과도 **감사(audit)** 대상이 될 수 있다

---

## 2. Verification Status 정의

### 2.1 confirmed_auto

다음 조건을 모두 만족하면 사용자 확인 없이 자동 확정한다.

* DOI 존재 + Crossref 강매칭

  * title / first author / year 일치 또는 준일치
* 또는 핵심 필드(title, authors, year)가

  * 서로 다른 source 2개 이상에서 합의(consensus)
* 주요 conflict 없음

---

### 2.2 needs_review

사람의 판단이 필요한 경우.

* DOI 없음 + 핵심 구조 필드 다수 누락
* title / author / year 간 충돌 발생
* Vision 또는 LLM 단일 source 의존도가 높음
* web source가 핵심 필드에 사용됨
* 문서 유형(journal vs series vs report) 불확실

---

### 2.3 failed

자동 추출이 의미 있는 후보를 생성하지 못한 경우.

* OCR / Vision 모두 핵심 필드 추출 실패
* 타이틀 페이지 또는 콜로폰 부재

---

## 3. 사용자 확인(Confirmation) 설계

### 3.1 확인 대상

* 기본 대상: `needs_review`
* 선택 대상: `confirmed_auto` 중 샘플 감사

---

### 3.2 확인 방식

사용자 확인은 **편집 중심이 아닌 결정 중심 UI**를 따른다.

* Accept: 제안 결과 그대로 확정
* Quick Fix: 최소 수정 후 확정
* Reject / Re-run: 재탐색 또는 실패 처리

---

## 4. 샘플링 감사 (Audit Sampling)

자동 확정 품질 유지를 위해 일부 레코드를 무작위 또는 조건부로 확인한다.

### 권장 전략

* 전체 confirmed_auto의 1–2% 무작위 샘플
* 고위험 조건 기반 샘플

  * 오래된 연도 (예: < 1970)
  * 비영어 OCR 문서
  * Vision 단독 확정 케이스

---

## 5. Rule-level Confirmation (고급)

반복되는 확인 패턴은 **규칙 승인(rule confirmation)** 으로 승격할 수 있다.

예:

* 특정 저널의 권호 표기 규칙
* 특정 기관 보고서의 콜로폰 위치

승인된 규칙은 이후 자동 확정 경로로 편입된다.

---

## 6. Reason Codes

`needs_review` 또는 `failed` 상태의 원인을 명시적으로 기록한다.

### 6.1 Core Field Issues

* NO_TITLE
* NO_AUTHORS
* NO_YEAR
* NO_JOURNAL
* NO_PAGES
* NO_VOLUME_ISSUE

---

### 6.2 Conflict Issues

* TITLE_CONFLICT
* AUTHOR_CONFLICT
* YEAR_CONFLICT_MINOR (±1)
* YEAR_CONFLICT_MAJOR (≥±2)
* JOURNAL_CONFLICT

---

### 6.3 Source Reliability Issues

* SINGLE_SOURCE_ONLY
* VISION_ONLY
* LLM_TEXT_ONLY
* WEB_ONLY
* LOW_CONFIDENCE_CORE_FIELD

---

### 6.4 Structure / Type Issues

* DOCUMENT_TYPE_UNCERTAIN
* SERIES_VS_JOURNAL_AMBIGUOUS
* REPORT_METADATA_ONLY

---

### 6.5 Data Quality Issues

* OCR_POOR_QUALITY
* IMAGE_QUALITY_LOW
* TEXT_ENCODING_BROKEN

---

### 6.6 External Validation Issues

* NO_CROSSREF_MATCH
* MULTIPLE_CROSSREF_CANDIDATES

---

## 7. Verification Log Requirements

각 레코드는 최소 다음 정보를 기록해야 한다.

* verification_status
* reason_codes[]
* confidence_summary (min / avg)
* sources_used[]
* user_action (if any)
* timestamp

---

## 8. Design Targets (10,000 PDF 기준)

* confirmed_auto: 85–95%
* needs_review: 5–15%
* failed: < 3%

---

## 9. Design Rationale

이 정책은 다음을 전제로 한다.

* 자동화의 목적은 인간을 제거하는 것이 아니라
  **인간의 판단을 가장 필요한 곳에 집중시키는 것**이다.
* 검증은 단발 이벤트가 아니라
  **지속적인 품질 관리 프로세스**이다.

---

(End of verification-policy.md)
