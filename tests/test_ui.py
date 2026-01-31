"""Tests for the Streamlit UI."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os

# Mock streamlit before it's imported by the module under test
from unittest.mock import MagicMock
import sys
sys.modules['streamlit'] = MagicMock()

from pdfresolve.ui.review_ui import main_app
from pdfresolve.core.pipeline import Pipeline
from pdfresolve.models.bibliography import BibliographyRecord

class TestReviewUI:

    @patch("pdfresolve.ui.review_ui.Pipeline")
    @patch("pdfresolve.ui.review_ui.Document")
    def test_main_app_file_processing(self, mock_document, mock_pipeline):
        """
        Tests that the main_app function correctly processes an uploaded file.
        """
        # 1. Setup
        # Mock the streamlit file uploader to return a dummy file
        st = sys.modules['streamlit']
        mock_file = MagicMock()
        mock_file.name = "test.pdf"
        mock_file.getbuffer.return_value = b"dummy pdf content"
        st.file_uploader.return_value = mock_file
        
        # Mock the session state to allow attribute access
        st.session_state = MagicMock()
        st.session_state.__contains__.return_value = False # Make it behave like a new session

        # Mock the pipeline to return a specific record
        mock_record = BibliographyRecord(id="123", type="article")
        mock_pipeline.return_value.run.return_value = mock_record

        # 2. Run the app function
        # We need a temporary directory for the file to be "uploaded" to
        with patch("pathlib.Path.mkdir"), patch("builtins.open"):
             main_app()

        # 3. Assertions
        # Check that a document was created with the correct path
        temp_path = Path("./temp_uploads") / "test.pdf"
        mock_document.assert_called_once_with(temp_path)
        
        # Check that the pipeline was run
        mock_pipeline.return_value.run.assert_called_once()
        
        # Check that the result was stored in the session state
        assert st.session_state.record == mock_record
        
        # Check that the success message was called
        st.success.assert_called_with("Processing complete!")
