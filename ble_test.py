"""
BLE Mesh Network Test Script

This script demonstrates how to set up two agents that can communicate
over BLE between two different Windows machines.

Modes:
1. Manual mode: Type messages to send to other agents
2. Auto mode: Agents communicate automatically with each other
"""
import asyncio
import sys
import random
import argparse
import json
from datetime import datetime
from typing import List, Dict, Optional
from simple_ble_mesh import SimpleBLEMesh as BLEMesh

# Sample conversation topics for auto mode
CONVERSATION_TOPICS = [
    "What's your favorite color?",
    "How's the weather over there?",
    "What do you think about AI?",
    "Have you seen any good movies lately?",
    "What's your favorite food?",
    "How's your day going?",
    "What's your favorite programming language?",
    "Do you like to travel?"
]

class AutoChat:
    """Handles automated chat behavior for agents."""
    
    def __init__(self, agent_id: str, mesh: BLEMesh):
        self.agent_id = agent_id
        self.mesh = mesh
        self.peers: List[str] = []
        self.is_active = False
        self.conversation_history: Dict[str, List[Dict]] = {}
    
    async def start(self):
        """Start the auto-chat mode."""
        self.is_active = True
        asyncio.create_task(self._auto_chat_loop())
    
    async def stop(self):
        """Stop the auto-chat mode."""
        self.is_active = False
    
    def add_peer(self, peer_id: str):
        """Add a peer to the list of known peers."""
        if peer_id != self.agent_id and peer_id not in self.peers:
            self.peers.append(peer_id)
            self.conversation_history[peer_id] = []
            print(f"[AUTO] Added peer: {peer_id}")
    
    async def _auto_chat_loop(self):
        """Main loop for automated chatting."""
        while self.is_active:
            if self.peers:
                # Select a random peer
                peer = random.choice(self.peers)
                
                # Generate a message
                if not self.conversation_history[peer]:
                    # First message to this peer
                    message = f"Hello! I'm {self.agent_id}. {random.choice(CONTEXT_PROMPTS)}"
                else:
                    # Continue the conversation
                    last_msg = self.conversation_history[peer][-1]
                    if last_msg['sender'] == self.agent_id:
                        # Wait for response
                        await asyncio.sleep(random.uniform(2, 5))
                        continue
                    else:
                        # Respond to the last message
                        message = self._generate_response(peer)
                
                # Send the message
                await self.mesh.send_message(peer, {
                    "type": "chat",
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add to conversation history
                self._add_to_history(peer, self.agent_id, message)
                
                print(f"[AUTO] Sent to {peer}: {message}")
                
            # Wait before next message
            await asyncio.sleep(random.uniform(5, 10))
    
    def _generate_response(self, peer_id: str) -> str:
        """Generate a response based on conversation history."""
        history = self.conversation_history.get(peer_id, [])
        
        # Simple response logic - in a real app, you'd use an AI model here
        last_message = history[-1]['content'] if history else ""
        
        responses = [
            f"That's interesting! Tell me more about that.",
            f"I see. What else is new with you?",
            f"Fascinating! I was just thinking about that too.",
            f"I understand. My thoughts exactly!",
            f"That's a great point. I've been wondering about that myself.",
            f"Really? I had no idea!"
        ]
        
        # If the last message was a question, try to answer it
        if '?' in last_message:
            if 'favorite' in last_message.lower():
                return f"My favorite is {random.choice(['pizza', 'sushi', 'pasta', 'salad'])}. What's yours?"
            elif 'how' in last_message.lower():
                return "I'm doing well, thanks for asking! How about you?"
            elif 'what' in last_message.lower():
                return f"I think it's {random.choice(['amazing', 'interesting', 'challenging', 'exciting'])}!"
        
        return random.choice(responses)
    
    def _add_to_history(self, peer_id: str, sender: str, message: str):
        """Add a message to the conversation history."""
        if peer_id not in self.conversation_history:
            self.conversation_history[peer_id] = []
        
        self.conversation_history[peer_id].append({
            'sender': sender,
            'content': message,
            'timestamp': datetime.now().isoformat()
        })

# Sample context prompts for initial messages
CONTEXT_PROMPTS = [
    "I'm excited to chat with you!",
    "How's your day going so far?",
    "I've been learning about BLE mesh networks. What about you?",
    "Do you come here often?",
    "What's new with you today?",
    "I'm testing out this BLE chat system. It's pretty cool!",
    "Have you worked with Bluetooth before?",
    "What do you think about wireless communication technologies?"
]

class BLETestAgent:
    """Agent for testing BLE communication with manual and auto modes."""
    
    def __init__(self, agent_id: str):
        """Initialize the test agent."""
        self.agent_id = agent_id
        self.mesh = BLEMesh(agent_id)
        self.auto_chat = AutoChat(agent_id, self.mesh)
        self.running = False
        self.auto_mode = False
        
    async def start(self):
        """Start the agent and BLE mesh."""
        print(f"[AGENT {self.agent_id}] Starting BLE mesh...")
        
        # Register message handler
        self.mesh.register_callback("chat", self._handle_chat_message)
        
        # Start the mesh network
        await self.mesh.start()
        self.running = True
        
        # Print instructions
        print(f"\n{'='*50}")
        print(f"AGENT {self.agent_id} - BLE Mesh Chat")
        print("="*50)
        print("\nAvailable Commands:")
        print("  Manual Mode:")
        print("    <recipient_id> <message>  Send a message")
        print("    Example: agent2 Hello from agent1")
        print("\n  Auto Mode:")
        print("    /auto on      Enable auto-chat mode")
        print("    /auto off     Disable auto-chat mode")
        print("\n  General:")
        print("    /peers        List discovered peers")
        print("    /exit         Exit the program")
        print("\nType your command and press Enter...\n")
        
        # Start the input loop
        asyncio.create_task(self._input_loop())
        
        # Keep the agent running
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the agent and clean up."""
        self.running = False
        await self.mesh.stop()
    
    async def _input_loop(self):
        """Handle user input in the background."""
        while self.running:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, f"[{self.agent_id}] > "
                )
                
                # Check for commands
                if user_input.lower() in ('exit', 'quit', '/exit'):
                    print("Shutting down...")
                    await self.stop()
                    return
                    
                elif user_input.lower() == '/peers':
                    print("\nDiscovered peers:")
                    for peer in self.auto_chat.peers:
                        print(f"  - {peer}")
                    print()
                    continue
                    
                elif user_input.lower() == '/auto on':
                    if not self.auto_mode:
                        self.auto_mode = True
                        await self.auto_chat.start()
                        print("Auto-chat mode enabled!")
                    else:
                        print("Auto-chat mode is already enabled")
                    continue
                    
                elif user_input.lower() == '/auto off':
                    if self.auto_mode:
                        self.auto_mode = False
                        await self.auto_chat.stop()
                        print("Auto-chat mode disabled")
                    else:
                        print("Auto-chat mode is already disabled")
                    continue
                
                # If in auto mode, only allow commands, not manual messages
                if self.auto_mode and not user_input.startswith('/'):
                    print("\n[!] Auto-chat mode is enabled. Type '/auto off' to send manual messages.\n")
                    continue
                
                # Handle manual message sending
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print("Invalid format. Use: <recipient_id> <message>")
                    continue
                    
                recipient_id, message = parts
                
                # Send the message
                await self.mesh.send_message(recipient_id, {
                    "type": "chat",
                    "content": message,
                    "timestamp": datetime.now().isoformat()
                })
                print(f"[SENT to {recipient_id}] {message}")
                
                # Add to conversation history
                self.auto_chat._add_to_history(recipient_id, self.agent_id, message)
                
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
    
    async def _handle_chat_message(self, sender_id: str, message: dict):
        """Handle incoming chat messages."""
        content = message.get("content", "")
        timestamp = message.get("timestamp", "")
        
        # Add to auto-chat's known peers
        self.auto_chat.add_peer(sender_id)
        
        # Add to conversation history
        self.auto_chat._add_to_history(sender_id, sender_id, content)
        
        # Format timestamp if available
        time_str = ""
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except (ValueError, TypeError):
                time_str = ""
        
        # Print the message
        print(f"\n{'='*50}")
        if time_str:
            print(f"[{time_str}] ", end="")
        print(f"[FROM {sender_id}] {content}")
        print("-" * 50)
        
        # If in auto mode, don't show the prompt (it will be shown after the auto-response)
        if not self.auto_mode:
            print(f"[{self.agent_id}] > ", end="", flush=True)

async def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="BLE Mesh Agent")
    parser.add_argument("agent_id", help="Unique ID for this agent (e.g., 'agent1' or 'agent2')")
    parser.add_argument("--auto", action="store_true", help="Enable auto-chat mode on startup")
    args = parser.parse_args()
    
    # Create and start the agent
    agent = BLETestAgent(args.agent_id)
    
    # Start in auto mode if requested
    if args.auto:
        await agent.auto_chat.start()
        agent.auto_mode = True
    
    try:
        await agent.start()
    except asyncio.CancelledError:
        pass
    finally:
        await agent.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
