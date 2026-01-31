# Acceptance Criteria

## 필수 기준

### 1. 서지 정보 추출
- [ ] 텍스트 PDF에서 핵심 필드(title, authors, year)를 추출할 수 있다.
- [ ] 스캔 PDF에서 OCR을 통해 핵심 필드를 추출할 수 있다.
- [ ] 단일 이미지(표지/타이틀 페이지)에서 서지 정보를 추출할 수 있다.

### 2. 다중 소스 결합
- [ ] 규칙 기반(regex), LLM, Vision 중 2개 이상의 소스를 결합하여 결과를 생성한다.
- [ ] 동일 값이 복수 소스에서 일치하면 consensus bonus가 적용된다.
- [ ] 소스 간 충돌 시 Decision Policy에 따라 해결한다.

### 3. Evidence 추적
- [ ] 모든 추출 필드에 페이지 번호와 원문 근거가 첨부된다.
- [ ] 사용자 검수 UI에서 근거 이미지와 bbox를 확인할 수 있다.

### 4. 상태 분류
- [ ] confidence 기반으로 confirmed / needs_review / failed 상태가 자동 할당된다.
- [ ] needs_review 레코드에 reason_code가 기록된다.

### 5. 출력
- [ ] CSL-JSON 형식으로 내보내기가 동작한다.
- [ ] RIS 형식으로 내보내기가 동작한다.
- [ ] BibTeX 형식으로 내보내기가 동작한다.

### 6. CLI
- [ ] `pdfhunter info <file.pdf>`: 문서 기본 정보를 표시한다.
- [ ] `pdfhunter extract <file.pdf> -o output.json`: 서지 정보를 추출하여 파일로 저장한다.

### 7. 사용자 검수 UI
- [ ] PDF 업로드 후 추출 결과를 확인할 수 있다.
- [ ] 추출된 필드를 수정할 수 있다.
- [ ] Evidence 이미지를 페이지별로 확인할 수 있다.

## 품질 목표 (10,000 PDF 기준)

- [ ] confirmed_auto 비율: 85% 이상
- [ ] needs_review 비율: 15% 이하
- [ ] failed 비율: 3% 미만
- [ ] 핵심 필드(title, authors, year) 정확도: 90% 이상 (confirmed 레코드 기준)
