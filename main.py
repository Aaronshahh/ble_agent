"""
BLE Agent - Main Application

This script demonstrates how to use the BLE communicator to create
agents that can communicate with each other over BLE.
"""
import asyncio
import argparse
import logging
import sys
import signal
from typing import Optional

from ble_communicator import BLECommunicator
from agent import Agent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class BLEChatApp:
    """Simple chat application using BLE for communication."""
    
    def __init__(self, agent_id: str):
        """Initialize the chat application."""
        self.agent_id = agent_id
        self.ble_communicator = BLECommunicator(agent_id)
        self.agent = Agent(agent_id, self.ble_communicator)
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Set up message handler
        self.agent.set_message_handler(self._handle_message)
        
        # Track connected peers
        self.connected_peers = set()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutting down...")
        asyncio.create_task(self.shutdown())
    
    async def _handle_message(self, sender: str, message: dict) -> None:
        """Handle incoming messages."""
        if 'content' in message:
            print(f"\n[{sender}]: {message['content']}")
            print("> ", end="", flush=True)
    
    async def start(self) -> None:
        """Start the BLE chat application."""
        logger.info(f"Starting BLE agent: {self.agent_id}")
        
        # Start the agent
        await self.agent.communicator.start(self._handle_message)
        
        # Start the command line interface
        await self._command_interface()
    
    async def _command_interface(self) -> None:
        """Run the command line interface."""
        print("\nBLE Chat - Commands:")
        print("  /help - Show this help")
        print("  /exit - Exit the application")
        print("  /list - List connected peers")
        print("  /msg <peer_id> <message> - Send a message to a peer")
        print("")
        
        while True:
            try:
                user_input = input("> ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() == '/exit':
                    await self.shutdown()
                    return
                    
                elif user_input.lower() == '/help':
                    print("\nAvailable commands:")
                    print("  /help - Show this help")
                    print("  /exit - Exit the application")
                    print("  /list - List connected peers")
                    print("  /msg <peer_id> <message> - Send a message to a peer")
                    print()
                    
                elif user_input.lower() == '/list':
                    if self.agent.communicator.connected:
                        print("\nConnected to:")
                        print(f"  - {self.agent.communicator.target_device.name}")
                    else:
                        print("\nNot connected to any peers.")
                    print()
                    
                elif user_input.lower().startswith('/msg '):
                    parts = user_input[5:].split(maxsplit=1)
                    if len(parts) < 2:
                        print("Usage: /msg <peer_id> <message>")
                        continue
                        
                    peer_id = parts[0]
                    message = parts[1]
                    
                    print(f"[You -> {peer_id}]: {message}")
                    await self.agent.send_message(peer_id, message)
                    
                else:
                    print("Unknown command. Type /help for available commands.")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in command interface: {e}")
    
    async def shutdown(self) -> None:
        """Shut down the application cleanly."""
        logger.info("Shutting down BLE agent...")
        await self.agent.close()
        # Exit the application
        asyncio.get_event_loop().stop()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='BLE Chat Application')
    parser.add_argument('agent_id', help='Unique ID for this agent')
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Create and start the application
    app = BLEChatApp(args.agent_id)
    await app.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
