import os
import sys
from pathlib import Path
import streamlit as st

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from ui.bot_ui import ChatBot


def main():
    """Main entry point for the Gundam Store Chatbot"""
    try:
        # Set page config
        st.set_page_config(
            page_title="Gundam Store Assistant",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        # Initialize chatbot
        bot = ChatBot()

        # Display sidebar
        bot.display_sidebar()

        # Display chat interface
        bot.display_chat()

    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        if st.button("Restart Application"):
            st.session_state.clear()
            st.rerun()


if __name__ == "__main__":
    main()
