"""
AI Agent implementation for the Bluetooth Mesh Network simulation.

This module defines the Agent class which can send and receive messages
and generate responses using a HuggingFace language model.
"""
import asyncio
from typing import Dict, Any, Optional

# Import the transformers library for AI capabilities
try:
    from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
    from transformers.utils import logging
    logging.set_verbosity_error()  # Reduce verbosity
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("Warning: transformers library not found. AI features will be disabled.")
    TRANSFORMERS_AVAILABLE = False

class Agent:
    """
    An AI agent that can communicate over the mesh network.
    
    Each agent has a unique ID and can send/receive messages,
    generating responses using a language model.
    """
    
    def __init__(self, agent_id: str, mesh_network: Any, model_name: str = "distilgpt2"):
        """
        Initialize a new agent.
        
        Args:
            agent_id: Unique identifier for this agent
            mesh_network: Reference to the MeshNetwork instance
            model_name: Name of the HuggingFace model to use
        """
        self.agent_id = agent_id
        self.mesh = mesh_network
        self.model_name = model_name
        self.conversation_history: Dict[str, list] = {}
        self.model = None
        self.tokenizer = None
        
        # Initialize the AI model
        self._init_model()
        
        # Register with the mesh network
        asyncio.create_task(
            self.mesh.register_agent(agent_id, self._handle_message)
        )
    
    def _init_model(self) -> None:
        """Initialize the language model and tokenizer."""
        if not TRANSFORMERS_AVAILABLE:
            print(f"[AGENT {self.agent_id}] Running in no-AI mode (transformers not available)")
            return
            
        try:
            print(f"[AGENT {self.agent_id}] Loading model '{self.model_name}'...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                pad_token_id=self.tokenizer.eos_token_id
            )
            self.generator = pipeline(
                'text-generation',
                model=self.model,
                tokenizer=self.tokenizer,
                device=-1  # Use CPU
            )
            print(f"[AGENT {self.agent_id}] Model loaded successfully")
        except Exception as e:
            print(f"[AGENT {self.agent_id}] Error loading model: {e}")
            print("[AGENT {self.agent_id}] Falling back to echo mode")
            self.model = None
    
    async def _handle_message(self, sender: str, message: Dict[str, Any]) -> None:
        """
        Handle an incoming message.
        
        Args:
            sender: ID of the sending agent
            message: The message content
        """
        print(f"[AGENT {self.agent_id}] Received from {sender}: {message.get('content', '')}")
        
        # Update conversation history
        if sender not in self.conversation_history:
            self.conversation_history[sender] = []
        self.conversation_history[sender].append(("them", message.get('content', '')))
        
        # Generate a response
        response = await self._generate_response(sender, message.get('content', ''))
        
        # Send the response back
        await self.send_message(sender, response)
    
    async def _generate_response(self, sender: str, message: str) -> str:
        """
        Generate a response to a message about Toronto's weather.
        
        Args:
            sender: ID of the sender
            message: The message to respond to
            
        Returns:
            str: The generated response about Toronto's weather
        """
        if not self.model or not TRANSFORMERS_AVAILABLE:
            # Fallback response if AI is not available
            return f"I can't access the weather model right now, but I hope the weather in Toronto is nice today!"
        
        try:
            # Create a more focused prompt about Toronto's weather
            prompt = (
                f"Conversation about Toronto's weather. "
                f"{self.agent_id} is talking to {sender} about the weather in Toronto.\n\n"
                f"{sender}: {message}\n"
                f"{self.agent_id}:"
            )
            
            # Generate response using the model with more focused parameters
            response = self.generator(
                prompt,
                max_length=150,
                num_return_sequences=1,
                temperature=0.8,  # Slightly higher for more creative responses
                top_k=40,
                top_p=0.9,
                do_sample=True,
                pad_token_id=50256  # Ensure we have an end token
            )
            
            # Extract and clean the response
            full_text = response[0]['generated_text']
            response_text = full_text[len(prompt):].strip()
            
            # Clean up the response
            response_text = response_text.split('\n')[0].strip()
            
            # Ensure we have a valid response
            if not response_text or len(response_text) < 2:
                response_text = "The weather in Toronto is quite nice today!"
                
            # Add to conversation history
            if sender not in self.conversation_history:
                self.conversation_history[sender] = []
            self.conversation_history[sender].append(("me", response_text))
            
            # Ensure the response isn't too long
            if len(response_text) > 200:
                response_text = response_text[:197] + "..."
                
            return response_text
            
        except Exception as e:
            print(f"[AGENT {self.agent_id}] Error generating response: {e}")
            # Fallback responses about Toronto's weather
            fallbacks = [
                "I heard Toronto is experiencing seasonal temperatures today.",
                "The weather in Toronto is always changing, isn't it?",
                "I don't have the latest forecast, but I hope Toronto's weather is pleasant!",
                "It's a beautiful day in Toronto, don't you think?"
            ]
            import random
            return random.choice(fallbacks)
    
    async def send_message(self, receiver: str, content: str) -> None:
        """
        Send a message to another agent.
        
        Args:
            receiver: ID of the receiving agent
            content: The message content
        """
        print(f"[AGENT {self.agent_id}] Sending to {receiver}: {content}")
        
        message = {
            "content": content,
            "type": "chat",
            "timestamp": asyncio.get_event_loop().time()
        }
        
        print(f"[AGENT {self.agent_id}] Sending to {receiver}: {content}")
        
        try:
            await self.mesh.send(self.agent_id, receiver, message)
        except Exception as e:
            print(f"[AGENT {self.agent_id}] Error sending message: {e}")
    
    async def start_conversation(self, receiver: str, content: str) -> None:
        """
        Start a new conversation with another agent.
        
        Args:
            receiver: ID of the agent to start a conversation with
            content: The initial message content
        """
        print(f"[AGENT {self.agent_id}] Starting conversation with {receiver}")
        await self.send_message(receiver, content)
    
    async def close(self) -> None:
        """Clean up resources and unregister from the network."""
        await self.mesh.unregister_agent(self.agent_id)
        if hasattr(self, 'model'):
            del self.model
        if hasattr(self, 'tokenizer'):
            del self.tokenizer
