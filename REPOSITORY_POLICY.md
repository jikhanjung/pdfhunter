# Repository Policy – PDFResolve / TextResolve 모노레포 관리 방침

본 문서는 **PDFResolve**(서지 정보 해석·결정 에이전트)와 **TextResolve**(본문 OCR 및 텍스트 레이어 생성 모듈)를
**하나의 GitHub repository(모노레포)** 로 관리하기 위한 원칙과 구조를 정의한다.

이 방침의 목적은 다음을 동시에 만족시키는 것이다.

- 개발·실험 단계에서의 생산성
- 모듈 간 스키마·정책 일관성 유지
- 향후 분리 배포/제품화 가능성 확보

---

## 1. 기본 방침 (One Repo, Multiple Packages)

### 원칙

- **코드는 하나의 repository에 둔다** (monorepo)
- **배포 단위는 모듈별로 분리한다**
  - `pdfresolve`
  - `textresolve`

즉,

> *One repository, multiple installable packages*

를 기본 전략으로 한다.

---

## 2. 왜 모노레포인가?

### 2.1 동일 도메인

- 두 모듈은 모두 **PDF 처리 파이프라인**에 속한다.
- 페이지 선택, 렌더링, 품질 평가, evidence 저장 등
  다수의 개념과 코드가 공유된다.

### 2.2 정책·스키마 공유

- `decision-policy.md`
- `verification-policy.md`
- `ocr-policy.md`

와 같은 정책 문서는 **모듈 공통 규약**이며,
분리된 repo로 관리할 경우 불일치 위험이 커진다.

### 2.3 변경 전파 용이성

- 서지 레코드 스키마 변경
- evidence 포맷 변경
- reason_codes 확장

과 같은 변경을 **원자적으로 적용**할 수 있다.

---

## 3. 권장 Repository 구조

```text
repo/
  README.md

  docs/
    agent-flow.md
    decision-policy.md
    verification-policy.md
    ocr-policy.md
    repository-policy.md

  packages/
    pdfresolve/
      pyproject.toml
      src/
      tests/

    textresolve/
      pyproject.toml
      src/
      tests/

  shared/
    src/
      pdf_rendering/
      page_selection/
      schemas/
      logging/
      quality_metrics/

  samples/
  tools/
```

---

## 4. 패키지 분리 원칙

### 4.1 pdfresolve

- 책임 범위
  - 서지 정보 추출
  - Vision/LLM/외부 DB 결합
  - decision / verification 정책 적용

- 범위 외
  - 대량 본문 OCR
  - 텍스트 레이어 재구성

---

### 4.2 textresolve

- 책임 범위
  - 스캔 PDF 본문 OCR
  - 텍스트 레이어 삽입
  - OCR 품질 평가 및 재시도

- 범위 외
  - 서지 결정 로직
  - 사용자 검수 UI

---

## 5. Shared 코드 관리 원칙

- `shared/`는 **순수 라이브러리 코드만 포함**한다.
- 비즈니스 로직은 각 패키지에 둔다.
- `shared` 변경은 반드시 두 패키지 테스트를 모두 통과해야 한다.

---

## 6. 버전 관리 및 릴리즈

### 6.1 독립 버전

- `pdfresolve`와 `textresolve`는 **독립적인 버전 번호**를 가진다.
- 단, 공통 스키마 변경 시 릴리즈 노트에 명시한다.

### 6.2 배포 전략

- 하나의 repo에서:
  - `pip install pdfresolve`
  - `pip install textresolve`

와 같이 **개별 배포**를 목표로 한다.

---

## 7. 언제 분리 Repo를 고려하는가?

다음 조건 중 하나라도 충족되면 멀티레포 전환을 검토한다.

1. 배포 대상 사용자가 완전히 분리됨
2. 실행 환경/의존성 충돌이 지속적으로 발생
3. 모듈별 전담 팀 또는 외부 기여자 분리
4. TextResolve를 범용 OCR 라이브러리로 독립 배포하고자 할 때

그 전까지는 **모노레포 유지가 기본값**이다.

---

## 8. 설계 철학 요약

- Repo 분리는 **조직/제품 단계의 문제**이지 초기 설계의 문제가 아니다.
- 초기에는 일관성과 속도가 가장 중요하다.
- 분리는 언제든 가능하지만, 분리 후 재통합은 어렵다.

---

(End of repository-policy.md)

