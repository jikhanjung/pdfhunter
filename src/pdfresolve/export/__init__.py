"""Export modules for CSL-JSON, RIS, BibTeX, Zotero JSON."""

from pdfresolve.export.bibtex import (
    escape_bibtex,
    export_bibtex,
    export_bibtex_string,
    generate_cite_key,
    record_to_bibtex,
    records_to_bibtex,
)
from pdfresolve.export.csl_json import (
    export_csl_json,
    export_csl_json_string,
    load_csl_json,
    record_to_csl_json,
    records_to_csl_json,
)
from pdfresolve.export.ris import (
    export_ris,
    export_ris_string,
    record_to_ris,
    records_to_ris,
)
from pdfresolve.export.zotero_json import (
    export_zotero_json,
    export_zotero_json_string,
    record_to_zotero_json,
    records_to_zotero_json,
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
    # Zotero JSON
    "export_zotero_json",
    "export_zotero_json_string",
    "record_to_zotero_json",
    "records_to_zotero_json",
]
