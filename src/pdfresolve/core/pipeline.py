"""The main extraction pipeline for PDFResolve."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from .document import Document, DocumentType
from ..models.bibliography import BibliographyRecord, RecordStatus, DateParts
from ..extraction.text_extractor import TextExtractor
from ..extraction.ocr_extractor import OCRExtractor
from ..parsing.rule_based import RuleBasedExtractor, ExtractionResult
from ..parsing.llm_extractor import LLMExtractor, LLMExtractionResult, create_llm_extractor
from ..enrichment.web_search import WebSearchEnricher
from ..enrichment.expansion import ExpansionAgent
from .config import Config
from .merger import Merger

logger = logging.getLogger(__name__)


@dataclass
class ExtractionDebugInfo:
    """Debug information from extraction pipeline."""

    pdf_metadata: dict = field(default_factory=dict)
    rule_based_results: list[dict] = field(default_factory=list)
    llm_text_result: dict = field(default_factory=dict)
    llm_vision_result: dict = field(default_factory=dict)
    merged_result: dict = field(default_factory=dict)
    conflicts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdf_metadata": self.pdf_metadata,
            "rule_based": self.rule_based_results,
            "llm_text": self.llm_text_result,
            "llm_vision": self.llm_vision_result,
            "merged": self.merged_result,
            "conflicts": self.conflicts,
        }


class Pipeline:
    """
    Orchestrates the entire bibliographic extraction process.
    """

    def __init__(self, config: Config | None = None, use_mock_llm: bool = False, verbose: bool = False):
        self.config = config or Config.load()
        self.verbose = verbose
        self.text_extractor = TextExtractor()
        self.ocr_extractor = OCRExtractor()
        self.rule_based_extractor = RuleBasedExtractor()
        self.web_search_enricher = WebSearchEnricher()
        self.merger = Merger()
        self.debug_info: ExtractionDebugInfo | None = None

        if use_mock_llm:
            self.llm_extractor = create_llm_extractor(use_mock=True)
        else:
            # Get API key from config (loaded from .env or environment)
            api_key = self.config.get_api_key()

            # Auto-select model based on provider only if using default OpenAI model
            llm_config = self.config.llm.model_dump()
            if llm_config["provider"] == "anthropic" and llm_config["model"] in ["gpt-4o-mini", "gpt-4o"]:
                llm_config["model"] = "claude-3-haiku-20240307"

            self.llm_extractor = LLMExtractor(
                **llm_config,
                api_key=api_key,
            )

    def run(self, document: Document) -> BibliographyRecord:
        """
        Runs the full extraction pipeline on a given document.

        Args:
            document: The document to process.

        Returns:
            The extracted and collated bibliographic record.
        """
        record_id = str(uuid.uuid4())
        page_indices = document.get_page_indices()

        rule_results: list[ExtractionResult] = []
        page_texts: list[str] = []
        page_images: list = []  # PIL Images for first few pages

        # Initialize debug info
        self.debug_info = ExtractionDebugInfo()

        # Collect PDF metadata
        pdf_metadata: dict = {}
        if document.is_pdf and document.metadata.has_useful_metadata():
            pdf_metadata = document.metadata.to_dict()
            self.debug_info.pdf_metadata = pdf_metadata
            logger.info(f"PDF metadata available: {pdf_metadata}")

        # Phase 1: Per-page rule-based extraction and collect page images
        for i, page_num in enumerate(page_indices):
            try:
                if document.document_type == DocumentType.TEXT_PDF:
                    page_text = document.extract_text(page_num)
                    # Render first 2 pages as images for vision LLM
                    if i < 2:
                        try:
                            image = document.render_page(page_num, dpi=150)
                            page_images.append(image)
                        except Exception as e:
                            logger.debug(f"Failed to render page {page_num}: {e}")
                else:  # SCANNED_PDF or IMAGE
                    image = document.render_page(page_num, dpi=self.config.ocr.high_dpi)
                    if i < 2:
                        page_images.append(image)
                    ocr_result = self.ocr_extractor.extract(image, page_number=page_num)
                    page_text = ocr_result.raw_text if ocr_result else ""

                if page_text.strip():
                    page_texts.append(page_text)
                    result = self.rule_based_extractor.extract(page_text, page_number=page_num)
                    rule_results.append(result)
                    # Store debug info
                    self.debug_info.rule_based_results.append(result.to_dict())
            except Exception as e:
                logger.debug(f"Failed to process page {page_num}: {e}")
                continue

        if not page_texts:
            return BibliographyRecord(id=record_id, status=RecordStatus.FAILED, type="unknown")

        # Phase 2a: Text-only LLM extraction
        full_text = "\n\n--- Page Break ---\n\n".join(page_texts)
        llm_text_result = self.llm_extractor.extract(full_text, pdf_metadata=pdf_metadata)
        self.debug_info.llm_text_result = llm_text_result.to_dict()
        logger.debug(f"LLM text extraction: {llm_text_result.to_dict()}")

        # Phase 2b: Vision LLM extraction (if images available)
        llm_vision_result: LLMExtractionResult | None = None
        if page_images:
            try:
                llm_vision_result = self.llm_extractor.extract_with_images(
                    full_text, page_images, pdf_metadata=pdf_metadata
                )
                self.debug_info.llm_vision_result = llm_vision_result.to_dict()
                logger.debug(f"LLM vision extraction: {llm_vision_result.to_dict()}")
            except Exception as e:
                logger.warning(f"Vision extraction failed: {e}")

        # Detect conflicts between text and vision LLM results
        if llm_vision_result:
            conflicts = self._detect_conflicts(llm_text_result, llm_vision_result)
            self.debug_info.conflicts = conflicts
            if conflicts:
                logger.info(f"Detected {len(conflicts)} conflicts between text and vision LLM")
                for conflict in conflicts:
                    logger.debug(f"  {conflict['field']}: text='{conflict['text_value']}' vs vision='{conflict['vision_value']}'")

        # Use vision result if available, otherwise fall back to text result
        # Vision LLM generally has better accuracy for structured info like year
        final_llm_result = llm_vision_result if llm_vision_result else llm_text_result

        # Initial Merging (with LLM taking priority for conflicting fields)
        combined_data, all_evidence = self.merger.merge(rule_results, final_llm_result)
        self.debug_info.merged_result = combined_data.copy()

        # Create the initial record
        record = BibliographyRecord(
            id=record_id,
            evidence=all_evidence,
            **combined_data,
            source_file=str(document.file_path.name)
        )

        # Phase 3: Agent Loop for expansion
        agent = ExpansionAgent(pipeline=self, document=document, record=record)
        record = agent.run()

        # Phase 4: Web search enrichment
        record = self.web_search_enricher.enrich(record)

        # Final confidence calculation and status determination
        record.determine_status()

        return record

    def _detect_conflicts(
        self, text_result: LLMExtractionResult, vision_result: LLMExtractionResult
    ) -> list[dict]:
        """Detect conflicts between text and vision LLM results."""
        conflicts = []
        fields_to_check = ["year", "volume", "issue", "page", "title", "container_title"]

        for field in fields_to_check:
            text_val = getattr(text_result, field, None)
            vision_val = getattr(vision_result, field, None)

            if text_val and vision_val and str(text_val) != str(vision_val):
                conflicts.append({
                    "field": field,
                    "text_value": text_val,
                    "vision_value": vision_val,
                })

        return conflicts
