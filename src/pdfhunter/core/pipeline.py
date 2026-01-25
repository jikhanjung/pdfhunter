"""The main extraction pipeline for PDFHunter."""

import uuid

from .document import Document, DocumentType
from ..models.bibliography import BibliographyRecord, RecordStatus, DateParts
from ..extraction.text_extractor import TextExtractor
from ..extraction.ocr_extractor import OCRExtractor
from ..parsing.rule_based import RuleBasedExtractor
from ..parsing.llm_extractor import LLMExtractor, create_llm_extractor
from ..enrichment.web_search import WebSearchEnricher
from ..enrichment.expansion import ExpansionAgent
from .config import Config
from .merger import Merger


class Pipeline:
    """
    Orchestrates the entire bibliographic extraction process.
    """

    def __init__(self, config: Config | None = None, use_mock_llm: bool = False):
        self.config = config or Config.load()
        self.text_extractor = TextExtractor()
        self.ocr_extractor = OCRExtractor()
        self.rule_based_extractor = RuleBasedExtractor()
        self.web_search_enricher = WebSearchEnricher()
        self.merger = Merger()

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
        
        rule_results = []
        page_texts = []

        # Phase 1: Per-page rule-based extraction
        for page_num in page_indices:
            try:
                if document.document_type == DocumentType.TEXT_PDF:
                    page_text = document.extract_text(page_num)
                else: # SCANNED_PDF or IMAGE
                    image = document.render_page(page_num, dpi=self.config.ocr.high_dpi)
                    ocr_result = self.ocr_extractor.extract(image, page_number=page_num)
                    page_text = ocr_result.raw_text if ocr_result else ""
                
                if page_text.strip():
                    page_texts.append(page_text)
                    rule_results.append(self.rule_based_extractor.extract(page_text, page_number=page_num))
            except Exception:
                # TODO: Add logging for failed pages
                continue

        if not page_texts:
            return BibliographyRecord(id=record_id, status=RecordStatus.FAILED, type="unknown")

        # Phase 2: Document-level LLM extraction
        full_text = "\n\n--- Page Break ---\n\n".join(page_texts)
        llm_result = self.llm_extractor.extract(full_text)

        # Initial Merging
        combined_data, all_evidence = self.merger.merge(rule_results, llm_result)
        
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
