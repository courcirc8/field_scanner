#!/bin/bash

# Enable debugging
set -e  # Exit immediately if a command exits with a non-zero status
set -x  # Print each command before executing it

# Define the Ethernet interface and IP address
INTERFACE="enp2s0"
IP_ADDRESS="192.168.2.1"

# Remove any existing IP addresses on the interface
ip addr flush dev "$INTERFACE"

# Add the new IP address to the interface
if ip addr add "$IP_ADDRESS/24" dev "$INTERFACE"; then
    echo "IP address $IP_ADDRESS added to $INTERFACE"
else
    echo "Failed to add IP address $IP_ADDRESS to $INTERFACE"
    exit 1
fi