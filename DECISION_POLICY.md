# Decision Policy – 서지 정보 결정 규약

본 문서는 **서지 정보 자동 추출 에이전트**에서 생성되는 여러 후보 정보들 중
**어떤 정보를 신뢰하고 최종 값으로 채택할 것인지**를 결정하는 규약(policy)을 정의한다.

이 문서는 **행동 순서(agent flow)** 를 정의하지 않으며,
오직 **출처 우선순위, 신뢰도 계산, 충돌 해결 방식**만을 다룬다.

---

## 1. Scope

### This document defines
- Source priority (정보 출처 우선순위)
- Confidence scoring (신뢰도 계산)
- Conflict resolution (충돌 해결)
- Provenance recording (근거 기록)

### This document does NOT define
- 에이전트 실행 순서
- 페이지 선택 전략
- OCR / Vision 호출 조건
- 사용자 UI 동작

---

## 2. Core Concepts

### 2.1 Candidate
각 필드는 여러 **후보(candidate)** 값을 가질 수 있다.
후보는 다음 정보를 포함해야 한다.

- value: 추출된 값
- source: 정보 출처
- evidence: 근거 (텍스트 문자열 또는 이미지 영역)
- confidence: 0~1 범위의 점수

---

### 2.2 Source Types

| source | 설명 |
|------|------|
| crossref | Crossref / OpenAlex 등 외부 서지 DB |
| vision | 이미지 기반 Vision LLM |
| llm_text | OCR 텍스트 기반 LLM 구조화 |
| regex | 정규식 기반 추출 |
| pdf_meta | PDF 메타데이터 |
| web | 웹 검색 |

---

## 3. Source Priority

필드별 기본 우선순위는 다음과 같다.

### 3.1 DOI
1. crossref
2. vision / llm_text
3. regex
4. pdf_meta
5. web

### 3.2 Title / Authors
1. crossref
2. vision
3. llm_text
4. regex
5. pdf_meta
6. web

### 3.3 Journal / Container
1. crossref
2. vision
3. llm_text
4. regex
5. pdf_meta
6. web

### 3.4 Year / Volume / Issue / Pages
1. crossref
2. vision
3. llm_text
4. regex
5. pdf_meta
6. web

---

## 4. Confidence Scoring

### 4.1 Base Confidence by Source

| source | base confidence |
|-------|-----------------|
| crossref | 0.95 |
| vision | 0.85 |
| llm_text | 0.80 |
| regex | 0.65 |
| pdf_meta | 0.60 |
| web | 0.55 |

---

### 4.2 Consensus Bonus

- 동일한 value가 **2개 이상의 서로 다른 source**에서 일치할 경우
  - confidence += 0.10
- 3개 이상 일치할 경우
  - confidence += 0.20

최대 confidence는 0.99로 제한한다.

---

### 4.3 Conflict Penalty

- Year 충돌이 ±1년 초과: confidence -= 0.20
- Journal 불일치: confidence -= 0.15
- Title 유사도 낮음(< threshold): confidence -= 0.20

---

## 5. Decision Rules

### 5.1 Field-level Decision

1. 가장 높은 priority source 후보를 기본 선택
2. confidence가 threshold(기본 0.75) 미만이면 `needs_review`
3. consensus 보너스 적용 후 재평가

---

### 5.2 Crossref Override Rule

- crossref 결과가 존재하고
- title + first author + year가 합리적으로 일치하면

→ crossref 값을 최종 값으로 **override**한다.

---

## 6. Provenance Recording

최종 채택된 필드는 반드시 다음 정보를 포함해야 한다.

```json
{
  "value": "...",
  "source": "vision",
  "confidence": 0.92,
  "evidence": "p1: 'Journal of ...'"
}
```

---

## 7. Final Status Assignment

### confirmed
- 핵심 필드(title, authors, year) 존재
- 평균 confidence ≥ 0.80

### needs_review
- 핵심 필드 중 일부 불확실
- 또는 주요 conflict 존재

### failed
- 핵심 필드 다수 누락

---

## 8. Design Rationale

이 정책의 핵심 철학은 다음과 같다.

- **정보는 항상 출처와 함께 판단한다**
- Vision과 LLM은 강력하지만 무오류가 아니다
- Crossref는 정규화의 기준점이다
- 자동화는 항상 검수 가능해야 한다

---

## 9. Usage Note

이 문서는 `agent-flow.md`에서 참조되어 사용되며,
에이전트의 모든 결정은 본 규약을 따라야 한다.

---

(End of decision-policy.md)
