#!/usr/bin/env python3

import curses
import subprocess
import time
from datetime import datetime

def run_tui(controller):
    try:
        curses.wrapper(lambda stdscr: TUI(stdscr, controller).run())
    except KeyboardInterrupt:
        pass

class TUI:
    def __init__(self, stdscr, controller):
        self.stdscr = stdscr
        self.controller = controller
        self.current_selection = 0
        self.services = []
        self.last_refresh = 0
        
        curses.curs_set(0)
        self.init_colors()
        
    def init_colors(self):
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # active
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # inactive
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # warning
            curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)   # header
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)   # selected
    
    def refresh_services(self):
        user_only = self.controller.config.get_user_services_only()
        all_services = self.controller.get_services(user_only=user_only)
        self.services = []
        
        for service in all_services:
            status = self.controller.get_service_status(service)
            if status:
                self.services.append(status)
        
        self.last_refresh = time.time()
    
    def draw_header(self):
        height, width = self.stdscr.getmaxyx()
        
        title = "SystemD Control - User Services"
        self.stdscr.addstr(0, (width - len(title)) // 2, title, 
                          curses.color_pair(4) | curses.A_BOLD)
        
        help_text = "q:quit r:refresh s:start p:stop e:restart space:status l:logs c:config"
        if len(help_text) < width:
            self.stdscr.addstr(1, (width - len(help_text)) // 2, help_text)
        
        filter_text = "Showing: All your services"
        self.stdscr.addstr(2, 2, filter_text, curses.color_pair(3))
        
        self.stdscr.addstr(4, 2, "SERVICE", curses.A_BOLD)
        self.stdscr.addstr(4, 32, "STATUS", curses.A_BOLD)
        self.stdscr.addstr(4, 42, "ENABLED", curses.A_BOLD)
        self.stdscr.addstr(4, 52, "UPTIME", curses.A_BOLD)
        self.stdscr.addstr(4, 68, "MEMORY", curses.A_BOLD)
        
        self.stdscr.hline(5, 2, '-', width - 4)
    
    def draw_services(self):
        height, width = self.stdscr.getmaxyx()
        start_row = 6
        max_services = height - start_row - 2
        
        if self.current_selection >= len(self.services):
            self.current_selection = max(0, len(self.services) - 1)
        
        for i, service in enumerate(self.services[:max_services]):
            row = start_row + i
            
            name = service['name'][:28]
            status_text = 'active' if service['active'] else 'inactive'
            enabled_text = 'yes' if service['enabled'] else 'no'
            uptime = self.controller.format_uptime(service['since'])[:14]
            memory = service['memory'][:8] if service['memory'] else 'N/A'
            
            color = curses.color_pair(1) if service['active'] else curses.color_pair(2)
            attr = curses.A_REVERSE if i == self.current_selection else 0
            
            if i == self.current_selection:
                self.stdscr.addstr(row, 1, f" {name:<28} {status_text:<8} {enabled_text:<6} {uptime:<14} {memory:<8} ", 
                                 curses.color_pair(5) | curses.A_BOLD)
            else:
                self.stdscr.addstr(row, 2, name, color | attr)
                self.stdscr.addstr(row, 32, status_text, color | attr)
                self.stdscr.addstr(row, 42, enabled_text, attr)
                self.stdscr.addstr(row, 52, uptime, attr)
                self.stdscr.addstr(row, 68, memory, attr)
    
    def show_status_detail(self, service_status):
        height, width = self.stdscr.getmaxyx()
        
        popup_height = 12
        popup_width = min(80, width - 4)
        start_y = (height - popup_height) // 2
        start_x = (width - popup_width) // 2
        
        popup = curses.newwin(popup_height, popup_width, start_y, start_x)
        popup.box()
        
        popup.addstr(1, 2, f"Service: {service_status['name']}", curses.A_BOLD)
        popup.addstr(2, 2, f"Description: {service_status['description'][:popup_width-15]}")
        popup.addstr(3, 2, f"Status: {'active' if service_status['active'] else 'inactive'}")
        popup.addstr(4, 2, f"Enabled: {'yes' if service_status['enabled'] else 'no'}")
        popup.addstr(5, 2, f"Since: {service_status['since'] or 'N/A'}")
        popup.addstr(6, 2, f"Uptime: {self.controller.format_uptime(service_status['since'])}")
        popup.addstr(7, 2, f"Main PID: {service_status['main_pid'] or 'N/A'}")
        popup.addstr(8, 2, f"Memory: {service_status['memory'] or 'N/A'}")
        popup.addstr(9, 2, f"Service file: {service_status['file_path'] or 'system location'}")
        
        popup.addstr(popup_height - 2, 2, "Press any key to continue...", curses.A_DIM)
        
        popup.refresh()
        popup.getch()
    
    def show_message(self, message, is_error=False):
        height, width = self.stdscr.getmaxyx()
        
        msg_height = 5
        msg_width = min(len(message) + 6, width - 4)
        start_y = (height - msg_height) // 2
        start_x = (width - msg_width) // 2
        
        msg_win = curses.newwin(msg_height, msg_width, start_y, start_x)
        msg_win.box()
        
        color = curses.color_pair(2) if is_error else curses.color_pair(1)
        msg_win.addstr(2, 3, message[:msg_width-6], color | curses.A_BOLD)
        msg_win.addstr(3, 3, "Press any key to continue...")
        
        msg_win.refresh()
        msg_win.getch()
    
    def show_brief_message(self, message):
        height, width = self.stdscr.getmaxyx()
        
        # Show message in status line briefly
        self.stdscr.addstr(height - 1, 2, message[:width-4], curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.refresh()
        time.sleep(0.3)
        
        # Clear the message
        self.stdscr.addstr(height - 1, 2, " " * (width - 4))
        self.stdscr.refresh()
    
    def show_service_logs(self, service_status):
        service_name = service_status['name']
        logs = self.controller.get_service_logs(service_name, lines=100)
        
        height, width = self.stdscr.getmaxyx()
        
        # Create a full-screen log viewer
        log_win = curses.newwin(height - 2, width - 2, 1, 1)
        log_win.box()
        
        # Header
        title = f"Logs for {service_name} (↑/↓ scroll, q to close)"
        log_win.addstr(1, 2, title[:width-6], curses.A_BOLD)
        log_win.hline(2, 1, '-', width - 4)
        
        # Calculate display area
        display_height = height - 6  # Leave room for box, header, and controls
        scroll_pos = max(0, len(logs) - display_height)  # Start at bottom
        
        while True:
            log_win.clear()
            log_win.box()
            log_win.addstr(1, 2, title[:width-6], curses.A_BOLD)
            log_win.hline(2, 1, '-', width - 4)
            
            # Show logs
            for i in range(display_height):
                line_idx = scroll_pos + i
                if line_idx < len(logs):
                    log_line = logs[line_idx][:width-6]  # Truncate long lines
                    try:
                        log_win.addstr(3 + i, 2, log_line)
                    except curses.error:
                        pass  # Ignore if we can't draw at this position
            
            # Show scroll indicator
            if len(logs) > display_height:
                scroll_info = f"Line {scroll_pos + 1}-{min(scroll_pos + display_height, len(logs))} of {len(logs)}"
                log_win.addstr(height - 3, width - len(scroll_info) - 4, scroll_info, curses.A_DIM)
            
            log_win.refresh()
            
            # Handle input
            key = log_win.getch()
            
            if key == ord('q') or key == 27:  # q or ESC
                break
            elif key == curses.KEY_UP or key == ord('k'):
                scroll_pos = max(0, scroll_pos - 1)
            elif key == curses.KEY_DOWN or key == ord('j'):
                scroll_pos = min(max(0, len(logs) - display_height), scroll_pos + 1)
            elif key == curses.KEY_NPAGE:  # Page Down
                scroll_pos = min(max(0, len(logs) - display_height), scroll_pos + display_height)
            elif key == curses.KEY_PPAGE:  # Page Up
                scroll_pos = max(0, scroll_pos - display_height)
            elif key == curses.KEY_HOME:
                scroll_pos = 0
            elif key == curses.KEY_END:
                scroll_pos = max(0, len(logs) - display_height)
    
    def show_config_screen(self):
        height, width = self.stdscr.getmaxyx()
        config = self.controller.config
        
        config_win = curses.newwin(height - 2, width - 2, 1, 1)
        config_win.box()
        
        title = "Configuration Settings (↑/↓ navigate, Enter to edit, q to close)"
        config_win.addstr(1, 2, title[:width-6], curses.A_BOLD)
        config_win.hline(2, 1, '-', width - 4)
        
        config_options = [
            ("Service Directories", config.get_service_directories()),
            ("Recursive Search", config.get_recursive_search()),
            ("User Services Only", config.get_user_services_only()),
            ("Refresh Interval", f"{config.get_refresh_interval()}s"),
            ("Config File", str(config.config_file))
        ]
        
        selection = 0
        
        while True:
            config_win.clear()
            config_win.box()
            config_win.addstr(1, 2, title[:width-6], curses.A_BOLD)
            config_win.hline(2, 1, '-', width - 4)
            
            for i, (key, value) in enumerate(config_options):
                row = 4 + i * 2
                if row >= height - 4:
                    break
                
                attr = curses.A_REVERSE if i == selection else 0
                config_win.addstr(row, 3, f"{key}:", curses.A_BOLD | attr)
                
                value_str = str(value)
                if isinstance(value, list):
                    value_str = ', '.join(value)
                elif len(value_str) > width - 25:
                    value_str = value_str[:width-28] + "..."
                
                config_win.addstr(row + 1, 5, value_str, attr)
            
            config_win.addstr(height - 4, 3, "Press 'r' to reset to defaults", curses.A_DIM)
            config_win.refresh()
            
            key = config_win.getch()
            
            if key == ord('q') or key == 27:
                break
            elif key == curses.KEY_UP or key == ord('k'):
                selection = max(0, selection - 1)
            elif key == curses.KEY_DOWN or key == ord('j'):
                selection = min(len(config_options) - 2, selection + 1)  # -1 for config file (read-only)
            elif key == ord('\n') or key == ord('\r'):
                if selection < len(config_options) - 1:  # Don't edit config file path
                    self.edit_config_option(selection, config)
                    # Refresh config options after edit
                    config_options = [
                        ("Service Directories", config.get_service_directories()),
                        ("Recursive Search", config.get_recursive_search()),
                        ("User Services Only", config.get_user_services_only()),
                        ("Refresh Interval", f"{config.get_refresh_interval()}s"),
                        ("Config File", str(config.config_file))
                    ]
            elif key == ord('r'):
                self.reset_config(config)
                config_options = [
                    ("Service Directories", config.get_service_directories()),
                    ("Recursive Search", config.get_recursive_search()),
                    ("User Services Only", config.get_user_services_only()),
                    ("Refresh Interval", f"{config.get_refresh_interval()}s"),
                    ("Config File", str(config.config_file))
                ]
    
    def edit_config_option(self, selection, config):
        if selection == 0:  # Service Directories
            self.edit_service_directories(config)
        elif selection == 1:  # Recursive Search
            current = config.get_recursive_search()
            config.set_recursive_search(not current)
            self.show_brief_message(f"Recursive search: {'enabled' if not current else 'disabled'}")
        elif selection == 2:  # User Services Only
            current = config.get_user_services_only()
            config.set_user_services_only(not current)
            self.show_brief_message(f"User services only: {'enabled' if not current else 'disabled'}")
        elif selection == 3:  # Refresh Interval
            self.edit_refresh_interval(config)
    
    def edit_service_directories(self, config):
        height, width = self.stdscr.getmaxyx()
        
        dir_win = curses.newwin(height - 4, width - 4, 2, 2)
        dir_win.box()
        
        title = "Service Directories (a:add d:delete Enter:done)"
        dir_win.addstr(1, 2, title[:width-8], curses.A_BOLD)
        dir_win.hline(2, 1, '-', width - 8)
        
        directories = config.get_service_directories()[:]
        selection = 0
        
        while True:
            dir_win.clear()
            dir_win.box()
            dir_win.addstr(1, 2, title[:width-8], curses.A_BOLD)
            dir_win.hline(2, 1, '-', width - 8)
            
            for i, directory in enumerate(directories):
                if 3 + i >= height - 6:
                    break
                attr = curses.A_REVERSE if i == selection else 0
                dir_win.addstr(3 + i, 3, directory[:width-10], attr)
            
            dir_win.refresh()
            key = dir_win.getch()
            
            if key == ord('\n') or key == ord('\r') or key == 27:
                # Save changes
                config.config['service_directories'] = directories
                config.save_config()
                break
            elif key == curses.KEY_UP or key == ord('k'):
                selection = max(0, selection - 1)
            elif key == curses.KEY_DOWN or key == ord('j'):
                selection = min(len(directories) - 1, selection + 1)
            elif key == ord('a'):
                new_dir = self.get_text_input("Enter directory path:")
                if new_dir and new_dir not in directories:
                    directories.append(new_dir)
            elif key == ord('d') and directories:
                if selection < len(directories):
                    directories.pop(selection)
                    selection = min(selection, len(directories) - 1)
    
    def edit_refresh_interval(self, config):
        current = config.get_refresh_interval()
        new_interval = self.get_text_input(f"Enter refresh interval in seconds (current: {current}):")
        if new_interval:
            try:
                interval = int(new_interval)
                if interval > 0:
                    config.set_refresh_interval(interval)
                    self.show_brief_message(f"Refresh interval set to {interval}s")
                else:
                    self.show_message("Invalid interval: must be positive", is_error=True)
            except ValueError:
                self.show_message("Invalid interval: must be a number", is_error=True)
    
    def get_text_input(self, prompt):
        height, width = self.stdscr.getmaxyx()
        
        input_height = 5
        input_width = min(60, width - 4)
        start_y = (height - input_height) // 2
        start_x = (width - input_width) // 2
        
        input_win = curses.newwin(input_height, input_width, start_y, start_x)
        input_win.box()
        input_win.addstr(1, 2, prompt[:input_width-4])
        input_win.addstr(3, 2, "> ")
        
        curses.curs_set(1)  # Show cursor
        input_win.refresh()
        
        text = ""
        while True:
            ch = input_win.getch()
            if ch == ord('\n') or ch == ord('\r'):
                break
            elif ch == 27:  # ESC
                text = ""
                break
            elif ch == curses.KEY_BACKSPACE or ch == 127:
                if text:
                    text = text[:-1]
                    input_win.addstr(3, 4 + len(text), " ")
                    input_win.move(3, 4 + len(text))
            elif 32 <= ch <= 126:  # Printable characters
                if len(text) < input_width - 6:
                    text += chr(ch)
                    input_win.addch(3, 4 + len(text) - 1, ch)
            
            input_win.refresh()
        
        curses.curs_set(0)  # Hide cursor
        return text.strip()
    
    def reset_config(self, config):
        if config.reset_to_defaults():
            self.show_brief_message("Configuration reset to defaults")
        else:
            self.show_message("Failed to reset configuration", is_error=True)
    
    def handle_service_action(self, action):
        if not self.services or self.current_selection >= len(self.services):
            return
        
        service = self.services[self.current_selection]
        service_name = service['name']
        
        try:
            self.stdscr.addstr(0, 0, f"Performing {action} on {service_name}...", curses.A_BOLD)
            self.stdscr.refresh()
            
            success, output = self.controller.control_service(action, service_name)
            
            if success:
                self.show_brief_message(f"Service {service_name} {action}ed successfully")
                self.refresh_services()
            else:
                self.show_message(f"Error {action}ing {service_name}: {output}", is_error=True)
        
        except Exception as e:
            self.show_message(f"Error: {str(e)}", is_error=True)
    
    def run(self):
        self.refresh_services()
        
        while True:
            refresh_interval = self.controller.config.get_refresh_interval()
            if time.time() - self.last_refresh > refresh_interval:
                self.refresh_services()
            
            self.stdscr.clear()
            self.draw_header()
            self.draw_services()
            
            height, width = self.stdscr.getmaxyx()
            status_line = f"Services: {len(self.services)} | Selected: {self.current_selection + 1 if self.services else 0}"
            self.stdscr.addstr(height - 1, 2, status_line, curses.A_DIM)
            
            self.stdscr.refresh()
            
            try:
                key = self.stdscr.getch()
                
                if key == ord('q') or key == 27:  # q or ESC
                    break
                
                elif key == ord('r'):
                    self.refresh_services()
                
                
                elif key == curses.KEY_UP or key == ord('k'):
                    self.current_selection = max(0, self.current_selection - 1)
                
                elif key == curses.KEY_DOWN or key == ord('j'):
                    self.current_selection = min(len(self.services) - 1, self.current_selection + 1)
                
                elif key == ord(' '):  # space for status
                    if self.services and self.current_selection < len(self.services):
                        self.show_status_detail(self.services[self.current_selection])
                
                elif key == ord('s'):  # start
                    self.handle_service_action('start')
                
                elif key == ord('p'):  # stop
                    self.handle_service_action('stop')
                
                elif key == ord('e'):  # restart
                    self.handle_service_action('restart')
                
                elif key == ord('l'):  # logs
                    if self.services and self.current_selection < len(self.services):
                        self.show_service_logs(self.services[self.current_selection])
                
                elif key == ord('c'):  # config
                    self.show_config_screen()
                    self.refresh_services()  # Refresh in case config changed
            
            except KeyboardInterrupt:
                break
            except curses.error:
                pass