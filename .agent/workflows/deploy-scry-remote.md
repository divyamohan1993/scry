---
description: Deploy Scry Remote to GCloud Ubuntu VM
---

# Deploying Scry Remote to GCloud

This workflow deploys the Scry Remote framework to a Google Cloud Ubuntu VM with the domain scry.dmj.one.

## Prerequisites

1. A GCloud account with a project
2. Domain `scry.dmj.one` ready to point to VM IP
3. Google OAuth credentials (from Google Cloud Console)
4. Gemini API key

---

## Step 1: Create GCloud VM

1. Go to Google Cloud Console → Compute Engine → VM instances
2. Click "Create Instance"
3. Configure:
   - Name: `scry-remote`
   - Region: Choose closest to users
   - Machine type: `e2-small` (2 vCPU, 2GB RAM) or larger
   - Boot disk: Ubuntu 22.04 LTS, 20GB SSD
   - Firewall: Allow HTTP and HTTPS traffic
4. Create and note the external IP

---

## Step 2: Configure DNS

Point your domain to the VM:

1. Go to your DNS provider (e.g., Cloudflare, GoDaddy)
2. Add an A record:
   - Name: `scry` (or `@` for root domain)
   - Type: `A`
   - Value: `<VM_EXTERNAL_IP>`
   - TTL: 3600 (or Auto)
3. Wait for DNS propagation (few minutes to few hours)

Test with: `nslookup scry.dmj.one`

---

## Step 3: Configure Google OAuth

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Configure consent screen if prompted
4. Application type: Web application
5. Name: "Scry Remote"
6. Authorized JavaScript origins:
   - `https://scry.dmj.one`
7. Authorized redirect URIs:
   - `https://scry.dmj.one/auth/callback`
8. Copy the Client ID and Client Secret

---

## Step 4: SSH into VM and Install

```bash
# SSH into the VM
gcloud compute ssh scry-remote

# Clone the repository (or upload files)
git clone https://github.com/divyamohan1993/scry.git
cd scry/remote/deploy

# Run installation
sudo DOMAIN=scry.dmj.one ./install.sh
```

---

## Step 5: Configure Environment

```bash
# Edit the .env file
sudo nano /opt/scry-remote/.env
```

Configure these values:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GEMINI_API_KEY=your-gemini-api-key
SECRET_KEY=generate-with-openssl-rand-hex-32
DOMAIN=scry.dmj.one
```

---

## Step 6: Setup SSL

```bash
# Run SSL setup
cd /opt/scry-remote/deploy
sudo ./ssl-setup.sh scry.dmj.one
```

---

## Step 7: Start Services

```bash
# Restart the service
sudo systemctl restart scry-remote

# Restart nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status scry-remote
```

---

## Step 8: Verify Deployment

1. Open https://scry.dmj.one in a browser
2. You should see the login page
3. Click "Login with Google"
4. After authentication, you should see the dashboard

---

## Troubleshooting

### View Logs

```bash
# Application logs
journalctl -u scry-remote -f

# Nginx logs
tail -f /var/log/nginx/scry-remote.error.log
```

### Common Issues

**SSL Certificate Issues:**
```bash
sudo certbot --nginx -d scry.dmj.one
```

**Permission Issues:**
```bash
sudo chown -R scry:scry /opt/scry-remote
```

**Port Already in Use:**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

---

## Updating

To update to a new version:

```bash
cd /opt/scry-remote
sudo -u scry git pull
sudo systemctl restart scry-remote
```
