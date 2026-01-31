"""Streamlit review UI for PDFResolve."""

import sys
from pathlib import Path

from PIL import ImageDraw

from ..models.bibliography import BibliographyRecord, Author, DateParts
from ..core.document import Document
from ..core.pipeline import Pipeline


def _get_st():
    """Get streamlit module, supporting mocking in tests."""
    return sys.modules.get('streamlit')


def review_ui(record: BibliographyRecord, document: Document):
    """
    Main UI component for the review screen.
    """
    st = _get_st()
    if st is None:
        raise ImportError("Streamlit is required for the review UI")

    st.info(f"Record ID: {record.id} | Status: {record.status.value.upper()}")

    # Main layout with two columns
    col1, col2 = st.columns(2)

    with col1:
        st.header("Extracted Fields")

        record.title = st.text_input("Title", value=record.title or "")
        st.subheader("Authors")
        if record.author:
            for i, author in enumerate(record.author):
                st.text(f"  {i+1}. {author.given or ''} {author.family or ''}")
        else:
            st.text("No authors found.")
        record.type = st.selectbox("Document Type", options=["article-journal", "book", "chapter", "report", "thesis"], index=0)
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            record.volume = st.text_input("Volume", value=record.volume or "")
        with c2:
            record.issue = st.text_input("Issue", value=record.issue or "")
        with c3:
            if record.issued:
                record.issued.year = st.number_input("Year", value=record.issued.year if record.issued else 2000)
        record.page = st.text_input("Pages", value=record.page or "")
        record.container_title = st.text_input("Container Title (Journal/Book)", value=record.container_title or "")


    with col2:
        st.header("Evidence")

        if not record.evidence:
            st.warning("No evidence was collected for this record.")
        else:
            page_numbers = sorted(list(set(ev.page_number for ev in record.evidence if ev.page_number is not None)))
            if not page_numbers:
                st.info("No evidence with page information found.")
            else:
                selected_page = st.selectbox("View Evidence for Page:", options=page_numbers)

                if selected_page:
                    try:
                        # Render the page image
                        image = document.render_page(selected_page, dpi=150).convert("RGB")
                        draw = ImageDraw.Draw(image)

                        # Get evidence for this page
                        page_evidence = [ev for ev in record.evidence if ev.page_number == selected_page and ev.bbox]

                        for ev in page_evidence:
                            if ev.bbox:
                                box = [ev.bbox.x1, ev.bbox.y1, ev.bbox.x2, ev.bbox.y2]
                                draw.rectangle(box, outline="red", width=2)
                                if ev.field_name:
                                    draw.text((box[0], box[1] - 10), ev.field_name, fill="red")

                        st.image(image, caption=f"Evidence on Page {selected_page}", use_column_width=True)

                    except Exception as e:
                        st.error(f"Failed to render page {selected_page}: {e}")

    st.divider()

    # --- Actions ---
    st.header("Actions")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("✅ Save and Confirm", use_container_width=True):
            st.success("Record saved and confirmed!")
    with c2:
        if st.button("💾 Save as 'Needs Review'", use_container_width=True):
            st.info("Record saved.")
    with c3:
        if st.button("🌐 Re-run Web Enrichment", use_container_width=True):
            st.toast("Web enrichment not implemented yet.")
    with c4:
        if st.button("❌ Mark as Failed", use_container_width=True):
            st.error("Record marked as failed.")


def main_app():
    """Main Streamlit application."""
    st = _get_st()
    if st is None:
        raise ImportError("Streamlit is required for the review UI")

    st.set_page_config(layout="wide")
    st.title("PDFResolve: Document Upload")

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        if "processed_file" not in st.session_state or st.session_state.processed_file != uploaded_file.name:
            st.session_state.processed_file = uploaded_file.name
            st.session_state.record = None
            st.session_state.document = None

            temp_dir = Path("./temp_uploads")
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / uploaded_file.name
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner(f"Processing {uploaded_file.name}..."):
                try:
                    pipeline = Pipeline(use_mock_llm=False)
                    doc = Document(temp_path)
                    st.session_state.document = doc
                    record = pipeline.run(doc)
                    st.session_state.record = record
                    st.success("Processing complete!")
                except Exception as e:
                    st.error(f"An error occurred during processing: {e}")

    if "record" in st.session_state and st.session_state.record and st.session_state.document:
        st.divider()
        review_ui(st.session_state.record, st.session_state.document)
    else:
        st.info("Please upload a PDF to begin processing.")


if __name__ == "__main__":
    main_app()
