"""
Bluetooth Low Energy (BLE) Mesh Network Implementation

This module provides a BLE-based mesh network for agent communication.
It uses the Bleak library for cross-platform BLE support.
"""
import asyncio
import json
import uuid
import platform
from typing import Dict, Callable, Any, Optional, List, Tuple

from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic, BleakServer
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# BLE Service and Characteristic UUIDs
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
MESSAGE_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

class BLEMesh:
    """
    A BLE-based mesh network implementation for agent communication.
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize the BLE Mesh.
        
        Args:
            agent_id: Unique identifier for this agent in the mesh
        """
        self.agent_id = agent_id
        self.callbacks: Dict[str, Callable[[str, dict], None]] = {}
        self.connected_devices: Dict[str, BleakClient] = {}
        self.is_advertising = False
        self.message_queue = asyncio.Queue()
        self.scanning = False
        
        # Generate a unique local name for BLE advertisement
        self.local_name = f"AgentMesh-{agent_id}"
        
    async def start(self) -> None:
        """Start the BLE mesh network."""
        # Start advertising and scanning in the background
        asyncio.create_task(self._advertise())
        asyncio.create_task(self._scan_for_peers())
        asyncio.create_task(self._process_message_queue())
    
    async def stop(self) -> None:
        """Stop the BLE mesh network."""
        self.is_advertising = False
        self.scanning = False
        
        # Disconnect all connected devices
        for device_id, client in list(self.connected_devices.items()):
            if client.is_connected:
                await client.disconnect()
            del self.connected_devices[device_id]
    
    def register_callback(self, message_type: str, callback: Callable[[str, dict], None]) -> None:
        """
        Register a callback for a specific message type.
        
        Args:
            message_type: The type of message to register for
            callback: Function to call when message is received
        """
        self.callbacks[message_type] = callback
    
    async def send_message(self, target_id: str, message: dict) -> None:
        """
        Send a message to a specific agent.
        
        Args:
            target_id: ID of the target agent
            message: Message data to send (must be JSON serializable)
        """
        # Add metadata to the message
        message_with_meta = {
            "sender": self.agent_id,
            "recipient": target_id,
            "timestamp": asyncio.get_event_loop().time(),
            "data": message
        }
        
        # Add to message queue for processing
        await self.message_queue.put((target_id, message_with_meta))
    
    async def _process_message_queue(self) -> None:
        """Process messages from the send queue."""
        while True:
            target_id, message = await self.message_queue.get()
            
            # Check if we're already connected to the target
            client = self.connected_devices.get(target_id)
            
            if client and client.is_connected:
                try:
                    # Send the message
                    await self._send_ble_message(client, message)
                    print(f"[BLE] Sent message to {target_id}")
                except Exception as e:
                    print(f"[BLE] Error sending to {target_id}: {e}")
                    # Reconnect and retry
                    await self._connect_to_peer(target_id)
            else:
                # Try to connect and send
                if await self._connect_to_peer(target_id):
                    try:
                        await self._send_ble_message(self.connected_devices[target_id], message)
                        print(f"[BLE] Sent message to {target_id}")
                    except Exception as e:
                        print(f"[BLE] Failed to send to {target_id}: {e}")
                else:
                    print(f"[BLE] Could not connect to {target_id}")
    
    async def _advertise(self) -> None:
        """Advertise this device's presence on the BLE network."""
        self.is_advertising = True
        print(f"[BLE] Advertising as {self.local_name}")
        
        # On Windows, we need to create a BLE server to be discoverable
        async with BleakServer(self.local_name) as server:
            # Add our service and characteristic
            await server.add_service(
                SERVICE_UUID,
                [
                    {
                        "uuid": MESSAGE_CHAR_UUID,
                        "properties": ["read", "write", "notify"],
                        "value": None,
                    }
                ]
            )
            
            # Start advertising
            await server.start()
            print(f"[BLE] BLE server started and advertising")
            
            # Keep the server running
            while self.is_advertising:
                await asyncio.sleep(1)
    
    async def _scan_for_peers(self) -> None:
        """Scan for other BLE mesh devices."""
        self.scanning = True
        print("[BLE] Starting device scan...")
        
        # Windows-specific BLE scan settings
        scanner = BleakScanner(
            detection_callback=self._detection_callback,
            service_uuids=[SERVICE_UUID],
            scanning_mode="active"
        )
        
        try:
            async with scanner:
                while self.scanning:
                    print("[BLE] Scanning for peers...")
                    await asyncio.sleep(10.0)  # Scan for 10 seconds
        except Exception as e:
            print(f"[BLE] Error in scanner: {e}")
            self.scanning = False
    
    def _detection_callback(self, device, advertisement_data):
        """Handle discovered BLE devices."""
        try:
            if device.name and device.name.startswith("AgentMesh-"):
                peer_id = device.name.split("-", 1)[1]
                if peer_id != self.agent_id and peer_id not in self.connected_devices:
                    print(f"[BLE] Found peer: {peer_id} at {device.address}")
                    # Schedule connection in the event loop
                    asyncio.create_task(self._connect_to_peer(peer_id, device.address))
        except Exception as e:
            print(f"[BLE] Error in detection callback: {e}")
    
    async def _connect_to_peer(self, peer_id: str, address: str = None) -> bool:
        """
        Connect to a peer device.
        
        Args:
            peer_id: ID of the peer to connect to
            address: BLE address of the peer (optional, will scan if not provided)
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        if peer_id in self.connected_devices and self.connected_devices[peer_id].is_connected:
            return True
            
        if not address:
            # Try to find the device by name if address not provided
            devices = await BleakScanner.discover(timeout=5.0)
            for device in devices:
                if device.name == f"AgentMesh-{peer_id}":
                    address = device.address
                    break
            
            if not address:
                print(f"[BLE] Could not find device for {peer_id}")
                return False
        
        try:
            print(f"[BLE] Connecting to {peer_id} at {address}...")
            client = BleakClient(address)
            await client.connect()
            
            # Discover services
            await client.start_notify(MESSAGE_CHAR_UUID, self._notification_handler)
            
            # Store the connection
            self.connected_devices[peer_id] = client
            print(f"[BLE] Connected to {peer_id}")
            return True
            
        except Exception as e:
            print(f"[BLE] Failed to connect to {peer_id}: {e}")
            if peer_id in self.connected_devices:
                del self.connected_devices[peer_id]
            return False
    
    async def _send_ble_message(self, client: BleakClient, message: dict) -> None:
        """
        Send a message over BLE.
        
        Args:
            client: Connected BLE client
            message: Message to send (will be JSON serialized)
        """
        try:
            # Convert message to bytes
            message_str = json.dumps(message)
            message_bytes = message_str.encode('utf-8')
            
            # Send the message in chunks if needed
            max_chunk_size = 20  # Standard BLE MTU is 20 bytes
            for i in range(0, len(message_bytes), max_chunk_size):
                chunk = message_bytes[i:i + max_chunk_size]
                await client.write_gatt_char(MESSAGE_CHAR_UUID, chunk, response=True)
                
        except Exception as e:
            print(f"[BLE] Error sending message: {e}")
            raise
    
    def _notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray) -> None:
        """Handle incoming BLE notifications."""
        try:
            # Reassemble message chunks (simplified)
            message_str = data.decode('utf-8')
            message = json.loads(message_str)
            
            # Find the sender's ID from our connected devices
            sender_id = None
            for peer_id, client in self.connected_devices.items():
                if client.address == sender.service.client.address:
                    sender_id = peer_id
                    break
            
            if sender_id and 'type' in message and message['type'] in self.callbacks:
                # Call the appropriate callback
                self.callbacks[message['type']](sender_id, message['data'])
                
        except Exception as e:
            print(f"[BLE] Error handling notification: {e}")
