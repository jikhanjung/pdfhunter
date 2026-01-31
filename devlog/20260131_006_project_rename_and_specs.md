# 프로젝트 리네임 및 스펙 문서 추가

**날짜**: 2026-01-31
**커밋**: 126fbb8, 615d3bc, 207c163

---

## 요약

프로젝트 이름을 `pdfhunter`에서 `pdfresolve`로 전면 변경하고, 스펙 문서 및 Streamlit 런처 스크립트를 추가했습니다.

---

## 변경 내역

### 1. 스펙 문서 및 Streamlit 런처 추가 (126fbb8)

프로젝트의 목표와 제약 조건을 명문화한 스펙 문서를 `specs/` 디렉토리에 추가했습니다.

- `specs/problem.md` — 해결하려는 문제 정의
- `specs/goals.md` — 프로젝트 목표
- `specs/non-goals.md` — 범위 밖 항목
- `specs/constraints.md` — 기술적 제약 조건
- `specs/acceptance.md` — 인수 기준

`run_ui.py`를 추가하여 `streamlit run run_ui.py`로 리뷰 UI를 바로 실행할 수 있게 했습니다.

### 2. temp_uploads 디렉토리 gitignore 추가 (615d3bc)

Streamlit UI에서 업로드한 임시 PDF 파일이 git에 포함되지 않도록 `.gitignore`에 `temp_uploads/`를 추가했습니다.

### 3. pdfhunter → pdfresolve 리네임 (207c163)

패키지명, 모듈 경로, import 문, CLI 엔트리포인트, 테스트, 설정 파일 전체를 `pdfhunter`에서 `pdfresolve`로 일괄 변경했습니다.

**주요 변경:**
- `src/pdfhunter/` → `src/pdfresolve/` 디렉토리 이동
- `pyproject.toml`의 패키지명, 빌드 설정, CLI 엔트리포인트 변경
- `CLAUDE.md` 내 모든 참조 업데이트
- 53개 파일에 걸쳐 import 경로 및 참조 수정
- 테스트 파일 내 모든 import 경로 업데이트

---

## 영향

- CLI 명령어가 `pdfresolve`로 통일
- 기존 `pdfhunter` 이름의 흔적 완전 제거
- 프로젝트 방향성을 스펙 문서로 명확히 정의
