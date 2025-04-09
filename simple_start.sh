#!/bin/bash

# Enable debugging
set -e  # Exit immediately if a command exits with a non-zero status
set -x  # Print each command before executing it

# Define the Ethernet interface and IP address
INTERFACE="enp2s0"
IP_ADDRESS="192.168.2.1"  # Make sure this is on the same subnet as the printer (192.168.2.x)

# Display current network status
echo "Current network interfaces:"
ip addr

# Remove any existing IP addresses from the interface
echo "Removing existing IP addresses from $INTERFACE..."
ip addr flush dev "$INTERFACE"

# Add the new IP address to the interface
echo "Adding IP address $IP_ADDRESS to $INTERFACE..."
if ip addr add "$IP_ADDRESS/24" dev "$INTERFACE"; then
    echo "IP address $IP_ADDRESS added to $INTERFACE"
else
    echo "Failed to add IP address $IP_ADDRESS to $INTERFACE"
    exit 1
fi

# Bring up the interface
echo "Bringing up interface $INTERFACE..."
ip link set "$INTERFACE" up

# Display new network status
echo "Updated network interfaces:"
ip addr

# Check connectivity to the printer
echo "Testing connectivity to printer..."
PRINTER_IP="192.168.2.100"
ping -c 3 "$PRINTER_IP"
echo "Ping successful. Network connection to printer established."

# Test telnet connectivity
echo "Testing telnet connectivity to printer..."
nc -z -w 3 "$PRINTER_IP" 23
if [ $? -eq 0 ]; then
    echo "Telnet port (23) is open on the printer"
else
    echo "WARNING: Telnet port (23) appears to be closed on the printer"
fi