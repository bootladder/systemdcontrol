#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import List, Dict, Any

class Config:
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'systemdcontrol'
        self.config_file = self.config_dir / 'config.json'
        self.default_config = {
            'service_directories': [
                '/etc/systemd/system',
                '/usr/lib/systemd/system',
                '/lib/systemd/system'
            ],
            'recursive_search': True,
            'user_services_only': True,
            'refresh_interval': 5
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        if not self.config_file.exists():
            return self.default_config.copy()
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all required keys exist
                merged_config = self.default_config.copy()
                merged_config.update(config)
                return merged_config
        except (json.JSONDecodeError, IOError):
            return self.default_config.copy()
    
    def save_config(self) -> bool:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except IOError:
            return False
    
    def get_service_directories(self) -> List[str]:
        return self.config.get('service_directories', self.default_config['service_directories'])
    
    def add_service_directory(self, directory: str) -> bool:
        if directory not in self.config['service_directories']:
            self.config['service_directories'].append(directory)
            return self.save_config()
        return True
    
    def remove_service_directory(self, directory: str) -> bool:
        if directory in self.config['service_directories']:
            self.config['service_directories'].remove(directory)
            return self.save_config()
        return True
    
    def set_recursive_search(self, recursive: bool) -> bool:
        self.config['recursive_search'] = recursive
        return self.save_config()
    
    def get_recursive_search(self) -> bool:
        return self.config.get('recursive_search', self.default_config['recursive_search'])
    
    def set_user_services_only(self, user_only: bool) -> bool:
        self.config['user_services_only'] = user_only
        return self.save_config()
    
    def get_user_services_only(self) -> bool:
        return self.config.get('user_services_only', self.default_config['user_services_only'])
    
    def set_refresh_interval(self, interval: int) -> bool:
        if interval > 0:
            self.config['refresh_interval'] = interval
            return self.save_config()
        return False
    
    def get_refresh_interval(self) -> int:
        return self.config.get('refresh_interval', self.default_config['refresh_interval'])
    
    def reset_to_defaults(self) -> bool:
        self.config = self.default_config.copy()
        return self.save_config()
    
    def get_all_service_files(self) -> List[Path]:
        service_files = []
        directories = self.get_service_directories()
        recursive = self.get_recursive_search()
        
        for dir_str in directories:
            dir_path = Path(dir_str)
            if not dir_path.exists():
                continue
                
            if recursive:
                # Recursively find all .service files
                service_files.extend(dir_path.rglob('*.service'))
            else:
                # Only direct children
                service_files.extend(dir_path.glob('*.service'))
        
        return list(set(service_files))  # Remove duplicates