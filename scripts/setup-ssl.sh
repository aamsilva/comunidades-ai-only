#!/bin/bash
# SSL Setup Script — Let's Encrypt
# Usage: ./setup-ssl.sh staging.comunidades.ai

set -e

DOMAIN=${1:-staging.comunidades.ai}
EMAIL=${2:-dev@hexalabs.io}

echo "🔒 SSL Setup — $DOMAIN"
echo "======================"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y certbot
    elif command -v yum &> /dev/null; then
        sudo yum install -y certbot
    else
        echo "❌ Cannot install certbot automatically"
        exit 1
    fi
fi

# Create webroot for ACME challenge
sudo mkdir -p /var/www/certbot

# Obtain certificate
echo "📜 Obtaining certificate for $DOMAIN..."
sudo certbot certonly \
    --standalone \
    --agree-tos \
    --no-eff-email \
    --email $EMAIL \
    -d $DOMAIN \
    -d relay.$DOMAIN \
    -d api.$DOMAIN

# Verify
echo "✅ Verifying certificate..."
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "Certificate installed successfully!"
    sudo openssl x509 -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" -noout -text | grep -A2 "Validity"
else
    echo "❌ Certificate not found"
    exit 1
fi

# Setup auto-renewal
echo "🔄 Setting up auto-renewal..."
(sudo crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | sudo crontab -

echo ""
echo "======================"
echo "✅ SSL Setup Complete!"
echo ""
echo "Certificate path: /etc/letsencrypt/live/$DOMAIN/"
echo "Auto-renewal: Enabled (daily at 12:00)"
echo ""
echo "Next: Update docker-compose.staging.yml with the certificate paths"
