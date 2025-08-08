#!/usr/bin/env python3

import argparse
import subprocess
import sys
import os
from pathlib import Path
import json
from datetime import datetime, timedelta
import re

class SystemdControl:
    def __init__(self):
        self.user_service_paths = [
            Path.home() / '.config/systemd/user',
            Path('/etc/systemd/user'),
            Path('/usr/lib/systemd/user'),
        ]

    def get_user_services(self):
        services = []
        try:
            result = subprocess.run(['systemctl', '--user', 'list-unit-files', '--type=service', '--no-pager'], 
                                  capture_output=True, text=True, check=True)
            
            for line in result.stdout.split('\n')[1:]:
                if line.strip() and not line.startswith('UNIT FILE'):
                    parts = line.split()
                    if len(parts) >= 2:
                        service_name = parts[0]
                        if service_name.endswith('.service'):
                            services.append(service_name)
        except subprocess.CalledProcessError:
            pass
        
        return sorted(services)

    def get_service_status(self, service):
        try:
            result = subprocess.run(['systemctl', '--user', 'status', service, '--no-pager'], 
                                  capture_output=True, text=True)
            
            status_info = {
                'name': service,
                'active': False,
                'enabled': False,
                'main_pid': None,
                'memory': None,
                'since': None,
                'description': '',
                'file_path': self.find_service_file(service)
            }
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'Active:' in line:
                    status_info['active'] = 'active (running)' in line
                    if 'since' in line:
                        since_match = re.search(r'since (.+?)(?:;|$)', line)
                        if since_match:
                            status_info['since'] = since_match.group(1).strip()
                elif 'Loaded:' in line:
                    status_info['enabled'] = 'enabled' in line
                elif 'Main PID:' in line:
                    pid_match = re.search(r'Main PID: (\d+)', line)
                    if pid_match:
                        status_info['main_pid'] = pid_match.group(1)
                elif 'Memory:' in line:
                    memory_match = re.search(r'Memory: (.+?)(?:\s|$)', line)
                    if memory_match:
                        status_info['memory'] = memory_match.group(1)
                elif line and not line.startswith('●') and not any(x in line for x in ['Active:', 'Loaded:', 'Main PID:', 'Memory:']):
                    if not status_info['description']:
                        status_info['description'] = line
            
            return status_info
        except Exception:
            return None

    def find_service_file(self, service):
        for path in self.user_service_paths:
            service_file = path / service
            if service_file.exists():
                return str(service_file)
        return None

    def control_service(self, action, service):
        try:
            result = subprocess.run(['systemctl', '--user', action, service], 
                                  capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr

    def format_uptime(self, since_str):
        if not since_str:
            return "N/A"
        
        try:
            since_time = datetime.strptime(since_str.split(';')[0].strip(), '%a %Y-%m-%d %H:%M:%S %Z')
            uptime = datetime.now() - since_time
            
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return since_str

def main():
    parser = argparse.ArgumentParser(description='User-friendly systemd service control tool')
    parser.add_argument('action', nargs='?', choices=['list', 'start', 'stop', 'restart', 'status', 'tui'], 
                       help='Action to perform')
    parser.add_argument('service', nargs='?', help='Service name (for start/stop/restart/status)')
    parser.add_argument('--all', action='store_true', help='Show all services including inactive')
    
    args = parser.parse_args()
    
    controller = SystemdControl()
    
    if not args.action or args.action == 'tui':
        from systemdcontrol_tui import run_tui
        run_tui(controller)
        return
    
    if args.action == 'list':
        services = controller.get_user_services()
        print(f"{'SERVICE':<30} {'STATUS':<10} {'ENABLED':<8} {'UPTIME':<15} {'FILE PATH'}")
        print("-" * 90)
        
        for service in services:
            status = controller.get_service_status(service)
            if status:
                if not args.all and not status['active']:
                    continue
                    
                status_str = 'active' if status['active'] else 'inactive'
                enabled_str = 'enabled' if status['enabled'] else 'disabled'
                uptime = controller.format_uptime(status['since'])
                file_path = status['file_path'] or 'system'
                
                print(f"{service:<30} {status_str:<10} {enabled_str:<8} {uptime:<15} {file_path}")
    
    elif args.action in ['start', 'stop', 'restart']:
        if not args.service:
            print(f"Error: service name required for {args.action}")
            sys.exit(1)
        
        success, output = controller.control_service(args.action, args.service)
        if success:
            print(f"Service {args.service} {args.action}ed successfully")
        else:
            print(f"Error {args.action}ing service {args.service}: {output}")
            sys.exit(1)
    
    elif args.action == 'status':
        if not args.service:
            print("Error: service name required for status")
            sys.exit(1)
        
        status = controller.get_service_status(args.service)
        if status:
            print(f"Service: {status['name']}")
            print(f"Description: {status['description']}")
            print(f"Status: {'active' if status['active'] else 'inactive'}")
            print(f"Enabled: {'yes' if status['enabled'] else 'no'}")
            print(f"Since: {status['since'] or 'N/A'}")
            print(f"Uptime: {controller.format_uptime(status['since'])}")
            print(f"Main PID: {status['main_pid'] or 'N/A'}")
            print(f"Memory: {status['memory'] or 'N/A'}")
            print(f"Service file: {status['file_path'] or 'system location'}")
        else:
            print(f"Service {args.service} not found")
            sys.exit(1)

if __name__ == '__main__':
    main()