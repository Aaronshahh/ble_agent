"""
Simulated Bluetooth Mesh Network for AI Agents

This module implements a virtual mesh network where AI agents can communicate
with simulated latency and basic error handling.
"""
import asyncio
import json
import random
from typing import Dict, Callable, Any, Optional

class MeshNetwork:
    """
    A simulated mesh network for message passing between agents.
    
    This class handles agent registration and message routing with simulated latency.
    """
    
    def __init__(self):
        """Initialize a new mesh network."""
        self.agents: Dict[str, Callable[[str, dict], None]] = {}
        self.message_counter = 0
    
    async def register_agent(self, agent_id: str, callback: Callable[[str, dict], None]) -> None:
        """
        Register an agent with the mesh network.
        
        Args:
            agent_id: Unique identifier for the agent
            callback: Function to call when agent receives a message
            
        Raises:
            ValueError: If agent_id is already registered
        """
        if agent_id in self.agents:
            raise ValueError(f"Agent ID '{agent_id}' is already registered")
        self.agents[agent_id] = callback
        print(f"[MESH] Agent '{agent_id}' joined the network")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the network."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            print(f"[MESH] Agent '{agent_id}' left the network")
    
    async def send(self, sender: str, receiver: str, message: dict) -> None:
        """
        Send a message from one agent to another.
        
        Args:
            sender: ID of the sending agent
            receiver: ID of the receiving agent
            message: Dictionary containing message data
            
        Raises:
            KeyError: If receiver is not found in the network
        """
        if receiver not in self.agents:
            raise KeyError(f"Receiver '{receiver}' not found in the network")
        
        # Add metadata to message
        message_id = self.message_counter
        self.message_counter += 1
        
        # Simulate network latency (100-500ms)
        latency = random.uniform(0.1, 0.5)
        
        # Create a task to handle the message with simulated latency
        asyncio.create_task(self._deliver_message(sender, receiver, message, message_id, latency))
    
    async def _deliver_message(self, sender: str, receiver: str, message: dict, 
                             message_id: int, delay: float) -> None:
        """
        Deliver a message after a simulated network delay.
        
        This is an internal method and should not be called directly.
        """
        try:
            # Wait for the simulated network delay
            await asyncio.sleep(delay)
            
            # Get the receiver's callback
            callback = self.agents.get(receiver)
            if callback:
                # Create a copy of the message to prevent modification
                message_copy = message.copy()
                message_copy['message_id'] = message_id
                message_copy['timestamp'] = asyncio.get_event_loop().time()
                
                # Call the receiver's callback
                await callback(sender, message_copy)
                print(f"[MESH] Message {message_id} delivered from '{sender}' to '{receiver}' "
                      f"(latency: {delay*1000:.0f}ms)")
            
        except Exception as e:
            print(f"[MESH] Error delivering message {message_id}: {e}")
    
    def get_agent_count(self) -> int:
        """Return the number of agents currently in the network."""
        return len(self.agents)
