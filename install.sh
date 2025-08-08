#!/bin/bash

set -e

INSTALL_DIR="/usr/local/bin"
SCRIPT_NAME="systemdcontrol"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "SystemD Control Installer"
echo "========================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    echo "Please install Python 3: sudo pacman -S python"
    exit 1
fi

# Check if we're on Arch Linux
if [ ! -f /etc/arch-release ]; then
    echo "Warning: This tool was designed for Arch Linux."
    echo "It may work on other systemd-based distributions."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if systemctl is available
if ! command -v systemctl &> /dev/null; then
    echo "Error: systemctl is required but not found."
    echo "This tool requires systemd."
    exit 1
fi

echo "Installing systemdcontrol to $INSTALL_DIR..."

# Create wrapper script
sudo tee "$INSTALL_DIR/$SCRIPT_NAME" > /dev/null << EOF
#!/bin/bash
exec python3 "$SCRIPT_DIR/systemdcontrol.py" "\$@"
EOF

# Make it executable
sudo chmod +x "$INSTALL_DIR/$SCRIPT_NAME"

# Create symlink for TUI mode
sudo ln -sf "$INSTALL_DIR/$SCRIPT_NAME" "$INSTALL_DIR/${SCRIPT_NAME}-tui" 2>/dev/null || true

echo "Installation complete!"
echo ""
echo "Usage:"
echo "  $SCRIPT_NAME               # Launch TUI mode"
echo "  $SCRIPT_NAME list          # List user services"
echo "  $SCRIPT_NAME status <svc>  # Show service status"
echo "  $SCRIPT_NAME start <svc>   # Start service"
echo "  $SCRIPT_NAME stop <svc>    # Stop service"
echo "  $SCRIPT_NAME restart <svc> # Restart service"
echo ""
echo "TUI Controls:"
echo "  ↑/↓ or j/k  - Navigate"
echo "  Space       - Show detailed status"
echo "  s           - Start service"
echo "  p           - Stop service"
echo "  e           - Restart service"
echo "  t           - Toggle show inactive services"
echo "  r           - Refresh service list"
echo "  q           - Quit"
echo ""
echo "Note: This tool only manages user systemd services."
echo "Use 'systemctl --user' for the underlying commands."