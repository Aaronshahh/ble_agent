"""
Simple BLE Mesh Implementation for Windows

This is a simplified version that works reliably on Windows using Bleak.
"""
import asyncio
import json
import uuid
from typing import Dict, Callable, Any, Optional, List

from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic

# BLE Service and Characteristic UUIDs
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
MESSAGE_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

class SimpleBLEMesh:
    """A simplified BLE mesh implementation for Windows."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.callbacks: Dict[str, Callable[[str, dict], None]] = {}
        self.connected_devices: Dict[str, BleakClient] = {}
        self.running = False
        self.local_name = f"AgentMesh-{agent_id}"
    
    def register_callback(self, message_type: str, callback: Callable[[str, dict], None]):
        """Register a callback for a specific message type."""
        self.callbacks[message_type] = callback
    
    async def start(self):
        """Start the BLE mesh."""
        self.running = True
        print(f"[BLE] Starting BLE mesh as {self.local_name}")
        
        # Start scanning for other devices
        asyncio.create_task(self._scan_loop())
    
    async def stop(self):
        """Stop the BLE mesh."""
        self.running = False
        for client in self.connected_devices.values():
            if client.is_connected:
                await client.disconnect()
    
    async def send_message(self, target_id: str, message: dict):
        """Send a message to a specific agent."""
        if target_id in self.connected_devices:
            client = self.connected_devices[target_id]
            try:
                if client.is_connected:
                    message_str = json.dumps(message)
                    # Send in chunks of 20 bytes (BLE MTU)
                    for i in range(0, len(message_str), 20):
                        chunk = message_str[i:i+20].encode('utf-8')
                        await client.write_gatt_char(MESSAGE_CHAR_UUID, chunk)
                    print(f"[SENT to {target_id}] {message.get('content', '')}")
            except Exception as e:
                print(f"[ERROR] Failed to send to {target_id}: {e}")
                if target_id in self.connected_devices:
                    del self.connected_devices[target_id]
    
    async def _scan_loop(self):
        """Continuously scan for other BLE devices."""
        while self.running:
            try:
                print("[BLE] Scanning for devices...")
                devices = await BleakScanner.discover(timeout=5.0)
                
                for device in devices:
                    if device.name and device.name.startswith("AgentMesh-"):
                        peer_id = device.name.split("-", 1)[1]
                        if peer_id != self.agent_id and peer_id not in self.connected_devices:
                            print(f"[BLE] Found peer: {peer_id}")
                            await self._connect_to_peer(peer_id, device.address)
                
            except Exception as e:
                print(f"[ERROR] Scan error: {e}")
            
            await asyncio.sleep(5)
    
    async def _connect_to_peer(self, peer_id: str, address: str):
        """Connect to a peer device."""
        if peer_id in self.connected_devices:
            return
        
        try:
            print(f"[BLE] Connecting to {peer_id}...")
            client = BleakClient(address)
            await client.connect()
            
            # Set up notification handler
            await client.start_notify(MESSAGE_CHAR_UUID, self._notification_handler)
            
            self.connected_devices[peer_id] = client
            print(f"[BLE] Connected to {peer_id}")
            
        except Exception as e:
            print(f"[ERROR] Failed to connect to {peer_id}: {e}")
    
    def _notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray):
        """Handle incoming BLE notifications."""
        try:
            message_str = data.decode('utf-8')
            message = json.loads(message_str)
            
            if 'type' in message and message['type'] in self.callbacks:
                # Find which peer sent this message
                peer_id = None
                for pid, client in self.connected_devices.items():
                    if client.is_connected and client.address == sender.service.client.address:
                        peer_id = pid
                        break
                
                if peer_id:
                    self.callbacks[message['type']](peer_id, message)
                    
        except Exception as e:
            print(f"[ERROR] Notification error: {e}")
