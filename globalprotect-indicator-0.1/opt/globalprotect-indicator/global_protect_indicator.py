#!/usr/bin/env python3

import os
import sys
import signal
import gi
import subprocess
import time
import threading

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk
import keyring

try:
   from gi.repository import AppIndicator3 as AppIndicator
except:
   from gi.repository import AppIndicator

class GlobalProtectSettings():

    def on_btn_save_clicked(self, data=None):
        self.host = self.builder.get_object("entry_host").get_text()
        self.username = self.builder.get_object("entry_username").get_text()
        self.password = self.builder.get_object("entry_password").get_text()
        print(self.host, self.username, self.password)
        keyring.get_keyring()
        keyring.set_password("gp", "host", self.host)
        keyring.set_password("gp", "username", self.username)
        keyring.set_password("gp", "password", self.password)
        self.window.hide()

    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("/opt/globalprotect-indicator/settings.xml")
        self.window = self.builder.get_object("MainWindow")
        self.window.set_icon_from_file("/opt/globalprotect-indicator/gp_on.png")
        self.builder.connect_signals(self)

        self.host = self.builder.get_object("entry_host")
        self.username = self.builder.get_object("entry_username")
        self.password = self.builder.get_object("entry_password")

        keyring.get_keyring()
        host = keyring.get_password("gp", "host")
        username = keyring.get_password("gp", "username")
        password = keyring.get_password("gp", "password")
        if not password:
            password = ''

        self.host.set_text(host)
        self.username.set_text(username)
        self.password.set_text(password)

        self.window.show_all()
        self.window.show()
    
class Indicator():
    def __init__(self):
        self.app = 'GlobalProtect'
        iconpath = "/opt/globalprotect-indicator/gp_off.png"
        self.connected = False
        self.proc = None
        self.indicator = AppIndicator.Indicator.new(self.app, iconpath, AppIndicator.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)

        self.indicator.set_menu(self.create_menu())

    def create_menu(self):
        menu = Gtk.Menu()

        if self.connected == False:
            connect = Gtk.MenuItem('Connect')
            connect.connect('activate', self.connect)
            menu.append(connect)
            self.indicator.set_icon("/opt/globalprotect-indicator/gp_off.png")
        else:
            disconnect = Gtk.MenuItem('Disconnect')
            disconnect.connect('activate', self.disconnect)
            self.indicator.set_icon("/opt/globalprotect-indicator/gp_on.png")
            menu.append(disconnect)
        
        settings = Gtk.MenuItem('Settings')
        settings.connect('activate', self.show_settings)
        menu.append(settings)

        # separator
        menu_sep = Gtk.SeparatorMenuItem()
        menu.append(menu_sep)

        # quit
        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', self.stop)
        menu.append(item_quit)
        menu.show_all()

        return menu

    def disconnect(self, obj=None):
        os.system("for v in $(ps aux |grep `which openconnect` |grep root |awk '{print $2}'); do pkexec kill -2 $v; done")
        self.connected = False
        self.indicator.set_menu(self.create_menu())

    def connect(self, obj=None):
        keyring.get_keyring()
        host = keyring.get_password("gp", "host")
        username = keyring.get_password("gp", "username")
        password = keyring.get_password("gp", "password")

        if not host or not username or not password:
            self.show_settings()
            return

        t = threading.Thread(target=self.connect_thread)
        t.start()

    def connect_thread(self, obj=None):
        keyring.get_keyring()
        host = keyring.get_password("gp", "host")
        username = keyring.get_password("gp", "username")
        password = keyring.get_password("gp", "password")
        if not password:
            password = ''

        if not username:
            username = 'abcde'

        self.proc = subprocess.Popen([
            'pkexec',
            'openconnect', 
            '-u', 
            username, 
            '--protocol=gp', 
            host, 
            '--passwd-on-stdin'
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        self.proc.stdin.write(password.encode('utf-8'))
        self.proc.stdin.write(b'\n')
        self.proc.stdin.flush()

        for line in iter(self.proc.stdout.readline, ''):
            s = line.decode('utf-8')
            if 'connected' in s and 'mainloop' in s:
                self.connected = True
                self.indicator.set_menu(self.create_menu())

            if 'error' in s:
                self.proc.kill()

            if line == b'':
                self.disconnect()
                break

    def stop(self, source):
        Gtk.main_quit()
        sys.exit(0)

    def show_settings(self, source):
        win = GlobalProtectSettings()
        Gtk.main()

def run_indicator():
    Indicator()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()

def run_settings():
    settings = GlobalProtectSettings()
    settings.window.connect("destroy", Gtk.main_quit)
    Gtk.main()

def test_connect():
    i = Indicator()
    i.connect()

if __name__ == '__main__':
    #run_settings()
    #test_connect()
    run_indicator()
