import sys
from pathlib import Path

# Make the src/ layout importable without installing the package (Streamlit Community Cloud).
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from share_gyan.main import main  # noqa: E402

main()
