#!/bin/bash
# Generate self-signed SSL certificates for development
# For production, replace with real certificates from Let's Encrypt or CA

set -e

SSL_DIR="./ssl"
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Generate private key
openssl genrsa -out "$KEY_FILE" 2048

# Generate certificate
openssl req -new -x509 -key "$KEY_FILE" -out "$CERT_FILE" -days 365 -subj "/C=US/ST=CA/L=San Francisco/O=LeanVibe/OU=Agent Hive/CN=localhost"

# Set proper permissions
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "SSL certificates generated successfully:"
echo "  Certificate: $CERT_FILE"
echo "  Private Key: $KEY_FILE"
echo ""
echo "Note: These are self-signed certificates for development only."
echo "For production, use certificates from a trusted CA or Let's Encrypt."