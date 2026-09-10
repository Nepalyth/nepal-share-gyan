import sys
from pathlib import Path

import streamlit as st
from streamlit.web import cli as stcli


def main():
    st.title("Share Gyan")
    name = st.text_input("What's your name?")
    if name:
        st.write(f"Hello, {name}! Welcome to Share Gyan.")


def run():
    # Entry point for the `app` console script: launches this file via `streamlit run`.
    sys.argv = ["streamlit", "run", str(Path(__file__).resolve())]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
