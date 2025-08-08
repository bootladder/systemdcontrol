#!/usr/bin/env python3

import argparse
import subprocess
import sys
import os
from pathlib import Path
import json
from datetime import datetime, timedelta
import re
from config import Config

class SystemdControl:
    def __init__(self):
        self.config = Config()
        self.service_paths = [Path(p) for p in self.config.get_service_directories()]

    def get_services(self, user_only=None):
        if user_only is None:
            user_only = self.config.get_user_services_only()
        
        services = []
        try:
            result = subprocess.run(['systemctl', 'list-unit-files', '--type=service', '--no-pager'], 
                                  capture_output=True, text=True, check=True)
            
            for line in result.stdout.split('\n')[1:]:
                if line.strip() and not line.startswith('UNIT FILE'):
                    parts = line.split()
                    if len(parts) >= 2:
                        service_name = parts[0]
                        if service_name.endswith('.service'):
                            if user_only:
                                # Only include services in configured directories
                                service_file = self.find_service_file(service_name)
                                if service_file and any(service_file.startswith(str(p)) for p in self.service_paths):
                                    services.append(service_name)
                            else:
                                services.append(service_name)
        except subprocess.CalledProcessError:
            pass
        
        return sorted(services)

    def get_service_status(self, service):
        try:
            result = subprocess.run(['systemctl', 'status', service, '--no-pager'], 
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
        for path in self.service_paths:
            if self.config.get_recursive_search():
                # Search recursively
                matches = list(path.rglob(service))
                if matches:
                    return str(matches[0])
            else:
                # Direct path only
                service_file = path / service
                if service_file.exists():
                    return str(service_file)
        return None

    def control_service(self, action, service):
        try:
            result = subprocess.run(['systemctl', action, service], 
                                  capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def get_service_logs(self, service, lines=50):
        try:
            result = subprocess.run(['journalctl', '-u', service, '-n', str(lines), '--no-pager'], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            return ["No logs available or service not found"]

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
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Service control commands
    service_parser = subparsers.add_parser('service', help='Service control commands')
    service_parser.add_argument('action', choices=['list', 'start', 'stop', 'restart', 'status'], 
                               help='Action to perform')
    service_parser.add_argument('service', nargs='?', help='Service name (for start/stop/restart/status)')
    service_parser.add_argument('--all', action='store_true', help='Show all services including inactive')
    service_parser.add_argument('--system', action='store_true', help='Show all system services (not just user-installed)')
    
    # Config commands
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_subparsers = config_parser.add_subparsers(dest='config_action', help='Config actions')
    
    # Config show
    config_subparsers.add_parser('show', help='Show current configuration')
    
    # Config add directory
    add_parser = config_subparsers.add_parser('add-dir', help='Add service directory')
    add_parser.add_argument('directory', help='Directory path to add')
    
    # Config remove directory
    remove_parser = config_subparsers.add_parser('remove-dir', help='Remove service directory')
    remove_parser.add_argument('directory', help='Directory path to remove')
    
    # Config set options
    set_parser = config_subparsers.add_parser('set', help='Set configuration option')
    set_parser.add_argument('option', choices=['recursive', 'user-only', 'refresh-interval'])
    set_parser.add_argument('value', help='Value to set')
    
    # Config reset
    config_subparsers.add_parser('reset', help='Reset configuration to defaults')
    
    # Legacy support - if no subcommand, treat first arg as action
    parser.add_argument('action', nargs='?', help=argparse.SUPPRESS)
    parser.add_argument('service', nargs='?', help=argparse.SUPPRESS)
    parser.add_argument('--all', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--system', action='store_true', help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    controller = SystemdControl()
    
    # Handle config commands
    if args.command == 'config':
        handle_config_command(args, controller)
        return
    
    # Handle service commands or legacy mode
    if args.command == 'service' or args.action:
        action = args.action if hasattr(args, 'action') and args.action else None
        if not action:
            from systemdcontrol_tui import run_tui
            run_tui(controller)
            return
        handle_service_command(action, args, controller)
        return
    
    # Default to TUI mode
    from systemdcontrol_tui import run_tui
    run_tui(controller)

def handle_config_command(args, controller):
    config = controller.config
    
    if args.config_action == 'show':
        print("Current Configuration:")
        print(f"  Service directories: {config.get_service_directories()}")
        print(f"  Recursive search: {config.get_recursive_search()}")
        print(f"  User services only: {config.get_user_services_only()}")
        print(f"  Refresh interval: {config.get_refresh_interval()}s")
        print(f"  Config file: {config.config_file}")
    
    elif args.config_action == 'add-dir':
        if config.add_service_directory(args.directory):
            print(f"Added directory: {args.directory}")
        else:
            print("Failed to save configuration")
            sys.exit(1)
    
    elif args.config_action == 'remove-dir':
        if config.remove_service_directory(args.directory):
            print(f"Removed directory: {args.directory}")
        else:
            print("Failed to save configuration")
            sys.exit(1)
    
    elif args.config_action == 'set':
        success = False
        if args.option == 'recursive':
            success = config.set_recursive_search(args.value.lower() == 'true')
        elif args.option == 'user-only':
            success = config.set_user_services_only(args.value.lower() == 'true')
        elif args.option == 'refresh-interval':
            try:
                success = config.set_refresh_interval(int(args.value))
            except ValueError:
                print("Invalid refresh interval value")
                sys.exit(1)
        
        if success:
            print(f"Set {args.option} to {args.value}")
        else:
            print("Failed to save configuration")
            sys.exit(1)
    
    elif args.config_action == 'reset':
        if config.reset_to_defaults():
            print("Configuration reset to defaults")
        else:
            print("Failed to reset configuration")
            sys.exit(1)

def handle_service_command(action, args, controller):
    if action == 'list':
        services = controller.get_services(user_only=not args.system)
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
    
    elif action in ['start', 'stop', 'restart']:
        if not args.service:
            print(f"Error: service name required for {action}")
            sys.exit(1)
        
        success, output = controller.control_service(action, args.service)
        if success:
            print(f"Service {args.service} {action}ed successfully")
        else:
            print(f"Error {action}ing service {args.service}: {output}")
            sys.exit(1)
    
    elif action == 'status':
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