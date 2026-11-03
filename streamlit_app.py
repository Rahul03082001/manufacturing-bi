"""Root entry point for Streamlit Community Cloud; reuse the tested dashboard."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).parent / 'dashboard' / 'app.py'), run_name='__main__')
