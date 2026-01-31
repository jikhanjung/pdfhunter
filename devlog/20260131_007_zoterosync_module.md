# ZoteroSync 모듈 구현 및 Streamlit 통합

**날짜**: 2026-01-31

---

## 요약

Zotero Web API를 통해 사용자의 Zotero 라이브러리를 로컬 SQLite DB에 동기화하는 독립 모듈 `zoterosync`를 구현했습니다. 독립 CLI(`zoterosync`)로 실행 가능하며, Streamlit UI에 Zotero Library 브라우저 탭을 추가하여 컬렉션/아이템 탐색 및 PDF 추출 연계 기능을 구현했습니다.

---

## 구현 내용

### 1. zoterosync 독립 모듈 (`src/zoterosync/`)

| 파일 | 역할 |
|------|------|
| `__init__.py` | 공개 API 노출 |
| `config.py` | `ZoteroSyncConfig` (pydantic-settings, `.env`에서 API 키/라이브러리 ID 로드) |
| `db.py` | SQLite 스키마(items, collections, sync_state) 및 CRUD |
| `client.py` | pyzotero 래퍼, 수동 페이지네이션 + 진행상황 콜백, 파일 다운로드 |
| `sync.py` | `full_clone()`, `incremental_sync()` — 단방향 동기화 로직 |
| `export.py` | DB → JSON 파일 내보내기 |
| `cli.py` | 독립 CLI 엔트리포인트 (`zoterosync clone/sync/export/status`) |

**주요 설계 결정:**
- `pyzotero.everything()` 대신 수동 페이지네이션으로 진행상황 콜백 지원
- `-v`/`--verbose` 옵션으로 fetch 진행률 실시간 출력 (예: `Fetched 200/1523 items`)
- `pdfresolve`와 독립된 별도 CLI 실행파일로 구성
- `ZoteroSyncConfig`에 `extra="ignore"` 설정으로 `.env`의 다른 키와 충돌 방지

### 2. Streamlit UI 통합

- **탭 구조 변경**: 기존 단일 페이지를 `Extract` / `Zotero Library` 두 탭으로 분리
- **Zotero Library 탭** (`zotero_browser.py`):
  - 왼쪽: 컬렉션 트리 (중첩 계층 지원)
  - 오른쪽: 선택한 컬렉션의 아이템 목록
  - parent item 아래 attachment를 그룹으로 표시
  - standalone PDF attachment (parentItem 없는 PDF)도 정상 표시
  - **Extract 버튼**: 클릭 시 Zotero API에서 PDF 다운로드 → Extract 탭으로 전달하여 자동 파이프라인 실행
- `use_column_width` → `use_container_width` deprecation 경고 수정

### 3. pyproject.toml 변경

- `pyzotero>=1.5` 의존성 추가
- `src/zoterosync` 패키지 등록
- `zoterosync` CLI 엔트리포인트 추가

### 4. 테스트

- `tests/test_zoterosync.py`: DB CRUD, config, export, full_clone, incremental_sync 총 10개 테스트 (모두 통과)

---

## 사용법

```bash
# .env 설정
ZOTERO_API_KEY=your_key
ZOTERO_LIBRARY_ID=your_id

# 전체 클론 (verbose)
zoterosync clone -v

# 증분 동기화
zoterosync sync

# 상태 확인
zoterosync status

# JSON 내보내기
zoterosync export -o data/zotero/export

# Streamlit UI
streamlit run run_ui.py
```

---

## 파일 목록

**신규:**
- `src/zoterosync/__init__.py`
- `src/zoterosync/config.py`
- `src/zoterosync/db.py`
- `src/zoterosync/client.py`
- `src/zoterosync/sync.py`
- `src/zoterosync/export.py`
- `src/zoterosync/cli.py`
- `src/pdfresolve/ui/zotero_browser.py`
- `tests/test_zoterosync.py`

**수정:**
- `pyproject.toml`
- `src/pdfresolve/ui/review_ui.py`
