# Complete Deployment Guide for Streamlit Document Generator

## Prerequisites
- Ubuntu/Debian server with sudo access
- SSH access to your server
- Domain name (e.g., `doc-maker.com`)

---

## Part 1: Initial Server Setup

### Step 1.1: Update System Packages
```bash
sudo apt update
sudo apt upgrade -y
```

### Step 1.2: Install Required Software
```bash
sudo apt install -y python3 python3-pip python3-venv nginx git
```

### Step 1.3: Create Application Directory
```bash
sudo mkdir -p /var/www/doc-generator
sudo chown $USER:$USER /var/www/doc-generator
cd /var/www/doc-generator
```

### Step 1.4: Clone Repository
```bash
git clone https://github.com/revelwivanto/LLM_document-maker.git .
```

---

## Part 2: Python Virtual Environment Setup

### Step 2.1: Create Virtual Environment
```bash
python3 -m venv venv
```

### Step 2.2: Activate Virtual Environment
```bash
source venv/bin/activate
```

### Step 2.3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2.4: Deactivate (when done testing)
```bash
deactivate
```

---

## Part 3: Systemd Service Configuration
### nano etc/systemd/system/docgen.service file


### Step 3.1: Create Servie file
```bash
sudo nano /etc/systemd/system/docgen.service
```

### Step 3.2: Verify Service File Permissions
```bash
sudo chmod 644 /etc/systemd/system/docgen.service
sudo chown root:root /etc/systemd/system/docgen.service
```

### Step 3.3: Reload Systemd Daemon
```bash
sudo systemctl daemon-reload
```

### Step 3.4: Enable Service (Auto-start on Boot)
```bash
sudo systemctl enable docgen.service
```

### Step 3.5: Start the Service
```bash
sudo systemctl start docgen.service
```

### Step 3.6: Check Service Status
```bash
sudo systemctl status docgen.service
```

### Step 3.7: View Real-time Logs
```bash
sudo journalctl -u docgen.service -f
```

Expected output:
```
docgen[XXXX]: You can now view your Streamlit app in your browser.
docgen[XXXX]: URL: http://127.0.0.1:8501
```

---

## Part 4: Nginx Configuration

### Step 4.1: Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/doc-generator
```

### Step 4.2: Paste Configuration (Copy the block below)
```nginx
upstream streamlit {
    server 127.0.0.1:8501;
}

server {
    listen 80;
    server_name doc-maker.com www.doc-maker.com;
    client_max_body_size 100M;

    # Redirect HTTP to HTTPS (optional - uncomment after SSL setup)
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://streamlit;
        proxy_http_version 1.1;
        
        # Headers required for Streamlit WebSocket
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long requests
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # Logs
    access_log /var/log/nginx/doc-generator_access.log;
    error_log /var/log/nginx/doc-generator_error.log;
}
```

### Step 4.3: Enable the Site
```bash
sudo ln -s /etc/nginx/sites-available/doc-generator /etc/nginx/sites-enabled/doc-generator
```

### Step 4.4: Remove Default Site (if exists)
```bash
sudo rm /etc/nginx/sites-enabled/default
```

### Step 4.5: Test Nginx Configuration
```bash
sudo nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Step 4.6: Reload Nginx
```bash
sudo systemctl reload nginx
```

### Step 4.7: Check Nginx Status
```bash
sudo systemctl status nginx
```

---

## Part 5: DNS Configuration

### Step 5.1: Get Your Server's IP Address
```bash
hostname -I
```

This will show your server's IP, e.g., `192.168.1.100` or `203.0.113.50` (for public IP)

### Step 5.2: Configure DNS (Choose your provider)

#### For Cloudflare:
1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain
3. Go to DNS > Records
4. Click "Add record"
5. Create two A records:
   - **Type:** A
   - **Name:** @
   - **IPv4 address:** YOUR_SERVER_IP
   - **TTL:** Auto
   - **Proxy status:** DNS only (gray cloud)
6. Create second record for www:
   - **Type:** A
   - **Name:** www
   - **IPv4 address:** YOUR_SERVER_IP

#### For Namecheap:
1. Log in to [Namecheap Dashboard](https://www.namecheap.com/myaccount/login/)
2. Go to "Domain List"
3. Click "Manage" next to your domain
4. Go to "Advanced DNS"
5. Add/Edit A Record:
   - **Host:** @
   - **Value:** YOUR_SERVER_IP
   - **TTL:** 30 min
6. Add A Record for www:
   - **Host:** www
   - **Value:** YOUR_SERVER_IP

#### For GoDaddy:
1. Log in to [GoDaddy](https://www.godaddy.com/en-in/account/security)
2. Find your domain and click "Manage DNS"
3. Edit the A record:
   - **Points to:** YOUR_SERVER_IP
4. Add www subdomain if needed

#### For Other Providers:
1. Find your domain's DNS management
2. Create/Edit A record:
   - **Name:** @ (or leave blank for root)
   - **Type:** A
   - **Value:** YOUR_SERVER_IP
3. Create A record for www:
   - **Name:** www
   - **Type:** A
   - **Value:** YOUR_SERVER_IP

### Step 5.3: Verify DNS Propagation
```bash
# Wait 5-15 minutes for DNS to propagate, then test:
nslookup doc-maker.com

# Or use dig:
dig doc-maker.com

# Or check from your server:
host doc-maker.com
```

Expected output should show your server's IP address.

---

## Part 6: Verification & Testing

### Step 6.1: Check If Service is Running
```bash
sudo systemctl status docgen.service
```

### Step 6.2: Check If Port 8501 is Listening
```bash
sudo ss -tlnp | grep 8501
```

Expected output:
```
LISTEN 127.0.0.1:8501
```

### Step 6.3: Test Streamlit Directly
```bash
curl http://127.0.0.1:8501
```

Should return HTML content (beginning of Streamlit page).

### Step 6.4: Test Nginx Proxy
```bash
curl http://localhost
```

### Step 6.5: Test from Browser
Once DNS is propagated:
```
http://doc-maker.com
```

You should see the Streamlit app!

---

## Part 7: SSL Certificate (Optional but Recommended)

### Step 7.1: Install Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Step 7.2: Get Free SSL Certificate
```bash
sudo certbot certonly --nginx -d doc-maker.com -d www.doc-maker.com
```

### Step 7.3: Update Nginx for HTTPS
Edit the Nginx config:
```bash
sudo nano /etc/nginx/sites-available/doc-generator
```

Replace the entire file with:
```nginx
upstream streamlit {
    server 127.0.0.1:8501;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name doc-maker.com www.doc-maker.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name doc-maker.com www.doc-maker.com;
    client_max_body_size 100M;

    # SSL certificates (from Certbot)
    ssl_certificate /etc/letsencrypt/live/doc-maker.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/doc-maker.com/privkey.pem;

    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://streamlit;
        proxy_http_version 1.1;
        
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    access_log /var/log/nginx/doc-generator_access.log;
    error_log /var/log/nginx/doc-generator_error.log;
}
```

### Step 7.4: Test and Reload Nginx
```bash
sudo nginx -t
sudo systemctl reload nginx
```

Now your site is accessible at `https://doc-maker.com`

### Step 7.5: Auto-renew SSL Certificate
```bash
sudo certbot renew --dry-run
```

Certbot will auto-renew 30 days before expiration.

---

## Part 8: Troubleshooting

### Service Not Starting
```bash
# Check logs
sudo journalctl -u docgen.service -n 50

# Check service file syntax
sudo systemd-analyze verify /etc/systemd/system/docgen.service

# Try restarting
sudo systemctl daemon-reload
sudo systemctl restart docgen.service
```

### Port 8501 Not Listening
```bash
# Check if process is running
ps aux | grep streamlit

# Check if port is in use by something else
sudo lsof -i :8501

# Kill and restart
sudo systemctl stop docgen.service
sudo systemctl start docgen.service
```

### Nginx 502 Bad Gateway
```bash
# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Verify Streamlit is running
sudo ss -tlnp | grep 8501

# Test proxy connection
curl http://127.0.0.1:8501
```

### DNS Not Resolving
```bash
# Flush DNS cache
sudo systemctl restart systemd-resolved

# Test DNS
nslookup doc-maker.com
dig doc-maker.com @8.8.8.8

# Check if your domain registrar points to correct nameservers
```

### View All Logs
```bash
# Streamlit logs
sudo journalctl -u docgen.service -f

# Nginx access
sudo tail -f /var/log/nginx/doc-generator_access.log

# Nginx errors
sudo tail -f /var/log/nginx/doc-generator_error.log

# System logs
sudo journalctl -f
```

---

## Quick Reference Commands

```bash
# Service management
sudo systemctl start docgen.service
sudo systemctl stop docgen.service
sudo systemctl restart docgen.service
sudo systemctl status docgen.service
sudo systemctl enable docgen.service
sudo systemctl disable docgen.service

# View logs
sudo journalctl -u docgen.service -f
sudo journalctl -u docgen.service -n 50

# Nginx management
sudo systemctl reload nginx
sudo systemctl restart nginx
sudo nginx -t

# Check ports
sudo ss -tlnp | grep 8501
sudo ss -tlnp | grep 80

# Test connectivity
curl http://127.0.0.1:8501
curl http://localhost
ping doc-maker.com
nslookup doc-maker.com
```

---

## Final Checklist

- [ ] Cloned repository to `/var/www/doc-generator`
- [ ] Virtual environment created and dependencies installed
- [ ] `docgen.service` copied to `/etc/systemd/system/`
- [ ] Service is running: `sudo systemctl status docgen.service`
- [ ] Port 8501 is listening: `sudo ss -tlnp | grep 8501`
- [ ] Nginx configured at `/etc/nginx/sites-available/doc-generator`
- [ ] Nginx is running: `sudo systemctl status nginx`
- [ ] Domain DNS records point to server IP
- [ ] DNS is resolving: `nslookup doc-maker.com`
- [ ] Site accessible at `http://doc-maker.com`
- [ ] SSL certificate installed (optional but recommended)
- [ ] Site accessible at `https://doc-maker.com`

---

## Support

If you encounter issues:
1. Check logs: `sudo journalctl -u docgen.service -f`
2. Verify Nginx: `sudo nginx -t`
3. Test connectivity: `curl http://127.0.0.1:8501`
4. Review error logs: `sudo tail -f /var/log/nginx/error.log`

Good luck! 🚀
