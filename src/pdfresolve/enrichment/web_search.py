"""Enrichment of bibliographic records using web search."""

from scholarly import scholarly

from ..models.bibliography import BibliographyRecord, DateParts


class WebSearchEnricher:
    """
    Enriches a BibliographyRecord by searching online sources.
    """

    def __init__(self):
        """Initializes the web search enricher."""
        # TODO: Re-enable proxy configuration when scholarly/httpx issue is resolved
        pass


    def enrich(self, record: BibliographyRecord) -> BibliographyRecord:
        """
        Performs a web search to find additional details for the record.

        Args:
            record: The bibliographic record to enrich.

        Returns:
            The enriched bibliographic record.
        """
        if not record.title:
            return record

        query = record.title
        if record.author:
            first_author_family_name = record.author[0].family
            if first_author_family_name:
                query += f" {first_author_family_name}"
        
        try:
            pub = scholarly.search_single_pub(query)
            if pub and "bib" in pub:
                bib_data = pub["bib"]
                
                # Merge year if not present
                if not (record.issued and record.issued.year) and "pub_year" in bib_data:
                    record.issued = DateParts(year=int(bib_data["pub_year"]))

                # Merge container-title (venue) if not present
                if not record.container_title and "venue" in bib_data:
                    record.container_title = bib_data["venue"]
                
                # Merge volume if not present
                if not record.volume and "volume" in bib_data:
                    record.volume = bib_data["volume"]
                    
                # Merge pages if not present
                if not record.page and "pages" in bib_data:
                    record.page = bib_data["pages"]

                # TODO:
                # - Add web source as Evidence
                # - More sophisticated merging (e.g., confidence-based)
        except Exception as e:
            print(f"An error occurred during web search: {e}")

        return record
