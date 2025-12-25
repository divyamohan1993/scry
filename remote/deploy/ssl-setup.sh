#!/bin/bash
# =============================================================================
# SCRY REMOTE - SSL SETUP SCRIPT
# =============================================================================
# Sets up Let's Encrypt SSL certificates for the domain
# Usage: sudo ./ssl-setup.sh [domain]
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

# Get domain
DOMAIN="${1:-scry.dmj.one}"
EMAIL="${2:-admin@${DOMAIN}}"

log_info "Setting up SSL for: ${DOMAIN}"
log_info "Email for notifications: ${EMAIL}"

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    log_info "Installing certbot..."
    apt-get update -qq
    apt-get install -y certbot python3-certbot-nginx
fi

# Check if certificate exists
if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    log_warning "Certificate already exists for ${DOMAIN}"
    
    read -p "Do you want to renew/replace it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Keeping existing certificate"
        exit 0
    fi
fi

# Verify domain points to this server
log_info "Checking DNS resolution..."
SERVER_IP=$(curl -s https://api.ipify.org)
DOMAIN_IP=$(dig +short ${DOMAIN} | head -1)

if [ "${SERVER_IP}" != "${DOMAIN_IP}" ]; then
    log_warning "Domain ${DOMAIN} resolves to ${DOMAIN_IP}"
    log_warning "This server's IP is ${SERVER_IP}"
    log_warning "Make sure DNS is correctly configured!"
    
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Aborted. Please configure DNS first."
        exit 1
    fi
fi

# Create temporary nginx config for challenge
log_info "Preparing for ACME challenge..."

# Ensure webroot exists
mkdir -p /var/www/html/.well-known/acme-challenge

# Get certificate
log_info "Requesting certificate from Let's Encrypt..."

certbot certonly \
    --nginx \
    -d ${DOMAIN} \
    --non-interactive \
    --agree-tos \
    --email ${EMAIL} \
    --redirect

if [ $? -eq 0 ]; then
    log_success "Certificate obtained successfully!"
else
    log_error "Failed to obtain certificate"
    log_info "Trying standalone method..."
    
    # Stop nginx temporarily
    systemctl stop nginx
    
    certbot certonly \
        --standalone \
        -d ${DOMAIN} \
        --non-interactive \
        --agree-tos \
        --email ${EMAIL}
    
    # Restart nginx
    systemctl start nginx
fi

# Setup auto-renewal
log_info "Setting up auto-renewal..."

# Create renewal hook
mkdir -p /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh << 'EOF'
#!/bin/bash
# Reload nginx after certificate renewal
systemctl reload nginx
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

# Test renewal
log_info "Testing certificate renewal..."
certbot renew --dry-run

# Verify certificate
log_info "Verifying certificate..."
openssl x509 -in /etc/letsencrypt/live/${DOMAIN}/fullchain.pem -text -noout | grep -E "Subject:|Issuer:|Not Before:|Not After :"

echo ""
log_success "=============================================="
log_success "       SSL SETUP COMPLETE!"
log_success "=============================================="
echo ""
log_info "Certificate location:"
echo "  Fullchain: /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
echo "  Private key: /etc/letsencrypt/live/${DOMAIN}/privkey.pem"
echo ""
log_info "Auto-renewal is configured via certbot systemd timer"
echo "  Check status: systemctl status certbot.timer"
echo ""
log_info "Restart nginx to apply:"
echo "  sudo systemctl restart nginx"
echo ""
