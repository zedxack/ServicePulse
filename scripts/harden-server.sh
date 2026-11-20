#!/usr/bin/env bash
# ==============================================================================
# ServicePulse - Ubuntu Server Security Hardening Script
# Project: ServicePulse — Enterprise Hybrid RMM & ITSM Platform
# Author: Muhammadyusuf Usmonov
# Target: Ubuntu 24.04 / 22.04 LTS
# ==============================================================================
set -euo pipefail

DRY_RUN=false
ASSUME_YES=false
SSH_PORT=22

for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=true
            ;;
        -y|--yes)
            ASSUME_YES=true
            ;;
        --port=*)
            SSH_PORT="${arg#*=}"
            ;;
        *)
            if [[ "$arg" =~ ^[0-9]+$ ]]; then
                SSH_PORT="$arg"
            fi
            ;;
    esac
done

if [ "$EUID" -ne 0 ] && [ "$DRY_RUN" = false ]; then
    echo "Error: This hardening script must be executed as root (e.g. sudo bash harden-server.sh)" >&2
    exit 1
fi

echo "======================================================================"
echo " ServicePulse Ubuntu Server Security Hardening Pipeline"
echo " Author: Muhammadyusuf Usmonov | "
echo " Target SSH Port: ${SSH_PORT}"
echo " Dry Run Mode:    ${DRY_RUN}"
echo "======================================================================"

# Step 0: Pre-flight SSH Key Check to Prevent Accidental Lockout
echo "[0/7] Auditing existing SSH keys..."
KEY_FOUND=false
CHECK_PATHS=("/root/.ssh/authorized_keys")

for home_auth in /home/*/.ssh/authorized_keys; do
    if [ -f "$home_auth" ]; then
        CHECK_PATHS+=("$home_auth")
    fi
done

for auth_file in "${CHECK_PATHS[@]}"; do
    if [ -s "$auth_file" ]; then
        KEY_FOUND=true
        echo "  [OK] Valid SSH authorized key found in: ${auth_file}"
    fi
done

DISABLE_PASSWORD_AUTH=true
if [ "$KEY_FOUND" = false ]; then
    echo "  [WARNING] No non-empty authorized_keys found in /root/.ssh or /home/*/.ssh!" >&2
    echo "  Disabling PasswordAuthentication without a public key WILL PERMANENTLY LOCK YOU OUT." >&2
    echo "  For safety, PasswordAuthentication will REMAIN ENABLED until you install an SSH key." >&2
    DISABLE_PASSWORD_AUTH=false
fi

if [ "$ASSUME_YES" = false ] && [ "$DRY_RUN" = false ]; then
    read -r -p "Apply hardening configuration to this server? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[yY]([eE][sS])?$ ]]; then
        echo "Hardening aborted by operator."
        exit 0
    fi
fi

if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] Simulating actions (no system changes will be applied):"
    echo "  - Would install: ufw, fail2ban, unattended-upgrades, iptables-persistent, curl, jq"
    echo "  - Would set UFW defaults: deny incoming, allow outgoing, deny routed"
    echo "  - Would allow ports: ${SSH_PORT}/tcp, 80/tcp, 443/tcp, 443/udp"
    echo "  - Would write /etc/docker/daemon.json with log rotation and live-restore"
    echo "  - Would write /etc/ssh/sshd_config.d/50-servicepulse-hardening.conf (PasswordAuthentication: $DISABLE_PASSWORD_AUTH)"
    echo "  - Would configure /etc/fail2ban/jail.local for sshd"
    echo "  - Would configure /etc/apt/apt.conf.d/20auto-upgrades"
    echo "  - Would apply /etc/sysctl.d/99-servicepulse-security.conf"
    echo "Dry run completed successfully."
    exit 0
fi

# Step 1: System Update & Security Packages
echo "[1/7] Updating system packages and installing security tooling..."
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
echo "[2/7] Configuring UFW firewall rules..."
ufw default deny incoming
ufw default allow outgoing
ufw default deny routed

# Allow SSH and Caddy ports
ufw allow "${SSH_PORT}/tcp" comment "SSH Management"
ufw allow 80/tcp comment "Caddy HTTP ACME Challenge"
ufw allow 443/tcp comment "Caddy HTTPS TLS"
ufw allow 443/udp comment "Caddy HTTP/3 QUIC"

echo "y" | ufw enable
ufw status verbose

# Step 3: Hardening Docker Daemon Configuration
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
    echo "Created ${DOCKER_DAEMON_JSON}"
    systemctl restart docker || true
fi

# Step 4: SSH Daemon Hardening
echo "[4/7] Applying SSH security parameters..."
SSHD_CONFIG="/etc/ssh/sshd_config.d/50-servicepulse-hardening.conf"
mkdir -p /etc/ssh/sshd_config.d

PWD_AUTH_VAL="no"
if [ "$DISABLE_PASSWORD_AUTH" = false ]; then
    PWD_AUTH_VAL="yes"
fi

cat <<EOF > "${SSHD_CONFIG}"
# ServicePulse Security Hardening Baseline
Port ${SSH_PORT}
PermitRootLogin prohibit-password
PasswordAuthentication ${PWD_AUTH_VAL}
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
EOF

# Syntax-check before restarting sshd
if sshd -t; then
    systemctl restart ssh || systemctl restart sshd || true
    echo "SSH daemon reloaded successfully."
else
    echo "Warning: SSH configuration syntax test failed. Reverting configuration." >&2
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
echo "[6/7] Enabling unattended upgrades for daily security patches..."
cat <<EOF > /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
systemctl enable unattended-upgrades
systemctl restart unattended-upgrades

# Step 7: Kernel sysctl Network Hardening
echo "[7/7] Applying kernel network hardening..."
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
