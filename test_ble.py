import asyncio
import json
from ble_bridge import BLEBridge

async def main():
    def message_received(sender, message):
        print(f"Received from {sender}: {message}")
        if message.get("type") == "ping":
            asyncio.create_task(send_pong(bridge, sender))

    async def send_pong(bridge, sender):
        await asyncio.sleep(1)  # Simulate processing time
        await bridge.send_message({
            "type": "pong",
            "from": "server",
            "to": sender,
            "message": "Pong!"
        })

    # Create and start the BLE bridge
    bridge = BLEBridge(message_received)
    await bridge.start()

    try:
        print("BLE Bridge is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping BLE bridge...")
    finally:
        await bridge.stop()

if __name__ == "__main__":
    asyncio.run(main())