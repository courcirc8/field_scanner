#!/bin/bash

# Script to configure a static IP for the Ethernet interface (enp2s0)

# Define the interface name and static IP configuration
INTERFACE="enp2s0"
STATIC_IP="192.168.1.2"
SUBNET_MASK="255.255.255.0"
GATEWAY="192.168.1.1"

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root (use sudo)."
  exit 1
fi

# Bring the interface up with the static IP
echo "Configuring $INTERFACE with IP $STATIC_IP..."
ip addr flush dev $INTERFACE  # Clear any existing IP configuration
ip addr add $STATIC_IP/$SUBNET_MASK dev $INTERFACE
ip link set $INTERFACE up

# Set the default gateway
echo "Setting default gateway to $GATEWAY..."
ip route add default via $GATEWAY dev $INTERFACE

# Verify the configuration
echo "Configuration complete. Current settings for $INTERFACE:"
ip addr show dev $INTERFACE

echo "You can now connect to your 3D printer at its static IP."