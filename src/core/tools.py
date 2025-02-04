
from typing import List, Dict, Optional, Deque, Literal
from collections import deque
from langchain.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool
import psycopg
import json
from pydantic import BaseModel, EmailStr
from datetime import datetime
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import asyncio

# Import OpenAIClient
from src.core.openai_client import OpenAIClient


class OrderLookupInput(BaseModel):
    """Input for order lookup"""
    email: EmailStr


class OrderCancelInput(BaseModel):
    """Input for order cancellation"""
    email: EmailStr
    order_id: str


class IntentResponse(BaseModel):
    """Response model for intent classification"""
    intent: Literal["CHECK_ORDERS", "CANCEL_ORDER", "FAQ", "CHAT"]
    confidence: float
    email: Optional[str] = None
    order_id: Optional[str] = None


def get_db_connection():
    """Create database connection"""
    return psycopg.connect("postgresql://postgres:postgres@localhost:5432/postgres")


def get_customer_orders(email: str) -> List[Dict]:
    """Get orders for a given email"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        order_id,
                        order_detail,
                        total_price,
                        status,
                        created_at
                    FROM orders
                    WHERE customer_email = %s
                    ORDER BY created_at DESC
                    """,
                    (email,),
                )

                results = []
                for row in cur.fetchall():
                    order_detail = row[1]
                    if isinstance(order_detail, str):
                        order_detail = json.loads(order_detail)

                    results.append(
                        {
                            "order_id": row[0],
                            "order_detail": order_detail,
                            "total_price": str(float(row[2])),
                            "status": row[3],
                            "created_at": row[4].isoformat(),
                        }
                    )
                return results
    except Exception as e:
        print(f"Database error: {str(e)}")
        return []


def cancel_order(input_data: OrderCancelInput) -> Dict:
    """Cancel an order if it's in pending status"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First check if order exists and is cancellable
                cur.execute(
                    """
                    SELECT status
                    FROM orders
                    WHERE customer_email = %s AND order_id = %s
                    """,
                    (input_data.email, input_data.order_id),
                )

                result = cur.fetchone()
                if not result:
                    return {
                        "success": False,
                        "message": "Order not found. Please verify your order ID and email."
                    }

                status = result[0]
                if status.lower() != "pending":
                    return {
                        "success": False,
                        "message": f"Cannot cancel order with status: {status}. Only pending orders can be cancelled."
                    }

                # Update order status to cancelled
                cur.execute(
                    """
                    UPDATE orders
                    SET status = 'cancelled',
                        updated_at = %s
                    WHERE customer_email = %s AND order_id = %s
                    RETURNING order_id
                    """,
                    (datetime.now(), input_data.email, input_data.order_id),
                )

                conn.commit()
                return {
                    "success": True,
                    "message": f"Order {input_data.order_id} has been cancelled successfully."
                }

    except Exception as e:
        print(f"Database error: {str(e)}")
        return {
            "success": False,
            "message": "An error occurred while cancelling the order. Please try again."
        }


class ChatMessage:
    """Class to represent a chat message"""
    def __init__(self, role: str, content: str, timestamp: datetime = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


class ConversationMemory:
    """Class to manage conversation history"""
    def __init__(self, max_messages: int = 5):
        self.messages: Deque[ChatMessage] = deque(maxlen=max_messages)
        self.max_messages = max_messages

    def add_message(self, role: str, content: str):
        """Add a new message to the history"""
        message = ChatMessage(role, content)
        self.messages.append(message)

    def get_history(self, as_dict: bool = False) -> List:
        """Get conversation history"""
        if as_dict:
            return [msg.to_dict() for msg in self.messages]
        return list(self.messages)

    def get_context_string(self) -> str:
        """Get conversation history as a formatted string"""
        return json.dumps([msg.to_dict() for msg in self.messages])

    def clear(self):
        """Clear conversation history"""
        self.messages.clear()

from dotenv import load_dotenv
import os
load_dotenv()  # Tải biến môi trường từ file .env
api_key = os.getenv("OPENAI_API_KEY")

class OrderQuerySystem:
    def __init__(self, api_key: str = os.getenv("OPENAI_API_KEY"), openai_model_id: str = "gpt-4o-mini"):
        # Initialize OpenAIClient instead of ChatBedrock
        self.llm = OpenAIClient(
            api_key=api_key,
            model_id=openai_model_id,
        )

        # Initialize memory
        self.memory = ConversationMemory(max_messages=3)

        # Create tools
        self._setup_tools()
        # Create chains
        self._setup_chains()

    def _setup_tools(self):
        """Initialize all tools"""
        self.tools = [
            StructuredTool.from_function(
                func=get_customer_orders,
                name="lookup_orders",
                description="Look up orders for a customer email",
            ),
            StructuredTool.from_function(
                func=cancel_order,
                name="cancel_order",
                description="Cancel a pending order for a customer",
            ),
        ]

    def _setup_chains(self):
        """Initialize all conversation chains"""
        self.chains = {
            "intent": self._create_intent_chain(),
            "email": self._create_email_chain(),
            "order_id": self._create_order_id_chain(),
            "response": self._create_response_chain(),
            "conversation": self._create_conversation_chain(),
            "response_formatter": self._create_response_formatter_chain(),
            "chat": self._create_chat_chain()
        }


    def _create_intent_chain(self):
        """Create chain for intent classification"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an intent classifier for a Gundam store assistant.
            Analyze the user's message and determine their intent.

            Consider the conversation history for context:
            {history}

            Classify the intent into one of these categories:
            1. CHECK_ORDERS: User wants to view their order history or status
            2. CANCEL_ORDER: User wants to cancel an order
            3. FAQ: General questions about products, policies, etc.
            4. CHAT: General conversation or Gundam-related discussion

            Also extract email and order ID if present.

            Respond in JSON format with these exact fields:
            {{
                "intent": "CHECK_ORDERS" | "CANCEL_ORDER" | "FAQ" | "CHAT",
                "confidence": <float between 0 and 1>,
                "email": "<email if found, null if not>",
                "order_id": "<order id if found, null if not>"
            }}

            Examples:
            - "I want to cancel order #123" -> {{"intent": "CANCEL_ORDER", "confidence": 0.95, "email": null, "order_id": "123"}}
            - "Show my orders for test@email.com" -> {{"intent": "CHECK_ORDERS", "confidence": 0.9, "email": "test@email.com", "order_id": null}}
            - "What's your return policy?" -> {{"intent": "FAQ", "confidence": 0.8, "email": null, "order_id": null}}
            - "What do you think about the RX-78-2?" -> {{"intent": "CHAT", "confidence": 0.85, "email": null, "order_id": null}}
            """),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser()

    def _create_email_chain(self):
        """Create chain for email extraction"""
        return ChatPromptTemplate.from_messages([
            ("system", """Extract an email address from the message if present.
            Consider the conversation history for context:
            {history}

            If you find an email, respond with just the email address.
            If no email is found, respond with 'None'.
            Following the language of the message, respond in the same language."""),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser() # Added StrOutputParser

    def _create_order_id_chain(self):
        """Create chain for order ID extraction"""
        return ChatPromptTemplate.from_messages([
            ("system", """Extract the order ID from the message if present.
            Consider the conversation history for context:
            {history}

            Look for patterns like:
            - Order numbers (e.g., ORD-123, #123)
            - Direct mentions of order IDs
            - References to specific orders

            If found, return just the order ID.
            If not found, return 'None'.
            Following the language of the message, respond in the same language."""),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser() # Added StrOutputParser

    def _create_response_chain(self):
        """Create chain for formatting order lookup responses"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a helpful Gundam store assistant.
            Format the order information in a clear, organized manner.
            Include:
            - Order ID
            - Status
            - Total price
            - Key items
            - Order date

            Consider the conversation history for context:
            {history}

            Be concise but friendly.
            Following the language of the message, respond in the same language."""),
            ("human", "Here are the orders: {orders}")
        ]) | self.llm | StrOutputParser() # Added StrOutputParser

    def _create_conversation_chain(self):
        """Create chain for general conversation"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a helpful Gundam store assistant.
            Consider the conversation history for context:
            {history}

            - If asking for email, be polite and clear
            - If user seems confused, explain how you can help
            - Keep responses friendly but professional
            - Focus on order-related queries
            Following the language of the message, respond in the same language."""),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser() # Added StrOutputParser

    def _create_chain_with_streaming(self, prompt):
        """Create a chain that supports streaming"""
        return (
            {"message": RunnablePassthrough(), "history": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def _create_response_formatter_chain(self):
        """Create chain for formatting responses with streaming"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful Gundam store assistant.
            Format the given message in a natural, conversational way.
            Keep the same meaning but make it sound more friendly and natural.

            Consider the conversation history for context:
            {history}

            Important:
            - Maintain the same language as the user's query
            - Keep the key information intact
            - Be polite and professional
            - Use appropriate cultural context
            """),
            ("human", "Please format this message: {message}")
        ])
        return self._create_chain_with_streaming(prompt)

    def _create_chat_chain(self):
        """Create chain for general chatting"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are a friendly Gundam store assistant who loves to chat about Gundam.
            Consider the conversation history for context:
            {history}

            Guidelines for chatting:
            - Be friendly and enthusiastic about Gundam
            - Share interesting facts about Gundam models when relevant
            - Stay in character as a Gundam store assistant
            - If the conversation moves towards orders, guide them to the order-related features
            - Keep responses concise but engaging
            - Match the user's language and tone
            - You can discuss:
              * Different Gundam series and models
              * Basic Gundam lore and history
              * Gundam building tips
              * Popular Gundam models
              * General Gundam-related topics

            Remember:
            - Keep the conversation Gundam-focused
            - Be helpful but maintain professional boundaries
            - If unsure, guide back to store-related topics
            - Following the language of the message, respond in the same language.
            """),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser() # Added StrOutputParser

    async def _format_response_stream(self, message: str, history: str):
        """Format response using LLM with streaming"""
        try:
            # OpenAI client does not natively support streaming in this setup.
            # We will just invoke and return the full response for now.
            response = self.chains["response_formatter"].invoke({
                "message": message,
                "history": history
            })
            yield response

        except Exception as e:
            print(f"Error formatting response: {str(e)}")
            yield message

    def _format_response(self, message: str, history: str) -> str:
        """Format response using LLM"""
        try:
            response = self.chains["response_formatter"].invoke({
                "message": message,
                "history": history
            })
            return response
        except Exception as e:
            print(f"Error formatting response: {str(e)}")
            return message

    async def process_query_stream(self, user_input: str):
        """Process user query with streaming response"""
        try:
            # Add user message to memory
            self.memory.add_message("user", user_input)
            history = self.memory.get_context_string()

            # Determine intent
            intent_result = json.loads(self.chains["intent"].invoke({
                "input": user_input,
                "history": history
            }))

            # Route to appropriate handler based on intent
            if intent_result["intent"] == "CANCEL_ORDER":
                response = await self._handle_cancellation(user_input, history, intent_result)
            elif intent_result["intent"] == "CHECK_ORDERS":
                response = self._handle_order_lookup(user_input, history, intent_result)
            elif intent_result["intent"] == "CHAT":
                # Handle chat intent
                response = self.chains["chat"].invoke({
                    "input": user_input,
                    "history": history
                })
            else:
                response = "I understand you have a general question. However, I'm currently configured to help with order-related queries and chat about Gundam. Feel free to ask about orders or discuss Gundam with me!"

            # Stream formatted response
            async for chunk in self._format_response_stream(response, history):
                yield chunk

            # Save complete response to memory
            self.memory.add_message("assistant", response)

        except Exception as e:
            print(f"Error in process_query: {str(e)}")
            error_msg = "I encountered an error processing your request. Please try again."
            async for chunk in self._format_response_stream(error_msg, history):
                yield chunk

    async def _handle_cancellation(self, user_input: str, history: str, intent_result: Dict) -> str:
        """Handle order cancellation flow"""
        email = intent_result.get("email")
        order_id = intent_result.get("order_id")

        # If we don't have email, ask for it
        if not email:
            email_result = self.chains["email"].invoke({
                "input": user_input,
                "history": history
            })
            if email_result.lower() != 'none':
                email = email_result

        # If we don't have order ID, ask for it
        if not order_id:
            order_id_result = self.chains["order_id"].invoke({
                "input": user_input,
                "history": history
            })
            if order_id_result.lower() != 'none':
                order_id = order_id_result

        # If we have both pieces of information, proceed with cancellation
        if email and order_id:
            try:
                # Create the input data dictionary
                input_data = {
                    "email": email,
                    "order_id": order_id
                }
                result = cancel_order(OrderCancelInput(**input_data))
                return result["message"]
            except Exception as e:
                print(f"Cancellation error: {str(e)}")
                return "I encountered an error while trying to cancel the order. Please try again."
        else:
            missing = []
            if not email:
                missing.append("email address")
            if not order_id:
                missing.append("order ID")
            return f"To cancel your order, I'll need your {' and '.join(missing)}. Could you please provide {'them' if len(missing) > 1 else 'it'}?"

    def _handle_order_lookup(self, user_input: str, history: str, intent_result: Dict) -> str:
        """Handle order lookup flow"""
        email = intent_result.get("email")

        if not email:
            email_result = self.chains["email"].invoke({
                "input": user_input,
                "history": history
            })
            if email_result.lower() != 'none':
                email = email_result

        if not email:
            return "I'll help you check your orders. Could you please provide your email address?"

        try:
            orders = self.tools[0].invoke(email)
            if not orders:
                return f"I couldn't find any orders associated with {email}. Please verify your email address."

            base_response = self.chains["response"].invoke({
                "orders": json.dumps(orders),
                "history": history
            })
            return base_response
        except Exception as e:
            print(f"Order lookup error: {str(e)}")
            return "I encountered an error while looking up your orders. Please try again."