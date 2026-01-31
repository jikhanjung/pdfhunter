"""Launcher script for PDFResolve Streamlit UI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pdfresolve.ui.review_ui import main_app

main_app()
