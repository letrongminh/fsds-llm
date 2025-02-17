from typing import List, Dict, Optional, Deque, Literal
from collections import deque
from langchain.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool
import psycopg
import json
from pydantic import BaseModel, EmailStr
from src.lang.prompt_vi import SYSTEM_PROMPTS, ERROR_MESSAGES
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

class ConversationState:
    """Class to manage conversation state"""
    def __init__(self):
        self.active_intent = None
        self.collected_data = {}
    
    def start_flow(self, intent: str):
        """Start a new conversation flow"""
        self.active_intent = intent
        self.collected_data = {}
    
    def add_data(self, key: str, value: str):
        """Add data to current flow"""
        self.collected_data[key] = value
    
    def get_data(self, key: str) -> Optional[str]:
        """Get data from current flow"""
        return self.collected_data.get(key)
    
    def clear(self):
        """Clear current flow"""
        self.active_intent = None
        self.collected_data = {}
    
    def is_cancel_flow(self) -> bool:
        """Check if current flow is order cancellation"""
        return self.active_intent == "CANCEL_ORDER"

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
                        "message": ERROR_MESSAGES["cancel_not_found"]
                    }

                status = result[0]
                if status.lower() != "pending":
                    return {
                        "success": False,
                        "message": ERROR_MESSAGES["cancel_invalid_status"].format(status)
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
                    "message": ERROR_MESSAGES["cancel_success"].format(input_data.order_id)
                }

    except Exception as e:
        print(f"Database error: {str(e)}")
        return {
            "success": False,
            "message": ERROR_MESSAGES["cancel_error"]
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

        # Initialize memory and state
        self.memory = ConversationMemory(max_messages=3)
        self.state = ConversationState()

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
            ("system", SYSTEM_PROMPTS["intent_classifier"]),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser()

    def _create_email_chain(self):
        """Create chain for email extraction"""
        return ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPTS["email_extractor"]),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser()

    def _create_order_id_chain(self):
        """Create chain for order ID extraction"""
        return ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPTS["order_id_extractor"]),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser()

    def _create_response_chain(self):
        """Create chain for formatting order lookup responses"""
        return ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPTS["order_response_formatter"]),
            ("human", "Here are the orders: {orders}")
        ]) | self.llm | StrOutputParser()

    def _create_conversation_chain(self):
        """Create chain for general conversation"""
        return ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPTS["conversation"]),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser()

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
            ("system", SYSTEM_PROMPTS["response_formatter"]),
            ("human", "Please format this message: {message}")
        ])
        return self._create_chain_with_streaming(prompt)

    def _create_chat_chain(self):
        """Create chain for general chatting"""
        return ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPTS["chat"]),
            ("human", "{input}")
        ]) | self.llm | StrOutputParser()

    async def _format_response_stream(self, message: str, history: str):
        """Format response using LLM with streaming"""
        try:
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

            # Extract email if in cancel flow
            if self.state.is_cancel_flow():
                email_result = self.chains["email"].invoke({
                    "input": user_input,
                    "history": history
                })
                if email_result.lower() != 'none':
                    self.state.add_data("email", email_result)
                
                # Extract order ID if we have email
                if self.state.get_data("email"):
                    order_id_result = self.chains["order_id"].invoke({
                        "input": user_input,
                        "history": history
                    })
                    if order_id_result.lower() != 'none':
                        self.state.add_data("order_id", order_id_result)

            # Determine intent if not in a flow
            if not self.state.active_intent:
                intent_result = json.loads(self.chains["intent"].invoke({
                    "input": user_input,
                    "history": history
                }))

                if intent_result["intent"] == "CANCEL_ORDER":
                    self.state.start_flow("CANCEL_ORDER")
                    if intent_result.get("email"):
                        self.state.add_data("email", intent_result["email"])
                    if intent_result.get("order_id"):
                        self.state.add_data("order_id", intent_result["order_id"])

            # Route to appropriate handler
            if self.state.is_cancel_flow():
                response = await self._handle_cancellation()
            else:
                response = await self._handle_other_queries(user_input, history)

            # Stream formatted response
            async for chunk in self._format_response_stream(response, history):
                yield chunk

            # Save complete response to memory
            self.memory.add_message("assistant", response)

        except Exception as e:
            print(f"Error in process_query: {str(e)}")
            error_msg = ERROR_MESSAGES["processing_error"]
            async for chunk in self._format_response_stream(error_msg, history):
                yield chunk

    async def _handle_cancellation(self) -> str:
        """Handle order cancellation flow"""
        email = self.state.get_data("email")
        order_id = self.state.get_data("order_id")

        # If we have both pieces of information, proceed with cancellation
        if email and order_id:
            try:
                result = cancel_order(OrderCancelInput(email=email, order_id=order_id))
                self.state.clear()  # Clear state after successful cancellation
                return result["message"]
            except Exception as e:
                print(f"Cancellation error: {str(e)}")
                return ERROR_MESSAGES["cancel_error"]
        else:
            # Ask for missing information
            missing = []
            if not email:
                missing.append("email address")
            if not order_id:
                missing.append("order ID")
            items_needed = ' and '.join(missing)
            return ERROR_MESSAGES["missing_info"].format(items_needed, 'them' if len(missing) > 1 else 'it')

    async def _handle_other_queries(self, user_input: str, history: str) -> str:
        """Handle all other types of queries"""
        # Get intent
        intent_result = json.loads(self.chains["intent"].invoke({
            "input": user_input,
            "history": history
        }))

        if intent_result["intent"] == "CHECK_ORDERS":
            return self._handle_order_lookup(user_input, history, intent_result)
        elif intent_result["intent"] == "CHAT":
            return self.chains["chat"].invoke({
                "input": user_input,
                "history": history
            })
        else:
            return ERROR_MESSAGES["general_query"]

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
            return ERROR_MESSAGES["email_needed"]

        try:
            orders = self.tools[0].invoke(email)
            if not orders:
                return ERROR_MESSAGES["no_orders"].format(email)

            base_response = self.chains["response"].invoke({
                "orders": json.dumps(orders),
                "history": history
            })
            return base_response
        except Exception as e:
            print(f"Order lookup error: {str(e)}")
            return ERROR_MESSAGES["lookup_error"]
