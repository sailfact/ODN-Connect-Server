#!/usr/bin/env bash
# Generate WireGuard server keypair and write to the wg-config volume.
# Run once before first `docker compose up`.
set -euo pipefail

PRIVKEY=$(wg genkey)
PUBKEY=$(echo "$PRIVKEY" | wg pubkey)

echo "Server private key: $PRIVKEY"
echo "Server public key:  $PUBKEY"

# If running inside the project, write to config dir
CONFIG_DIR="${WG_CONFIG_DIR:-./nginx/certs}"  # overridden by docker exec
echo "$PRIVKEY" > /etc/wireguard/privatekey
echo "$PUBKEY"  > /etc/wireguard/publickey
chmod 600 /etc/wireguard/privatekey

echo "Keys written to /etc/wireguard/"
