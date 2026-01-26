# LLM Vision 기반 추출 기능 구현

**날짜**: 2026-01-25
**작업**: 이미지 기반 멀티모달 LLM 추출 메서드 구현

---

## 요약

`llm_extractor.py`에 미완성 상태로 남아있던 이미지 기반 추출 메서드를 구현했습니다. 이제 PDF 페이지 이미지와 텍스트를 함께 멀티모달 LLM에 전송하여 더 정확한 서지정보 추출이 가능합니다.

---

## 배경

이전 구현에서 `extract_with_images()` 메서드가 다음 두 메서드를 호출하도록 되어 있었으나 실제 구현이 누락되어 있었습니다:

```python
# 301-304라인 (기존 코드)
if self.provider == "openai":
    return self._extract_openai_with_images(prompt, images)  # 미구현
else:
    return self._extract_anthropic_with_images(prompt, images)  # 미구현
```

---

## 구현 내용

### 1. `_extract_openai_with_images()` 메서드

OpenAI Vision API를 사용하여 이미지와 텍스트를 함께 전송합니다.

**주요 특징:**
- GPT-4o, GPT-4o-mini 등 Vision 지원 모델과 호환
- 이미지를 base64로 인코딩하여 전송
- `detail: "high"` 설정으로 고해상도 이미지 분석

```python
def _extract_openai_with_images(self, prompt: str, images: list) -> LLMExtractionResult:
    client = self._get_openai_client()

    content = [{"type": "text", "text": prompt}]
    for image in images:
        base64_image = self._encode_image_to_base64(image)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
                "detail": "high",
            },
        })

    response = client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": "..."},
            {"role": "user", "content": content},
        ],
        response_format={"type": "json_object"},
    )
    # ...
```

### 2. `_extract_anthropic_with_images()` 메서드

Anthropic Claude Vision API를 사용합니다.

**주요 특징:**
- Claude 3 Haiku, Sonnet, Opus 등 Vision 지원 모델과 호환
- Anthropic API 형식에 맞게 이미지를 content 배열 앞에 배치
- `media_type: "image/jpeg"` 명시

```python
def _extract_anthropic_with_images(self, prompt: str, images: list) -> LLMExtractionResult:
    client = self._get_anthropic_client()

    content = []
    for image in images:
        base64_image = self._encode_image_to_base64(image)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64_image,
            },
        })
    content.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=self.model,
        max_tokens=self.max_tokens,
        messages=[{"role": "user", "content": content}],
        system="...",
    )
    # ...
```

### 3. `MockLLMExtractor.extract_with_images()` 메서드

테스트용 mock 구현. 이미지를 무시하고 텍스트 기반 추출로 위임합니다.

```python
def extract_with_images(self, text: str, images: list, max_text_length: int = 4000) -> LLMExtractionResult:
    return self.extract(text, max_text_length)
```

---

## 추가된 테스트

`tests/test_parsing.py`에 5개 테스트 추가:

| 테스트 | 설명 |
|--------|------|
| `test_mock_extract_with_images` | Mock extractor가 이미지와 함께 올바르게 동작하는지 확인 |
| `test_mock_extract_with_images_empty_list` | 빈 이미지 리스트 처리 확인 |
| `test_encode_image_to_base64` | RGB 이미지 base64 인코딩 확인 |
| `test_encode_image_to_base64_rgba` | RGBA 이미지 RGB 변환 후 인코딩 확인 |
| `test_extract_with_images_no_images` | 이미지 없을 때 텍스트 전용 추출로 폴백 확인 |

---

## 테스트 결과

```
======================== 176 passed, 1 xfailed, 1 warning ==================
```

| 상태 | 개수 | 비고 |
|------|------|------|
| passed | 176 | 기존 170 + 신규 6 (5개 테스트 + 기타) |
| xfailed | 1 | PaddleOCR 환경 이슈 (expected fail) |

---

## 파일 변경 목록

| 파일 | 변경 내용 |
|------|-----------|
| `parsing/llm_extractor.py` | `_extract_openai_with_images()`, `_extract_anthropic_with_images()`, `MockLLMExtractor.extract_with_images()` 추가 |
| `tests/test_parsing.py` | Vision 관련 테스트 5개 추가 |

---

## 사용 예시

```python
from pdfhunter.parsing.llm_extractor import LLMExtractor
from PIL import Image

# OpenAI Vision 사용
extractor = LLMExtractor(provider="openai", model="gpt-4o")
images = [Image.open("page1.png"), Image.open("page2.png")]
result = extractor.extract_with_images(ocr_text, images)

# Anthropic Vision 사용
extractor = LLMExtractor(provider="anthropic", model="claude-3-5-sonnet-20241022")
result = extractor.extract_with_images(ocr_text, images)
```

---

## 다음 단계

1. **파이프라인에 Vision 추출 통합** - `pipeline.py`에서 `extract_with_images()` 호출하도록 수정
2. **실제 API 통합 테스트** - 실제 PDF 이미지로 Vision 모델 정확도 검증
3. **이미지 최적화** - 토큰 비용 절감을 위한 이미지 리사이징/압축 옵션 추가
4. **선택적 Vision 사용** - 텍스트 추출 실패 시에만 Vision 사용하는 폴백 로직

---

## 기타

### .gitignore 추가

프로젝트 초기 커밋 시 `.pyc`, `__pycache__/`, `.env`, `pdfs/` 등이 포함되는 문제를 해결하기 위해 `.gitignore` 파일을 생성했습니다.
