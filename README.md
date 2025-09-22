# BLE Chat Application

A simple Bluetooth Low Energy (BLE) chat application that allows communication between two agents running on separate machines.

## Features

- Connect two devices over BLE
- Send and receive text messages
- Simple command-line interface
- Automatic peer discovery
- Works on Windows, macOS, and Linux

## Prerequisites

- Python 3.8 or higher
- Bluetooth 4.0 or higher (BLE support required)
- Bleak library (will be installed via requirements.txt)

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd ble_agent
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### On the first machine (e.g., "Alice"):
```bash
python main.py Alice
```

### On the second machine (e.g., "Bob"):
```bash
python main.py Bob
```

### Available Commands

- `/help` - Show help message
- `/exit` - Exit the application
- `/list` - List connected peers
- `/msg <peer_id> <message>` - Send a message to a peer

## How It Works

1. Each agent starts a BLE server with a unique name (the agent ID)
2. Agents scan for other BLE devices and automatically connect when a peer is found
3. Once connected, you can send messages between the agents
4. Messages are sent as BLE notifications between the devices

## Troubleshooting

### Connection Issues
- Make sure Bluetooth is enabled on both devices
- Ensure the devices are within range (typically up to 10 meters)
- Check that no firewall is blocking the Bluetooth connection

### Error: "Bluetooth device not found"
- Make sure your Bluetooth adapter is working properly
- Check that the required Bluetooth drivers are installed

## License

This project is licensed under the MIT License - see the LICENSE file for details.
