import streamlit as st
from src.core.tools import OrderQuerySystem
from src.core.pgvector import PGVector
from src.core.embedding import EmbeddingClient
import json
from typing import Dict, List, AsyncGenerator
import asyncio
from contextlib import contextmanager
from src.lang.vi import UI_MESSAGES

from dotenv import load_dotenv
import os

load_dotenv()  # Tải biến môi trường từ file .env
api_key = os.getenv("OPENAI_API_KEY")

class ChatBot:
    def __init__(self):
        # Initialize resources
        self._initialize_resources()

        # Initialize session state
        if "messages" not in st.session_state:
            st.session_state.messages = []

    def _initialize_resources(self):
        """Initialize or get cached resources"""
        if "resources" not in st.session_state:
            st.session_state.resources = {
                "order_system": OrderQuerySystem(),
                "vector_db": PGVector(),
                "embedding_client": EmbeddingClient(api_key=api_key),
            }

        self.order_system = st.session_state.resources["order_system"]
        self.vector_db = st.session_state.resources["vector_db"]
        self.embedding_client = st.session_state.resources["embedding_client"]

    def get_faq_response(self, query: str) -> Dict:
        """Get response from FAQ system"""
        try:
            # Get embedding for query
            query_embeddings = self.embedding_client.embed_documents(
                texts=[query], input_type="search_query"
            )

            if not query_embeddings:
                return {"found": False}

            # Search similar questions
            results = self.vector_db.similarity_search(
                query_embedding=query_embeddings[0], k=3, similarity_threshold=0.7
            )

            if results:
                return {
                    "found": True,
                    "answer": results[0]["answer"],
                    "similarity": results[0]["similarity"],
                }
        except Exception as e:
            print(UI_MESSAGES["faq_error"].format(str(e)))
        return {"found": False}

    async def get_streaming_response(self, user_input: str) -> AsyncGenerator[str, None]:
        """Get streaming response from the order system"""
        try:
            # First check FAQ
            faq_response = self.get_faq_response(user_input)
            #
            if faq_response["found"] and faq_response["similarity"] > 0.7:
                yield faq_response["answer"]
                return

            # Use order system for streaming response
            async for chunk in self.order_system.process_query_stream(user_input):
                yield chunk

        except Exception as e:
            print(f"Response error: {str(e)}")
            yield UI_MESSAGES["response_error"]

    def display_chat(self):
        """Display chat interface"""
        # Chat header
        st.title(UI_MESSAGES["chat_title"])
        st.write(UI_MESSAGES["chat_subtitle"])

        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input(UI_MESSAGES["chat_input_placeholder"]):
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Display assistant response with streaming
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                # Create and run async response generator
                async def process_response():
                    nonlocal full_response
                    async for chunk in self.get_streaming_response(prompt):
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                
                # Run the async function
                asyncio.run(process_response())
                
                # Update final response
                message_placeholder.markdown(full_response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )

    def display_sidebar(self):
        """Display sidebar with additional information"""
        with st.sidebar:
            st.title(UI_MESSAGES["sidebar_title"])
            with st.expander(UI_MESSAGES["how_to_use_title"], expanded=True):
                st.markdown(UI_MESSAGES["how_to_use_content"])

            with st.expander(UI_MESSAGES["example_questions_title"], expanded=True):
                st.markdown(UI_MESSAGES["example_questions_content"])

            # Clear chat button
            if st.button(UI_MESSAGES["clear_chat"]):
                st.session_state.messages = []
                st.rerun()

def main():
    try:
        # Set page config
        st.set_page_config(
            page_title=UI_MESSAGES["page_title"],
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
        st.error(UI_MESSAGES["app_error"].format(str(e)))
        if st.button(UI_MESSAGES["restart_app"]):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
