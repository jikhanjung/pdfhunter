"""
The Agent loop for automatically expanding the search for missing fields.
"""
from ..core.document import Document
from ..models.bibliography import BibliographyRecord, RecordStatus


class ExpansionAgent:
    """
    An agent that intelligently decides to perform additional extraction steps
    if the initial result is incomplete.
    """

    def __init__(self, pipeline: "Pipeline", document: Document, record: BibliographyRecord, max_iterations: int = 2):
        """
        Initializes the expansion agent.

        Args:
            pipeline: The main extraction pipeline.
            document: The document being processed.
            record: The initial bibliography record to improve.
            max_iterations: The maximum number of expansion loops to perform.
        """
        self.pipeline = pipeline
        self.document = document
        self.record = record
        self.max_iterations = max_iterations
        self.iteration = 0
        self.tried_running_headers = False
        self.tried_last_pages = False

    def run(self) -> BibliographyRecord:
        """
        Runs the agent loop to enrich the record.

        Returns:
            The improved BibliographyRecord.
        """
        while self.iteration < self.max_iterations:
            self.iteration += 1
            
            if self._is_complete():
                break

            action_taken = self._choose_and_execute_action()
            if not action_taken:
                # Stop if no more actions can be taken
                break
        
        # Final status determination
        self.record.determine_status()
        return self.record

    def _is_complete(self) -> bool:
        """
        Checks if the record is sufficiently complete.
        """
        if self.record.type == "article-journal":
            return all([
                self.record.title,
                self.record.author,
                self.record.issued,
                self.record.container_title,
                self.record.page,
                self.record.volume
            ])
        elif self.record.type == "book":
            return all([
                self.record.title,
                self.record.author,
                self.record.issued,
                self.record.publisher,
                self.record.publisher_place
            ])
        # For other types, we might have different completeness criteria
        return all([self.record.title, self.record.author, self.record.issued])

    def _choose_and_execute_action(self) -> bool:
        """
        Chooses and executes the next best action to improve the record.
        """
        # Rule 1: For articles missing page or volume, look for running headers
        if self.record.type == "article-journal" and not (self.record.page and self.record.volume) and not self.tried_running_headers:
            return self._action_find_running_headers()
            
        # Rule 2: For any type, if publisher/place is missing, check last pages
        if not (self.record.publisher and self.record.publisher_place) and not self.tried_last_pages:
            return self._action_find_publication_info()
            
        return False

    def _action_find_running_headers(self) -> bool:
        """
        Action: Scans page headers for volume/page numbers.
        """
        self.tried_running_headers = True
        if not self.document.is_pdf or self.document.page_count < 5:
            return False

        # Searching for running headers
        
        # Strategy: check a few pages from the middle
        pages_to_scan = [p for p in [4, 5, 6] if p < self.document.page_count]
        
        
        headers_text = []
        for page_num in pages_to_scan:
            try: # Restored try...except block
                full_image = self.document.render_page(page_num, dpi=150)
                
                # Crop the top 15% for the header
                width, height = full_image.size
                header_box = (0, 0, width, int(height * 0.15))
                header_image = full_image.crop(header_box)
                
                # Extract text from the header
                ocr_result = self.pipeline.ocr_extractor.extract(header_image, page_number=page_num)
                if ocr_result.raw_text:
                    headers_text.append(ocr_result.raw_text)
            except Exception:
                continue # Ignore pages that fail to render/OCR
        
        if not headers_text:
            return False
            
        # Use rule-based extractor to find patterns in the combined header text
        combined_text = "\n".join(headers_text)
        rule_result = self.pipeline.rule_based_extractor.extract(combined_text)
        
        # Select best matches for page and volume from the collected evidence
        best_page_match = None
        best_volume_match = None
        
        for match in rule_result.matches:
            if match.field_name == "pages" and (not best_page_match or match.confidence > best_page_match.confidence):
                best_page_match = match
            if match.field_name == "volume" and (not best_volume_match or match.confidence > best_volume_match.confidence):
                best_volume_match = match
        
        action_taken = False
        if not self.record.page and best_page_match:
            self.record.page = best_page_match.value
            action_taken = True

        if not self.record.volume and best_volume_match:
            self.record.volume = best_volume_match.value
            action_taken = True

        return action_taken

    def _action_find_publication_info(self) -> bool:
        """
        Action: Scans last pages for publisher and place information.
        """
        self.tried_last_pages = True
        if not self.document.is_pdf or self.document.page_count < 1:
            return False

        pages_to_scan = []
        if self.document.page_count >= 1:
            pages_to_scan.append(self.document.page_count)
        if self.document.page_count >= 2:
            pages_to_scan.append(self.document.page_count - 1)

        if not pages_to_scan:
            return False

        last_pages_text = []
        for page_num in pages_to_scan:
            try:
                full_image = self.document.render_page(page_num, dpi=150)
                ocr_result = self.pipeline.ocr_extractor.extract(full_image, page_number=page_num)
                if ocr_result.raw_text:
                    last_pages_text.append(ocr_result.raw_text)
            except Exception:
                continue

        if not last_pages_text:
            return False

        combined_text = "\n".join(last_pages_text)

        # Use rule-based extractor for place
        rule_result = self.pipeline.rule_based_extractor.extract(combined_text)
        best_place_match = None
        for match in rule_result.matches:
            if match.field_name == "place" and (not best_place_match or match.confidence > best_place_match.confidence):
                best_place_match = match

        action_taken = False
        if not self.record.publisher_place and best_place_match:
            self.record.publisher_place = best_place_match.value
            action_taken = True

        # Use LLM extractor for publisher (more complex to regex)
        llm_result = self.pipeline.llm_extractor.extract(combined_text)
        if not self.record.publisher and llm_result.publisher:
            self.record.publisher = llm_result.publisher
            action_taken = True

        return action_taken
