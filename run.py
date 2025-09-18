"""
Bluetooth Mesh AI Agents - Demo Runner

This script demonstrates the simulated mesh network with AI agents
communicating with each other.
"""
import asyncio
import signal
import sys
from typing import List

from mesh import MeshNetwork
from agent import Agent

# Global variables for cleanup
agents: List[Agent] = []

async def main():
    """Main entry point for the demo."""
    print("=== Bluetooth Mesh AI Agents Demo ===\n")
    
    # Create the mesh network
    mesh = MeshNetwork()
    
    try:
        # Create and initialize agents
        alice = Agent("Alice", mesh)
        bob = Agent("Bob", mesh)
        charlie = Agent("Charlie", mesh)
        
        # Store references for cleanup
        global agents
        agents = [alice, bob, charlie]
        
        # Give the agents a moment to initialize
        await asyncio.sleep(1)
        
        print("\n=== Starting Conversation ===")
        
        # Start a conversation about Toronto's weather
        await alice.start_conversation("Bob", "Hey Bob, have you checked the weather in Toronto today? I heard it's quite unpredictable this time of year.")
        
        # Wait a bit for the conversation to progress
        await asyncio.sleep(2)
        
        # Bob responds about the weather
        await bob.start_conversation("Alice", "Hi Alice! Yes, I just saw the forecast. It's currently 18°C with a mix of sun and clouds. Perfect weather for a walk by the lake!")
        
        # Wait a bit more
        await asyncio.sleep(2)
        
        # Charlie joins the conversation
        await charlie.start_conversation("Alice", "Hi Alice and Bob! I just checked the forecast for Toronto. They're predicting a high of 22°C today with a 20% chance of rain in the evening.")
        
        # Let the conversation continue naturally
        await asyncio.sleep(1)
        
        # Keep the program running
        print("\n=== Agents are chatting (Press Ctrl+C to exit) ===")
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        print("\nShutting down...")
    finally:
        # Clean up all agents
        for agent in agents:
            await agent.close()
        print("All agents have been shut down.")

async def shutdown(signal, loop):
    """Handle shutdown gracefully."""
    print(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Register signal handlers for graceful shutdown on Unix systems
        if sys.platform != 'win32':
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig, 
                    lambda s=sig: asyncio.create_task(shutdown(s, loop))
                )
        
        # Run the main coroutine
        loop.run_until_complete(main())
        
    except asyncio.CancelledError:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up the event loop
        if loop.is_running():
            loop.stop()
        loop.close()
        print("Demo completed.")
