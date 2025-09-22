"""
Bluetooth Low Energy (BLE) Communicator

This module provides a simple BLE communication layer for agent communication
between two separate machines using the Bleak library.
"""
import asyncio
import json
import logging
import uuid
from typing import Dict, Callable, Optional, Any

from bleak import BleakClient, BleakServer, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# BLE Service and Characteristic UUIDs
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
MESSAGE_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

class BLECommunicator:
    """
    A BLE-based communication class for agent messaging between two machines.
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize the BLE Communicator.
        
        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id
        self.callback = None
        self.client = None
        self.server = None
        self.connected = False
        self.message_queue = asyncio.Queue()
        self.target_device = None
        
    async def start(self, message_callback: Callable[[str, dict], None]) -> None:
        """
        Start the BLE communicator.
        
        Args:
            message_callback: Function to call when a message is received
        """
        self.callback = message_callback
        
        # Start the BLE server
        await self._start_server()
        
        # Start scanning for other devices
        asyncio.create_task(self._scan_for_devices())
        
        # Start processing outgoing messages
        asyncio.create_task(self._process_message_queue())
    
    async def stop(self) -> None:
        """Stop the BLE communicator and clean up resources."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
        if self.server:
            await self.server.stop()
    
    async def send_message(self, target_id: str, message: dict) -> None:
        """
        Send a message to another agent.
        
        Args:
            target_id: ID of the target agent
            message: Message data to send (must be JSON serializable)
        """
        message_data = {
            "sender": self.agent_id,
            "recipient": target_id,
            "timestamp": asyncio.get_event_loop().time(),
            "data": message
        }
        await self.message_queue.put(message_data)
    
    async def _process_message_queue(self) -> None:
        """Process outgoing messages from the queue."""
        while True:
            message = await self.message_queue.get()
            
            if not self.connected or not self.client or not self.client.is_connected:
                logger.warning("Not connected to any device. Cannot send message.")
                continue
                
            try:
                await self._send_ble_message(self.client, message)
                logger.info(f"Message sent to {message.get('recipient')}")
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                self.connected = False
    
    async def _start_server(self) -> None:
        """Start the BLE server for receiving messages."""
        self.server = BleakServer(self.agent_id)
        
        def notification_handler(sender, data: bytearray):
            """Handle incoming BLE notifications."""
            try:
                message = json.loads(data.decode('utf-8'))
                if self.callback:
                    self.callback(message.get('sender'), message.get('data', {}))
            except Exception as e:
                logger.error(f"Error handling notification: {e}")
        
        # Add our service and characteristic
        await self.server.add_service(
            SERVICE_UUID,
            [{
                "uuid": MESSAGE_CHAR_UUID,
                "properties": ["read", "write", "notify"],
                "value": None,
                "descriptors": [
                    "00002902-0000-1000-8000-00805f9b34fb",  # Client Characteristic Configuration
                ],
            }]
        )
        
        # Set up notification handler
        await self.server.start_notify(MESSAGE_CHAR_UUID, notification_handler)
        
        # Start the server
        await self.server.start()
        logger.info(f"BLE server started as '{self.agent_id}'")
    
    async def _scan_for_devices(self) -> None:
        """Scan for other BLE devices."""
        scanner = BleakScanner(self._detection_callback)
        
        try:
            await scanner.start()
            logger.info("Scanning for devices...")
            
            while True:
                await asyncio.sleep(5.0)  # Scan continuously
                
        except asyncio.CancelledError:
            pass
        finally:
            await scanner.stop()
    
    def _detection_callback(self, device: BLEDevice, advertisement_data: AdvertisementData) -> None:
        """Handle discovered BLE devices."""
        if device.name and device.name != self.agent_id and not self.connected:
            logger.info(f"Found device: {device.name} ({device.address})")
            self.target_device = device
            asyncio.create_task(self._connect_to_device())
    
    async def _connect_to_device(self) -> None:
        """Connect to the discovered BLE device."""
        if not self.target_device or self.connected:
            return
            
        if self.client and self.client.is_connected:
            return
            
        logger.info(f"Attempting to connect to {self.target_device.name}...")
        self.client = BleakClient(self.target_device.address)
        
        try:
            await self.client.connect()
            self.connected = True
            logger.info(f"Connected to {self.target_device.name}")
            
            # Start notifications
            await self.client.start_notify(MESSAGE_CHAR_UUID, self._notification_handler)
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.target_device.name}: {e}")
            self.connected = False
            self.client = None
    
    async def _send_ble_message(self, client: BleakClient, message: dict) -> None:
        """
        Send a message over BLE.
        
        Args:
            client: Connected BLE client
            message: Message to send (will be JSON serialized)
        """
        try:
            message_str = json.dumps(message)
            message_bytes = message_str.encode('utf-8')
            
            # Send the message in chunks if needed
            max_chunk_size = 20  # Standard BLE MTU is 20 bytes
            for i in range(0, len(message_bytes), max_chunk_size):
                chunk = message_bytes[i:i + max_chunk_size]
                await client.write_gatt_char(MESSAGE_CHAR_UUID, chunk, response=True)
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    def _notification_handler(self, sender, data: bytearray) -> None:
        """Handle incoming BLE notifications."""
        try:
            message = json.loads(data.decode('utf-8'))
            if self.callback:
                self.callback(message.get('sender'), message.get('data', {}))
        except Exception as e:
            logger.error(f"Error handling notification: {e}")
