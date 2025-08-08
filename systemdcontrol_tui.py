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
        all_services = self.controller.get_services(user_only=True)
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
        
        help_text = "q:quit r:refresh s:start p:stop e:restart space:status l:logs"
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
            if time.time() - self.last_refresh > 5:
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
            
            except KeyboardInterrupt:
                break
            except curses.error:
                pass