"""Zotero API client wrapper using pyzotero."""

from typing import Callable, Optional

from pyzotero import zotero

from zoterosync.config import ZoteroSyncConfig

# Type for progress callback: (fetched_so_far, total_or_none)
ProgressCallback = Callable[[int, Optional[int]], None]


class ZoteroClient:
    """Wrapper around pyzotero with automatic pagination."""

    ITEMS_PER_PAGE = 100

    def __init__(self, config: ZoteroSyncConfig):
        self.config = config
        self.zot = zotero.Zotero(
            config.zotero_library_id,
            config.zotero_library_type,
            config.zotero_api_key,
        )

    def get_library_version(self) -> int:
        """Get the current library version number."""
        self.zot.items(limit=1)
        return int(self.zot.request.headers.get("Last-Modified-Version", 0))

    def _fetch_paginated(
        self,
        method,
        on_progress: Optional[ProgressCallback] = None,
        **kwargs,
    ) -> list[dict]:
        """Fetch all results with manual pagination and progress reporting."""
        all_results = []
        start = 0
        total = None

        while True:
            batch = method(limit=self.ITEMS_PER_PAGE, start=start, **kwargs)

            if total is None and self.zot.request is not None:
                total_header = self.zot.request.headers.get("Total-Results")
                if total_header is not None:
                    total = int(total_header)

            all_results.extend(batch)

            if on_progress:
                on_progress(len(all_results), total)

            if len(batch) < self.ITEMS_PER_PAGE:
                break

            start += self.ITEMS_PER_PAGE

        return all_results

    def fetch_all_items(
        self, on_progress: Optional[ProgressCallback] = None
    ) -> list[dict]:
        """Fetch all items with progress reporting."""
        return self._fetch_paginated(self.zot.items, on_progress=on_progress)

    def fetch_all_collections(
        self, on_progress: Optional[ProgressCallback] = None
    ) -> list[dict]:
        """Fetch all collections with progress reporting."""
        return self._fetch_paginated(self.zot.collections, on_progress=on_progress)

    def fetch_items_since(
        self, version: int, on_progress: Optional[ProgressCallback] = None
    ) -> list[dict]:
        """Fetch items modified since the given version."""
        return self._fetch_paginated(
            self.zot.items, on_progress=on_progress, since=version
        )

    def fetch_collections_since(
        self, version: int, on_progress: Optional[ProgressCallback] = None
    ) -> list[dict]:
        """Fetch collections modified since the given version."""
        return self._fetch_paginated(
            self.zot.collections, on_progress=on_progress, since=version
        )

    def fetch_deleted_since(self, version: int) -> dict:
        """Fetch keys of items/collections deleted since the given version."""
        return self.zot.deleted(since=version)

    def download_file(self, item_key: str) -> bytes:
        """Download the file content for an attachment item."""
        return self.zot.file(item_key)
