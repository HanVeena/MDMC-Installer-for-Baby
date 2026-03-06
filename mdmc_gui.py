import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import os
import urllib.request
import zipfile
import shutil
import threading
import sys

ML_DOWNLOAD_URL = "https://github.com/LavaGang/MelonLoader/releases/download/v0.6.1/MelonLoader.x64.zip"
CA_DOWNLOAD_URL = "https://github.com/MDMods/CustomAlbums/releases/latest/download/CustomAlbums.dll"
CINEMA_DOWNLOAD_URL = "https://github.com/MDMods/Cinema/releases/latest/download/Cinema.dll"

def get_resource_path(relative_path):
    """获取资源的绝对路径。兼容开发环境和 PyInstaller 打包后的临时解压环境"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class MDMCInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MDMC Installer - Muse Dash Mod自动化部署工具")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        
        try:
            icon_path = get_resource_path("icon.ico")
            self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        self.game_dir = None
        
        self.setup_ui()
        
        self.log("===================================================")
        self.log("MDMC Installer 已启动，请确保你已开启VPN！")
        self.log("===================================================")
        
        threading.Thread(target=self.init_checks, daemon=True).start()

    def setup_ui(self):
        btn_frame = tk.Frame(self.root, pady=10)
        btn_frame.pack(fill=tk.X)
        
        self.btn_ml = tk.Button(btn_frame, text="安装/重装 MelonLoader", width=25, command=lambda: self.run_task(self.install_ml))
        self.btn_ml.grid(row=0, column=0, padx=10, pady=5)
        
        self.btn_un = tk.Button(btn_frame, text="卸载 MelonLoader 及所有组件", width=25, command=lambda: self.run_task(self.uninstall_all))
        self.btn_un.grid(row=0, column=1, padx=10, pady=5)
        
        self.btn_mod = tk.Button(btn_frame, text="安装/更新 MOD 组件", width=25, command=lambda: self.run_task(self.install_mods))
        self.btn_mod.grid(row=1, column=0, padx=10, pady=5)
        
        self.btn_path = tk.Button(btn_frame, text="手动选择游戏目录", width=25, command=self.manual_select_path)
        self.btn_path.grid(row=1, column=1, padx=10, pady=5)

        self.log_area = scrolledtext.ScrolledText(self.root, state='disabled', bg='black', fg='white', font=('Consolas', 10))
        self.log_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    def log(self, text):
        """将文字输出到窗口内的日志区"""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def init_checks(self):
        """执行初始化：查代理、查路径"""
        proxies = urllib.request.getproxies()
        if 'http' in proxies or 'https' in proxies:
            self.log(f"[成功] 检测到系统代理配置: {proxies.get('http', 'N/A')}")
        else:
            self.log("[警告] 未检测到系统开启代理，将尝试直接连接（可能导致下载失败）。")

        self.log("\n[信息] 正在自动检测 MuseDash 安装位置...")
        possible_paths = [
            r"SteamLibrary\steamapps\common\Muse Dash",
            r"Steam\steamapps\common\Muse Dash",
            r"Program Files (x86)\Steam\steamapps\common\Muse Dash",
            r"Program Files\Steam\steamapps\common\Muse Dash"
        ]
        
        found = False
        drives = [chr(x) + ":" for x in range(67, 91)] # C: 到 Z:
        for drive in drives:
            for p in possible_paths:
                target_exe = os.path.join(drive + "\\", p, "MuseDash.exe")
                if os.path.exists(target_exe):
                    self.game_dir = os.path.dirname(target_exe)
                    found = True
                    break
            if found: break
            
        if found:
            self.log(f"[成功] 目标游戏路径: {self.game_dir}")
        else:
            self.log("[警告] 未检测到游戏文件位置，请点击上方按钮手动选择 MuseDash.exe！")

    def manual_select_path(self):
        file_path = filedialog.askopenfilename(
            title="请定位并选择 MuseDash.exe",
            filetypes=[("MuseDash.exe", "MuseDash.exe")]
        )
        if file_path:
            self.game_dir = os.path.dirname(file_path)
            self.log(f"[成功] 已手动设置游戏路径: {self.game_dir}")

    def run_task(self, target_func):
        """关键技术：多线程执行，防止主界面卡死"""
        if not self.game_dir:
            messagebox.showerror("错误", "未找到游戏路径，请先手动选择 MuseDash.exe！")
            return
            
        self.set_buttons_state(tk.DISABLED)
        threading.Thread(target=self.thread_wrapper, args=(target_func,), daemon=True).start()

    def thread_wrapper(self, func):
        try:
            func()
        except Exception as e:
            self.log(f"\n[错误] 执行期间发生异常: {str(e)}")
        finally:
            self.set_buttons_state(tk.NORMAL)

    def set_buttons_state(self, state):
        self.btn_ml.config(state=state)
        self.btn_un.config(state=state)
        self.btn_mod.config(state=state)
        self.btn_path.config(state=state)

    def download_file(self, url, dest_path):
        self.log(f"-> 正在请求: {url.split('/')[-1]}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

    def install_ml(self):
        self.log("\n[1/2] 正在通过本地网络下载 MelonLoader v0.6.1... (可能需要一些时间，请耐心等待)")
        temp_zip = os.path.join(os.environ['TEMP'], "MelonLoader.zip")
        try:
            self.download_file(ML_DOWNLOAD_URL, temp_zip)
            self.log("[成功] 下载完成！")
        except Exception as e:
            self.log(f"[错误] 下载失败，请检查VPN。详细信息: {e}")
            return

        self.log("[2/2] 正在解压并部署到游戏目录...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(self.game_dir)
            
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
            
        self.log("[成功] MelonLoader 部署完毕！第一次启动游戏请保持 VPN 开启！")

    def uninstall_all(self):
        self.log("\n[清理] 正在移除 MelonLoader 核心文件及相关文件夹...")
        dirs_to_remove = ["MelonLoader", "Mods", "Plugins", "UserData"]
        files_to_remove = ["version.dll", "winhttp.dll", "NOTICE.txt"]

        for d in dirs_to_remove:
            dp = os.path.join(self.game_dir, d)
            if os.path.exists(dp):
                shutil.rmtree(dp, ignore_errors=True)
                
        for f in files_to_remove:
            fp = os.path.join(self.game_dir, f)
            if os.path.exists(fp):
                try: os.remove(fp)
                except: pass

        self.log("[成功] 已彻底卸载 MelonLoader 及所有MOD组件。")

    def install_mods(self):
        mods_dir = os.path.join(self.game_dir, "Mods")
        ca_dir = os.path.join(self.game_dir, "Custom_Albums")
        
        os.makedirs(mods_dir, exist_ok=True)
        if not os.path.exists(ca_dir):
            os.makedirs(ca_dir)
            self.log("[信息] 已为您自动创建 Custom_Albums 谱面文件夹。")

        self.log("\n[1/2] 正在请求并下载 CustomAlbums.dll ...")
        ca_path = os.path.join(mods_dir, "CustomAlbums.dll")
        try:
            self.download_file(CA_DOWNLOAD_URL, ca_path)
        except Exception as e:
            self.log(f"[错误] CustomAlbums 下载失败: {e}")

        self.log("[2/2] 正在请求并下载 Cinema.dll ...")
        cinema_path = os.path.join(mods_dir, "Cinema.dll")
        try:
            self.download_file(CINEMA_DOWNLOAD_URL, cinema_path)
        except Exception as e:
            self.log(f"[错误] Cinema 下载失败: {e}")

        self.log("[成功] MOD组件部署/更新完成！")

if __name__ == "__main__":
    root = tk.Tk()
    app = MDMCInstallerApp(root)
    root.mainloop()