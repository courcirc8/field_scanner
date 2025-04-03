#!/bin/bash

# Enable debugging
set -e  # Exit immediately if a command exits with a non-zero status
set -x  # Print each command before executing it

# Define the Ethernet interface and IP address
INTERFACE="enp2s0"
IP_ADDRESS="192.168.1.2/24"

# Add the IP address to the interface
if ip addr add "$IP_ADDRESS" dev "$INTERFACE"; then
    echo "Successfully assigned IP address $IP_ADDRESS to $INTERFACE."
else
    echo "Failed to assign IP address. Please check the interface name and IP address."
    exit 1
fi

# Bring the interface up
if ip link set "$INTERFACE" up; then
    echo "Successfully brought up the interface $INTERFACE."
else
    echo "Failed to bring up the interface. Please check the interface name."
    exit 1
fi

# Display the interface status for verification
ip addr show "$INTERFACE"

