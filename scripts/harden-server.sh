#!/usr/bin/env bash
# ==============================================================================
# ServicePulse - Ubuntu Server Security Hardening Script
# Project: ServicePulse (AT-Servis BMI)
# Author: Muhammadyusuf Usmonov
# Target: Ubuntu 24.04 / 22.04 LTS
# ==============================================================================
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "Error: This hardening script must be executed as root (e.g. sudo bash harden-server.sh)" >&2
    exit 1
fi

SSH_PORT="${1:-22}"

echo "======================================================================"
echo " Starting Ubuntu Server Hardening for ServicePulse Production"
echo " Author: Muhammadyusuf Usmonov | Academic Purpose: AT-Servis BMI"
echo " Target SSH Port: ${SSH_PORT}"
echo "======================================================================"

# Step 1: System Update & Security Packages
echo "[1/7] Updating system and installing essential security tooling..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ufw \
    fail2ban \
    unattended-upgrades \
    iptables-persistent \
    curl \
    jq

# Step 2: Configure UFW Firewall
echo "[2/7] Configuring UFW Firewall policies..."
ufw default deny incoming
ufw default allow outgoing
ufw default deny routed

# Allow SSH
ufw allow "${SSH_PORT}/tcp" comment "SSH Remote Access"

# Allow Caddy HTTP/HTTPS (including HTTP/3 UDP)
ufw allow 80/tcp comment "Caddy HTTP (ACME challenge & HTTPS redirect)"
ufw allow 443/tcp comment "Caddy HTTPS TLS"
ufw allow 443/udp comment "Caddy HTTP/3 QUIC"

# Enable UFW
echo "y" | ufw enable
ufw status verbose

# Step 3: Mitigate Docker UFW Bypass
# Docker by default bypasses UFW by injecting PREROUTING iptables rules.
# In ServicePulse production compose, ONLY Caddy exposes public ports.
# We add a safety warning and ensure Docker daemon config is secure.
echo "[3/7] Hardening Docker daemon configuration..."
DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
mkdir -p /etc/docker

if [ ! -f "${DOCKER_DAEMON_JSON}" ]; then
    cat <<EOF > "${DOCKER_DAEMON_JSON}"
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "20m",
    "max-file": "5"
  },
  "live-restore": true,
  "userland-proxy": false
}
EOF
    echo "Created /etc/docker/daemon.json with log rotation and security settings."
    systemctl restart docker || true
fi

# Step 4: SSH Daemon Hardening
echo "[4/7] Applying SSH security configuration..."
SSHD_CONFIG="/etc/ssh/sshd_config.d/50-servicepulse-hardening.conf"
mkdir -p /etc/ssh/sshd_config.d

cat <<EOF > "${SSHD_CONFIG}"
# ServicePulse Security Hardening Baseline
Port ${SSH_PORT}
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
EOF

# Test SSH config syntax before reloading
if sshd -t; then
    systemctl restart ssh || systemctl restart sshd || true
    echo "SSH daemon reloaded with hardened parameters."
else
    echo "Warning: SSH configuration test failed. Restoring default." >&2
    rm -f "${SSHD_CONFIG}"
fi

# Step 5: Fail2ban Intrusion Prevention
echo "[5/7] Configuring Fail2ban jail..."
FAIL2BAN_JAIL="/etc/fail2ban/jail.local"

cat <<EOF > "${FAIL2BAN_JAIL}"
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
banaction = ufw

[sshd]
enabled = true
port = ${SSH_PORT}
mode = aggressive
EOF

systemctl enable fail2ban
systemctl restart fail2ban

# Step 6: Enable Automatic Security Updates
echo "[6/7] Enabling unattended security upgrades..."
cat <<EOF > /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
systemctl enable unattended-upgrades
systemctl restart unattended-upgrades

# Step 7: Kernel Network Hardening (sysctl)
echo "[7/7] Applying kernel sysctl hardening..."
SYSCTL_CONF="/etc/sysctl.d/99-servicepulse-security.conf"

cat <<EOF > "${SYSCTL_CONF}"
# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# IP Spoofing and Redirect protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Ignore ICMP broadcast requests
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
EOF

sysctl -p "${SYSCTL_CONF}" || true

echo "======================================================================"
echo " Ubuntu Server Security Hardening COMPLETED SUCCESSFULLY!"
echo "======================================================================"
