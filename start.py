import sys
import io
import os
import json
import pygetwindow as gw
import pystray
from pystray import MenuItem as item, Icon
from PIL import Image
from win32gui import GetWindowText, GetForegroundWindow
from requests import post
from datetime import datetime
from time import sleep
import threading
import win32console
import win32gui
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox

# --- config start
SERVER = ''
SECRET = ''
DEVICE_ID = 'PC'
DEVICE_SHOW_NAME = 'MyPC'
CHECK_INTERVAL = 1
BYPASS_SAME_REQUEST = True
SKIPPED_NAMES = ['', '系统托盘溢出窗口。', '新通知', '任务切换', '快速设置', '通知中心', '搜索', 'Flow.Launcher', '任务切换', '屑鲤鱼 似了吗? - Google Chrome', 'Program Manager']
NOT_USING_NAMES = ['Windows 默认锁屏界面']
Url = ''  # 将 URL 初始为空
last_window = ''
running = True
LOG_FONT_SIZE = 12  # 设置日志字体大小
# --- config end

# 配置日志
if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
else:
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding='utf-8')

def send_update():
    global last_window, SERVER, SECRET, Url
    # 如果没有协议部分，自动加上 http://
    if not SERVER.startswith('http://') and not SERVER.startswith('https://'):
        SERVER = 'http://' + SERVER

    Url = f'{SERVER}/device/set'  # 每次发送请求时动态更新 URL

    window = GetWindowText(GetForegroundWindow())
    print(f'--- Window: `{window}`')
    if BYPASS_SAME_REQUEST and window == last_window:
        return
    if window in SKIPPED_NAMES:
        return
    using = window not in NOT_USING_NAMES
    try:
        resp = post(url=Url, json={
            'secret': SECRET,
            'id': DEVICE_ID,
            'show_name': DEVICE_SHOW_NAME,
            'using': using,
            'app_name': window
        }, headers={'Content-Type': 'application/json'})
        print(f'Response: {resp.status_code} - {resp.json()}')
    except Exception as e:
        print(f'Error: {e}')
    last_window = window

def main_loop():
    while running:
        send_update()
        sleep(CHECK_INTERVAL)

def start():
    global running
    running = True
    threading.Thread(target=main_loop, daemon=True).start()

def pause():
    global running
    running = False

def on_exit(icon, item):
    icon.stop()
    sys.exit(0)

def run_tray():
    image = Image.new('RGB', (64, 64), (0, 0, 0))
    menu = (item('退出', on_exit))
    icon = Icon("win_device", image, menu=menu)
    icon.run()

# 配置文件路径
def get_config_path():
    user_name = os.getlogin()  # 获取当前系统用户名
    config_dir = os.path.join(f'C:\\Users\\{user_name}', '.sleepy')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, 'config.json')

def load_config():
    config_path = get_config_path()
    global SERVER, SECRET  # 确保函数内可以修改这些变量
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            SERVER = config.get('SERVER', '')
            SECRET = config.get('SECRET', '')
    if not SERVER:  # 如果配置为空，则给出默认值
        SERVER = 'http://localhost'  # 设置默认 SERVER
    if not SECRET:  # 如果 SECRET 没有配置，则给出默认值
        SECRET = 'defaultsecret'  # 设置默认 SECRET
    print(f"Loaded config: SERVER={SERVER}, SECRET={SECRET}")  # 调试信息

def save_config():
    config_path = get_config_path()
    global SERVER, SECRET
    config = {'SERVER': SERVER, 'SECRET': SECRET}
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print(f"Config saved: SERVER={SERVER}, SECRET={SECRET}")  # 调试信息

# 更新日志函数，超过 100 行时清空日志
def log_message(message):
    # 获取当前日志行数
    lines = log_area.get(1.0, tk.END).splitlines()
    
    # 如果行数超过100行，清空日志
    if len(lines) > 100:
        log_area.delete(1.0, tk.END)  # 清空日志区域
    
    log_area.insert(tk.END, message + "\n")
    log_area.yview(tk.END)

# GUI部分
def create_gui():
    global SERVER, SECRET

    # 加载之前的配置
    load_config()

    root = tk.Tk()
    root.title("sleepy 客户端")
    root.geometry("400x430")  # 增加窗口的垂直高度

    # 日志输出区域
    global log_area
    log_area = scrolledtext.ScrolledText(root, width=70, height=10, wrap=tk.WORD, font=("Arial", LOG_FONT_SIZE))
    log_area.pack(padx=10, pady=10)

    # 将 stdout 重定向到日志区域
    class TextRedirector:
        def __init__(self, widget):
            self.widget = widget

        def write(self, message):
            self.widget.insert(tk.END, message)
            self.widget.yview(tk.END)

        def flush(self):
            pass

    sys.stdout = TextRedirector(log_area)

    # 控制按钮
    frame = tk.Frame(root)
    frame.pack(pady=10)

    start_button = tk.Button(frame, text="开始", command=start)
    start_button.grid(row=0, column=0, padx=5)

    pause_button = tk.Button(frame, text="暂停", command=pause)
    pause_button.grid(row=0, column=1, padx=5)

    # 配置输入框（恢复为单行的 Entry）
    server_label = tk.Label(root, text="Server URL:")
    server_label.pack(pady=5)

    server_entry = tk.Entry(root, width=50)  # 恢复为单行输入框
    server_entry.insert(tk.END, SERVER)
    server_entry.pack(pady=5)

    secret_label = tk.Label(root, text="Secret:")
    secret_label.pack(pady=5)

    secret_entry = tk.Entry(root, width=50, show="*")  # 恢复为单行输入框
    secret_entry.insert(tk.END, SECRET)
    secret_entry.pack(pady=5)

    def save_settings():
        global SERVER, SECRET
        SERVER = server_entry.get()  # 获取单行文本
        SECRET = secret_entry.get()  # 获取单行文本
        
        # 如果没有协议部分，自动加上 http://
        if not SERVER.startswith('http://') and not SERVER.startswith('https://'):
            SERVER = 'http://' + SERVER
        
        save_config()
        messagebox.showinfo("保存", "配置已保存！")

    save_button = tk.Button(root, text="保存配置", command=save_settings)
    save_button.pack(pady=10)

    return root

# 托盘图标和处理
tray_icon = Icon("sleepy_client")
tray_icon.icon = Image.new('RGB', (64, 64), (0, 0, 0))

if __name__ == '__main__':
    threading.Thread(target=main_loop, daemon=True).start()
    gui = create_gui()  # 启动GUI
    threading.Thread(target=run_tray, daemon=True).start()  # 启动任务栏图标
    gui.mainloop()
