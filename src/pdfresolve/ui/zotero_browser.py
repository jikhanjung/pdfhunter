"""Streamlit UI for browsing synced Zotero library."""

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_st():
    return sys.modules.get("streamlit")


def _load_data(db_path: Path):
    """Load collections and items from Zotero SQLite DB."""
    from zoterosync.db import ZoteroDB

    with ZoteroDB(db_path) as db:
        collections = db.get_all_collections()
        items = db.get_all_items()
        sync_state = db.get_sync_state("")  # try empty first
        # Try to get any sync state
        row = db.conn.execute("SELECT * FROM sync_state LIMIT 1").fetchone()
        if row:
            sync_state = dict(row)
    return collections, items, sync_state


def _build_collection_tree(collections: list[dict]) -> dict:
    """Build a nested tree structure from flat collection list.

    Returns:
        dict mapping parent_key -> list of child collections.
        Root collections have parent_key = None or False.
    """
    tree = {}  # parent_key -> [collection, ...]
    for col in collections:
        data = col.get("data", {})
        parent = data.get("parentCollection", None)
        if parent is False or parent == "false":
            parent = None
        tree.setdefault(parent, []).append(col)

    # Sort children by name
    for key in tree:
        tree[key].sort(key=lambda c: c.get("data", {}).get("name", "").lower())

    return tree


def _render_collection_tree(tree: dict, parent_key, level: int, selected_key: str):
    """Recursively render collection tree using radio-like buttons."""
    st = _get_st()
    children = tree.get(parent_key, [])
    result = selected_key

    for col in children:
        col_key = col["key"]
        col_name = col.get("data", {}).get("name", "(unnamed)")
        indent = "\u2003" * level  # em-space for indentation
        prefix = "📂" if col_key in tree else "📁"
        label = f"{indent}{prefix} {col_name}"

        if st.button(label, key=f"col_{col_key}", use_container_width=True):
            result = col_key

        # Recurse into children
        if col_key in tree:
            child_result = _render_collection_tree(tree, col_key, level + 1, result)
            if child_result != result:
                result = child_result

    return result


def _get_items_in_collection(items: list[dict], collection_key: str) -> list[dict]:
    """Filter items that belong to a specific collection."""
    result = []
    for item in items:
        data = item.get("data", {})
        collections = data.get("collections", [])
        if collection_key in collections:
            result.append(item)
    return result


def _group_items_with_attachments(items: list[dict], all_items_by_key: dict) -> list[dict]:
    """Group items: parent items first, with their attachments nested.

    Returns list of dicts with added '_attachments' key for parent items.
    """
    # Separate parent items and attachments
    parent_items = []
    attachments_by_parent = {}  # parentItem key -> [attachment, ...]

    for item in items:
        data = item.get("data", {})
        item_type = data.get("itemType", "")
        parent_item = data.get("parentItem", None)

        if (item_type in ("attachment", "note")) and parent_item:
            attachments_by_parent.setdefault(parent_item, []).append(item)
        else:
            parent_items.append(item)

    # Also find attachments from all_items that belong to these parent items
    parent_keys = {item["key"] for item in parent_items}
    for key, item in all_items_by_key.items():
        data = item.get("data", {})
        parent_item = data.get("parentItem", None)
        if parent_item and parent_item in parent_keys:
            if key not in {a["key"] for attachments in attachments_by_parent.values() for a in attachments}:
                attachments_by_parent.setdefault(parent_item, []).append(item)

    # Attach attachments to parent items
    for item in parent_items:
        item["_attachments"] = attachments_by_parent.get(item["key"], [])

    # Sort by title
    parent_items.sort(key=lambda i: i.get("data", {}).get("title", i.get("data", {}).get("filename", "")).lower())

    return parent_items


def _format_creators(creators: list[dict]) -> str:
    """Format creator list into a string."""
    parts = []
    for c in creators[:3]:
        name = c.get("lastName", c.get("name", ""))
        first = c.get("firstName", "")
        if first:
            parts.append(f"{name}, {first}")
        else:
            parts.append(name)
    if len(creators) > 3:
        parts.append("et al.")
    return "; ".join(parts)


def _is_standalone_pdf(item: dict) -> bool:
    """Check if item is a standalone PDF attachment (no parentItem)."""
    data = item.get("data", {})
    return (
        data.get("itemType") == "attachment"
        and not data.get("parentItem")
        and data.get("contentType", "") == "application/pdf"
    )


def _find_pdf_attachment(attachments: list[dict]) -> dict | None:
    """Find the first PDF attachment in a list of child attachments."""
    for att in attachments:
        att_data = att.get("data", {})
        if att_data.get("contentType", "") == "application/pdf":
            return att
    return None


def _download_zotero_pdf(item_key: str, filename: str) -> Path | None:
    """Download a PDF from Zotero API and save to temp_uploads."""
    from zoterosync.client import ZoteroClient
    from zoterosync.config import ZoteroSyncConfig

    config = ZoteroSyncConfig()
    client = ZoteroClient(config)

    temp_dir = Path("./temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    dest = temp_dir / filename

    try:
        pdf_bytes = client.download_file(item_key)
        dest.write_bytes(pdf_bytes)
        return dest
    except Exception as e:
        logger.error("Failed to download PDF %s: %s", item_key, e)
        return None


def _render_extract_button(item_key: str, filename: str, btn_key: str):
    """Render an Extract button that downloads PDF and switches to Extract tab."""
    st = _get_st()
    if st.button("Extract", key=btn_key, type="primary"):
        with st.spinner(f"Downloading {filename} from Zotero..."):
            pdf_path = _download_zotero_pdf(item_key, filename)
        if pdf_path:
            st.session_state.zotero_extract_file = str(pdf_path)
            st.session_state.zotero_extract_filename = filename
            st.rerun()
        else:
            st.error(f"Failed to download {filename}")


def _render_item_detail(data: dict):
    """Render common item detail fields."""
    st = _get_st()
    creators = data.get("creators", [])
    creator_str = _format_creators(creators) if creators else ""
    if creator_str:
        st.caption(f"Authors: {creator_str}")
    if data.get("publicationTitle"):
        st.caption(f"Journal: {data['publicationTitle']}")
    if data.get("DOI"):
        st.caption(f"DOI: {data['DOI']}")
    if data.get("url"):
        st.caption(f"URL: {data['url']}")


def _render_item_list(items: list[dict], all_items_by_key: dict):
    """Render items as a list with expandable attachments."""
    st = _get_st()

    grouped = _group_items_with_attachments(items, all_items_by_key)

    if not grouped:
        st.info("No items in this collection.")
        return

    st.caption(f"{len(grouped)} items")

    for item in grouped:
        data = item.get("data", {})
        item_type = data.get("itemType", "")
        title = data.get("title", data.get("filename", "(no title)"))
        creators = data.get("creators", [])
        date = data.get("date", "")
        attachments = item.get("_attachments", [])

        # Build display line
        creator_str = _format_creators(creators) if creators else ""
        year_str = f" ({date})" if date else ""
        type_badge = f"`{item_type}`"

        has_children = len(attachments) > 0

        with st.expander(f"📄 **{title}**{year_str} — {creator_str} {type_badge}", expanded=False):
            _render_item_detail(data)

            # Standalone PDF attachment: show Extract button directly
            if _is_standalone_pdf(item):
                filename = data.get("filename", data.get("title", "file.pdf"))
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"
                _render_extract_button(item["key"], filename, f"extract_{item['key']}")

            # Child attachments
            if has_children:
                st.markdown("**Attachments:**")
                for att in attachments:
                    att_data = att.get("data", {})
                    att_type = att_data.get("itemType", "")
                    att_title = att_data.get("title", att_data.get("filename", "(unnamed)"))
                    content_type = att_data.get("contentType", "")
                    icon = "📎" if att_type == "attachment" else "📝"
                    ct_label = f" [{content_type}]" if content_type else ""
                    st.markdown(f"  {icon} {att_title}{ct_label}")

                # If parent item has a PDF attachment, show Extract button
                pdf_att = _find_pdf_attachment(attachments)
                if pdf_att:
                    att_data = pdf_att.get("data", {})
                    filename = att_data.get("filename", att_data.get("title", "file.pdf"))
                    if not filename.lower().endswith(".pdf"):
                        filename += ".pdf"
                    _render_extract_button(
                        pdf_att["key"], filename, f"extract_{pdf_att['key']}"
                    )


def zotero_browser():
    """Main Zotero browser UI component."""
    st = _get_st()
    if st is None:
        raise ImportError("Streamlit is required")

    from zoterosync.config import ZoteroSyncConfig

    config = ZoteroSyncConfig()
    db_path = config.db_path

    if not db_path.exists():
        st.warning("No Zotero database found. Run `zoterosync clone` first.")
        st.code("zoterosync clone -v", language="bash")
        return

    # Load data (cached)
    @st.cache_data(ttl=60)
    def load_data():
        return _load_data(db_path)

    collections, items, sync_state = load_data()

    # Build lookup
    all_items_by_key = {item["key"]: item for item in items}

    # Sync info bar
    if sync_state:
        st.caption(
            f"Library version: {sync_state.get('last_version', '?')} | "
            f"Last synced: {sync_state.get('last_synced_at', '?')} | "
            f"Items: {len(items)} | Collections: {len(collections)}"
        )

    # Two-column layout: collections tree | items list
    col_tree, col_items = st.columns([1, 3])

    with col_tree:
        st.subheader("Collections")

        # "All Items" button
        if "zotero_selected_collection" not in st.session_state:
            st.session_state.zotero_selected_collection = None

        # Render collection tree
        tree = _build_collection_tree(collections)
        selected = _render_collection_tree(
            tree, None, 0, st.session_state.zotero_selected_collection
        )
        if selected != st.session_state.zotero_selected_collection:
            st.session_state.zotero_selected_collection = selected
            st.rerun()

    with col_items:
        selected_key = st.session_state.zotero_selected_collection

        if selected_key is None:
            st.info("Select a collection from the left to view its items.")
        else:
            # Find collection name
            col_name = selected_key
            for col in collections:
                if col["key"] == selected_key:
                    col_name = col.get("data", {}).get("name", selected_key)
                    break
            st.subheader(f"Collection: {col_name}")
            col_items_list = _get_items_in_collection(items, selected_key)
            # Filter out child attachments/notes (ones with parentItem),
            # but keep standalone attachments (directly in collection)
            col_items_list = [
                i for i in col_items_list
                if not (
                    i.get("data", {}).get("itemType") in ("attachment", "note")
                    and i.get("data", {}).get("parentItem")
                )
            ]
            _render_item_list(col_items_list, all_items_by_key)
