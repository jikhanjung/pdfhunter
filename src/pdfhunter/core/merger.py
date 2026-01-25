from collections import defaultdict

from ..parsing.rule_based import ExtractionResult as RuleResult
from ..parsing.llm_extractor import LLMExtractionResult as LLMResult
from ..models.bibliography import DateParts
from ..models.evidence import Evidence, EvidenceType

class Merger:
    """
    Merges results from rule-based, LLM, and web search extractors.
    """

    def __init__(self):
        """Initializes the merger."""
        self.field_priority = {
            "doi": ["rule"], "issn": ["rule"], "isbn": ["rule"],
            "year": ["rule", "llm"], "volume": ["rule", "llm"],
            "issue": ["rule", "llm"], "page": ["rule", "llm"],
            "title": ["llm", "rule"], "author": ["llm"],
            "container_title": ["llm", "rule"], "abstract": ["llm"],
            "type": ["llm"],
        }

    def merge(self, rule_results: list[RuleResult], llm_result: LLMResult) -> tuple[dict, list[Evidence]]:
        """
        Merges results to produce a final record and a list of all evidence.

        Args:
            rule_results: A list of results from the rule-based extractor (one per page).
            llm_result: The result from the LLM extractor.

        Returns:
            A tuple containing:
            - A dictionary of the merged bibliographic data.
            - A list of all Evidence objects generated.
        """
        # 1. Convert all rule-based matches to Evidence objects
        all_evidence = []
        for res in rule_results:
            for match in res.matches:
                evidence = Evidence(
                    field_name=match.field_name,
                    value=match.value,
                    evidence_type=EvidenceType.PDF_TEXT, # Assume PDF text for now
                    page_number=match.page_number,
                    source_text=match.raw_match,
                    bbox=match.bbox,
                    confidence=match.confidence,
                    metadata={"pattern": match.pattern_name}
                )
                all_evidence.append(evidence)

        # 2. Group rule-based evidence by field and select the best one
        best_rule_evidence = {}
        evidence_by_field = defaultdict(list)
        for ev in all_evidence:
            evidence_by_field[ev.field_name].append(ev)

        for field, evidences in evidence_by_field.items():
            if evidences:
                best_rule_evidence[field] = max(evidences, key=lambda e: e.confidence)

        # 3. Merge with LLM result based on priority
        final_data = {}
        llm_data = llm_result.to_dict()
        
        all_field_names = set(best_rule_evidence.keys()) | set(llm_data.keys()) | set(self.field_priority.keys())

        for field in all_field_names:
            priority = self.field_priority.get(field, ["llm", "rule"])
            
            for source in priority:
                if source == "rule" and field in best_rule_evidence:
                    final_data[field] = best_rule_evidence[field].value
                    break
                elif source == "llm" and llm_data.get(field):
                    final_data[field] = llm_data[field]
                    break
        
        # Add LLM-only fields that might have been missed
        for field in ["author", "abstract", "type"]:
             if field in llm_data:
                final_data[field] = llm_data[field]

        # 4. Handle special cases like 'year' -> 'issued'
        if "year" in final_data:
            try:
                final_data["issued"] = DateParts(year=int(final_data["year"]))
            except (ValueError, TypeError):
                pass # Ignore if year is not a valid integer
            del final_data["year"]
            
        return final_data, all_evidence
