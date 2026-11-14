# ServicePulse — Ubuntu Server Security Hardening Baseline
**Enterprise Hybrid Remote Monitoring & Management (RMM) and IT Service Management (ITSM)**  
**Author:** Muhammadyusuf Usmonov  
**Academic Purpose:** Graduation Qualification Work (BMI), Tashkent University of Information Technologies (TUIT) & AT-Servis  
**Operating System:** Ubuntu 24.04 LTS / Ubuntu 22.04 LTS

---

## 1. Security Philosophy & Principles

ServicePulse enforces defense-in-depth security across every architectural boundary:
1. **Zero Unnecessary Host Port Exposure:** Only the reverse proxy (Caddy) binds public ports (`80`, `443`). PostgreSQL (`5432`) and FastAPI (`8000`) are accessible only inside private Docker bridge networks.
2. **Least Privilege Execution:** Containers run with resource boundaries and read-only mounts where possible. Secrets files are locked to `chmod 600`.
3. **Automated Protection:** Intrusion prevention (Fail2ban), automated security patches (`unattended-upgrades`), and kernel TCP hardening are enforced at the OS level.
4. **Non-Interactive Verification:** Every security control is validated with reproducible automated test scripts.

---

## 2. Firewall Architecture & Docker UFW Bypass Mitigation

### The Docker UFW Port Bypass Problem
By default, the Docker daemon automatically modifies Linux `iptables` by inserting routing rules in the `PREROUTING` chain of the `nat` table. Because `PREROUTING` rules execute *before* the `INPUT` chain where UFW rules reside, published container ports (e.g. `-p 5432:5432`) **bypass UFW firewall rules completely**, leaving services exposed to the public internet regardless of `ufw deny 5432`.

### ServicePulse Defense Strategy
1. **Architectural Mitigation in Compose:** In `compose.prod.yaml`, **no database or application ports are published to host interfaces**. Only Caddy publishes `80:80` and `443:443`.
2. **Internal Bridge Network:** All inter-container communication occurs across `servicepulse-prod-net`, preventing outside network access to PostgreSQL or FastAPI.
3. **UFW Default Policy:**
   ```bash
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw default deny routed
   ```
4. **Explicit Rules:**
   ```bash
   sudo ufw allow 22/tcp comment "SSH Management"
   sudo ufw allow 80/tcp comment "Caddy HTTP ACME Challenge"
   sudo ufw allow 443/tcp comment "Caddy HTTPS TLS"
   sudo ufw allow 443/udp comment "Caddy HTTP/3 QUIC"
   sudo ufw enable
   ```

---

## 3. SSH Hardening

SSH access to the production server must be locked down against brute-force attacks and credential theft:

### Configuration (`/etc/ssh/sshd_config.d/50-servicepulse-hardening.conf`)
```ini
# Enforce modern, secure SSH parameters
Port 22
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
```

Apply and verify:
```bash
sudo sshd -t && sudo systemctl restart ssh
```

---

## 4. Intrusion Prevention with Fail2ban

Fail2ban monitors system logs and automatically blocks IP addresses exhibiting malicious brute-force patterns.

### Configuration (`/etc/fail2ban/jail.local`)
```ini
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
banaction = ufw

[sshd]
enabled = true
port = 22
mode = aggressive
```

Check status:
```bash
sudo fail2ban-client status sshd
```

---

## 5. Automated Security Upgrades

Enable Ubuntu's unattended-upgrades service to automatically apply security patches without manual intervention:

```bash
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Verify `/etc/apt/apt.conf.d/20auto-upgrades`:
```apt
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
```

---

## 6. Kernel Network Hardening (`sysctl`)

Harden the Linux networking stack against common denial-of-service, spoofing, and redirection attacks.

Create `/etc/sysctl.d/99-servicepulse-security.conf`:
```ini
# SYN Flood Protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# IP Spoofing and Redirect Prevention
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Ignore Malicious ICMP Broadcasts
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
```

Load configuration:
```bash
sudo sysctl -p /etc/sysctl.d/99-servicepulse-security.conf
```

---

## 7. File System & Secrets Hygiene

1. **Production Environment File (`.env.production`):**
   ```bash
   chmod 600 /opt/servicepulse/.env.production
   chown root:root /opt/servicepulse/.env.production
   ```
2. **Backups Directory (`backups/`):**
   ```bash
   chmod 700 /opt/servicepulse/backups
   chown root:root /opt/servicepulse/backups
   ```
3. **Git Hygiene:** Strict `.gitignore` rules prevent `.env*`, `.key`, `.pem`, and `*.sql.gz` files from ever being staged or committed to source control.
4. **Secret Length Enforcement:** The backend validator (`backend/app/core/config.py`) rejects startup if `SECRET_KEY` or `AGENT_ENROLLMENT_SECRET` is shorter than 32 characters or matches insecure default strings.
