"""
ADXRay Game Spy - 图形界面 (Tkinter)
小白用户友好，双击运行
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from adxray_spy_core import ADXRaySpy, ensure_playwright_browsers


class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.update()

    def flush(self):
        pass


class ADXRaySpyGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("ADXRay Game Spy v1.0")
        self.window.geometry("680x580")
        self.window.resizable(False, False)

        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 680) // 2
        y = (self.window.winfo_screenheight() - 580) // 2
        self.window.geometry(f"+{x}+{y}")

        self.session_name = "adx"
        self.spy = None
        self.login_status = False
        self.output_dir = str(Path.cwd() / "output")

        self._build_ui()

    def _build_ui(self):
        title = tk.Label(self.window, text="ADXRay Game Spy",
                         font=("Microsoft YaHei", 16, "bold"), fg="#1a73e8")
        title.pack(pady=(15, 5))
        subtitle = tk.Label(self.window,
                            text="Enter game name -> auto extract ADXRay ad data",
                            font=("Microsoft YaHei", 9), fg="#666")
        subtitle.pack(pady=(0, 15))

        frame = ttk.Frame(self.window, padding=10)
        frame.pack(fill="x", padx=20)

        ttk.Label(frame, text="Game:", font=("Microsoft YaHei", 10)).grid(
            row=0, column=0, sticky="w", pady=5)
        self.game_entry = ttk.Entry(frame, font=("Microsoft YaHei", 11), width=40)
        self.game_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=(5, 0))
        self.game_entry.focus()

        ttk.Label(frame, text="Output:", font=("Microsoft YaHei", 10)).grid(
            row=1, column=0, sticky="w", pady=5)
        self.dir_var = tk.StringVar(value=self.output_dir)
        dir_entry = ttk.Entry(frame, textvariable=self.dir_var,
                              font=("Microsoft YaHei", 9), width=30)
        dir_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=(5, 0))
        ttk.Button(frame, text="Browse", command=self._browse_dir, width=8).grid(
            row=1, column=2, padx=(5, 0))

        self.status_frame = ttk.LabelFrame(self.window, text="Login Status", padding=5)
        self.status_frame.pack(fill="x", padx=30, pady=10)

        status_row = ttk.Frame(self.status_frame)
        status_row.pack(fill="x")

        self.status_icon = tk.Label(status_row, text="*", fg="#999",
                                    font=("Microsoft YaHei", 14))
        self.status_icon.pack(side="left", padx=(5, 5))
        self.status_label = tk.Label(status_row, text="Not checked", fg="#666",
                                     font=("Microsoft YaHei", 9))
        self.status_label.pack(side="left")

        ttk.Button(status_row, text="Check Login",
                   command=self._check_login, width=15).pack(side="right", padx=5)
        ttk.Button(status_row, text="Re-login",
                   command=self._re_login, width=12).pack(side="right", padx=5)

        self.run_btn = ttk.Button(
            self.window, text=" Start Extract",
            command=self._start_extract,
            style="run.TButton",
        )
        self.run_btn.pack(pady=(5, 10))
        style = ttk.Style()
        style.configure("run.TButton", font=("Microsoft YaHei", 12, "bold"), padding=8)

        log_label = tk.Label(self.window, text="Log", font=("Microsoft YaHei", 9), fg="#666")
        log_label.pack(anchor="w", padx=30)

        self.log_text = scrolledtext.ScrolledText(
            self.window, height=14, width=80,
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            state="normal",
        )
        self.log_text.pack(fill="both", padx=30, pady=(0, 15), expand=True)

        sys.stdout = RedirectText(self.log_text)

        bottom = ttk.Frame(self.window)
        bottom.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(
            bottom,
            text="Requires ADXRay account | First run auto-downloads Chromium",
            font=("Microsoft YaHei", 8), fg="#999",
        ).pack(side="left")

        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.output_dir)
        if d:
            self.output_dir = d
            self.dir_var.set(d)

    def _log(self, msg):
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {msg}")

    def _safe_msgbox(self, func, title, msg):
        """在主线程弹消息框（线程安全）"""
        import queue
        q = queue.Queue()
        def _do():
            try:
                q.put(func(title, msg))
            except:
                q.put(None)
        self.window.after(0, _do)
        return q.get()

    def _ensure_browser_closed(self):
        """安全关闭上一个浏览器，释放 user_data_dir"""
        old = self.spy
        self.spy = None
        if old:
            try:
                old.close()
            except Exception:
                pass
        # 强制清理残留进程
        import subprocess, time
        try:
            dir_str = str(Path.home() / ".adxray_spy").replace("'", "''")
            subprocess.run(
                ['wmic', 'process', 'where',
                 f"name='chrome.exe' and commandline like '%{dir_str}%'",
                 'delete'],
                capture_output=True, timeout=10
            )
        except Exception:
            pass
        time.sleep(1.5)

    def _update_status(self, logged_in, msg=""):
        self.login_status = logged_in
        if logged_in:
            self.status_icon.config(text="*", fg="#4caf50")
            self.status_label.config(text=f"Logged in {msg}", fg="#4caf50")
        else:
            self.status_icon.config(text="*", fg="#f44336")
            self.status_label.config(text=f"Not logged in {msg}", fg="#f44336")

    def _check_login(self):
        def task():
            self._ensure_browser_closed()
            self._log("Checking login status...")
            try:
                ensure_playwright_browsers()
                spy = ADXRaySpy(self.session_name)
                self.spy = spy
                spy.launch(headless=True)
                ok = spy.check_login()
                spy.close()
                if self.spy is spy:
                    self.spy = None
                if ok:
                    self._update_status(True, "(session valid)")
                    self._log("Login OK")
                else:
                    self._update_status(False)
                    self._log("Not logged in, click Re-login")
            except Exception as e:
                self._update_status(False)
                self._log(f"Check failed: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _re_login(self):
        def task():
            self._ensure_browser_closed()
            self._log("Opening browser for login...")
            self._log("Please log into ADXRay in the browser window")
            try:
                ensure_playwright_browsers()
                spy = ADXRaySpy(self.session_name)
                self.spy = spy
                spy.launch(headless=False)
                ok = spy.wait_for_login()
                spy.close()
                if self.spy is spy:
                    self.spy = None
                if ok:
                    self._update_status(True, "(logged in)")
                    self._log("Login success!")
                else:
                    self._update_status(False)
                    self._log("Login timeout")
            except Exception as e:
                self._log(f"Login error: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _start_extract(self):
        raw = self.game_entry.get().strip()
        if not raw:
            messagebox.showwarning("Hint", "Please enter at least one game name")
            return

        game_names = [g.strip() for g in raw.replace("，", ",").split(",") if g.strip()]
        if not game_names:
            messagebox.showwarning("Hint", "Please enter at least one game name")
            return

        total = len(game_names)
        self.run_btn.config(state="disabled", text="Extracting...")
        self._log(f"\n{'='*50}")
        self._log(f"Games ({total}): {', '.join(game_names)}")
        self._log(f"{'='*50}")

        def task():
            results = []
            try:
                self._ensure_browser_closed()
                ensure_playwright_browsers()
                spy = ADXRaySpy(self.session_name)
                self.spy = spy
                spy.launch(headless=False)

                if not spy.check_login():
                    self._log("Need ADXRay login...")
                    if not spy.wait_for_login():
                        raise Exception("Login timeout")
                    self._update_status(True)

                for i, game in enumerate(game_names, 1):
                    self._log(f"\n{'─'*50}")
                    self._log(f"[{i}/{total}] Processing: {game}")
                    self._log(f"{'─'*50}")
                    try:
                        self._log(f"Searching: {game}")
                        products = spy.get_product_from_search(game)
                        if not products:
                            self._log(f"Game not found: {game}")
                            results.append((game, "not found", None))
                            continue

                        ids = ", ".join(p["id"] for p in (products if isinstance(products, list) else [products]))
                        self._log(f"Target IDs: {ids}")

                        data = spy.extract_all(products)

                        output = Path(self.output_dir)
                        output.mkdir(parents=True, exist_ok=True)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        report_path = spy.generate_report(
                            data, str(output / f"{game}_{ts}_report.txt"))

                        self._log(f"Done! Report: {report_path}")
                        results.append((game, "ok", report_path))
                    except Exception as e:
                        self._log(f"Error processing '{game}': {e}")
                        results.append((game, "error", str(e)))

                # Summary
                ok_count = sum(1 for r in results if r[1] == "ok")
                self._log(f"\n{'='*50}")
                self._log(f"All done! {ok_count}/{total} succeeded")
                self._log(f"{'='*50}")
                ok_paths = [r[2] for r in results if r[1] == "ok"]
                fail_names = [r[0] for r in results if r[1] != "ok"]
                msg = f"Complete! {ok_count}/{total} succeeded\n"
                if ok_paths:
                    msg += f"\nReports:\n" + "\n".join(ok_paths)
                if fail_names:
                    msg += f"\n\nFailed: {', '.join(fail_names)}"
                self._safe_msgbox(messagebox.showinfo, "Summary", msg)

            except Exception as e:
                self._log(f"Error: {e}")
                self._safe_msgbox(messagebox.showerror, "Error", str(e))
            finally:
                if self.spy:
                    self.spy.close()
                    self.spy = None
                self.run_btn.config(state="normal", text="Start Extract")

        threading.Thread(target=task, daemon=True).start()

    def _on_close(self):
        if self.spy:
            self.spy.close()
        sys.stdout = sys.__stdout__
        self.window.destroy()

    def run(self):
        self.window.mainloop()


def main():
    app = ADXRaySpyGUI()
    app.run()


if __name__ == "__main__":
    main()
