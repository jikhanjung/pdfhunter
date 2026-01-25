"""Export modules for CSL-JSON, RIS, BibTeX."""

from pdfhunter.export.bibtex import (
    escape_bibtex,
    export_bibtex,
    export_bibtex_string,
    generate_cite_key,
    record_to_bibtex,
    records_to_bibtex,
)
from pdfhunter.export.csl_json import (
    export_csl_json,
    export_csl_json_string,
    load_csl_json,
    record_to_csl_json,
    records_to_csl_json,
)
from pdfhunter.export.ris import (
    export_ris,
    export_ris_string,
    record_to_ris,
    records_to_ris,
)

__all__ = [
    # CSL-JSON
    "export_csl_json",
    "export_csl_json_string",
    "load_csl_json",
    "record_to_csl_json",
    "records_to_csl_json",
    # RIS
    "export_ris",
    "export_ris_string",
    "record_to_ris",
    "records_to_ris",
    # BibTeX
    "escape_bibtex",
    "export_bibtex",
    "export_bibtex_string",
    "generate_cite_key",
    "record_to_bibtex",
    "records_to_bibtex",
]
