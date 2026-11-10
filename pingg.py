import customtkinter as ctk
import subprocess
import platform
import threading
import queue
import re
import time
from collections import deque


# -----------------------------
# تنظیمات ظاهری برنامه
# -----------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PingMonitor(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("pingman • Network Ping Monitor")
        self.geometry("1050x680")
        self.minsize(900, 600)

        self.running = False
        self.ping_thread = None
        self.result_queue = queue.Queue()

        self.pings = deque(maxlen=60)
        self.sent = 0
        self.received = 0
        self.lost = 0

        self._build_ui()
        self.after(100, self._process_queue)
        self.protocol("WM_DELETE_WINDOW", self._close)

    # -----------------------------
    # ساخت رابط کاربری
    # -----------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # سربرگ
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="#111827")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="ping man",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#60A5FA"
        ).grid(row=0, column=0, padx=(28, 8), pady=(18, 0), sticky="w")

        ctk.CTkLabel(
            header,
            text="NETWORK PING MONITOR created by mahdi alizadeh ( amoaliz )",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#9CA3AF"
        ).grid(row=1, column=0, padx=(30, 8), pady=(0, 18), sticky="w")

        self.status_label = ctk.CTkLabel(
            header,
            text="●  READY",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#9CA3AF"
        )
        self.status_label.grid(row=0, column=2, rowspan=2, padx=30)

        # نوار انتخاب مقصد
        target = ctk.CTkFrame(self, fg_color="transparent")
        target.grid(row=1, column=0, sticky="ew", padx=28, pady=22)
        target.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            target,
            text="TARGET",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#9CA3AF"
        ).grid(row=0, column=0, padx=(0, 12))

        self.host_entry = ctk.CTkEntry(
            target,
            height=42,
            placeholder_text="8.8.8.8 or google.com",
            font=ctk.CTkFont(size=14)
        )
        self.host_entry.insert(0, "8.8.8.8")
        self.host_entry.grid(row=0, column=1, sticky="ew")

        self.start_button = ctk.CTkButton(
            target,
            text="▶  START",
            width=125,
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.start_ping
        )
        self.start_button.grid(row=0, column=2, padx=(12, 0))

        self.stop_button = ctk.CTkButton(
            target,
            text="■  STOP",
            width=110,
            height=42,
            fg_color="#374151",
            hover_color="#4B5563",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.stop_ping,
            state="disabled"
        )
        self.stop_button.grid(row=0, column=3, padx=(8, 0))

        # محتوای اصلی
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=2, column=0, sticky="nsew", padx=28, pady=(0, 25))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(1, weight=1)

        # کارت پینگ فعلی
        current_card = ctk.CTkFrame(
            content, corner_radius=18, fg_color="#111827"
        )
        current_card.grid(
            row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 12)
        )

        ctk.CTkLabel(
            current_card,
            text="CURRENT LATENCY",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#9CA3AF"
        ).pack(pady=(20, 0))

        self.ping_value = ctk.CTkLabel(
            current_card,
            text="— ms",
            font=ctk.CTkFont(size=42, weight="bold"),
            text_color="#60A5FA"
        )
        self.ping_value.pack(pady=(4, 20))

        # کارت‌های آمار
        stats = ctk.CTkFrame(content, corner_radius=18, fg_color="#111827")
        stats.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        stats.grid_columnconfigure((0, 1), weight=1)
        stats.grid_rowconfigure((0, 1), weight=1)

        self.stat_sent = self._create_stat(stats, "SENT", "0", 0, 0)
        self.stat_received = self._create_stat(stats, "RECEIVED", "0", 0, 1)
        self.stat_lost = self._create_stat(stats, "LOST", "0", 1, 0)
        self.stat_avg = self._create_stat(stats, "AVERAGE", "—", 1, 1)

        # کنسول داخل خود برنامه
        console_frame = ctk.CTkFrame(
            content, corner_radius=18, fg_color="#0B1120"
        )
        console_frame.grid(
            row=0, column=1, rowspan=2, sticky="nsew", padx=(10, 0)
        )

        ctk.CTkLabel(
            console_frame,
            text="LIVE OUTPUT",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#9CA3AF"
        ).pack(anchor="w", padx=20, pady=(18, 8))

        self.console = ctk.CTkTextbox(
            console_frame,
            corner_radius=12,
            fg_color="#050A13",
            text_color="#D1FAE5",
            font=("Consolas", 12),
            wrap="none"
        )
        self.console.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self._log("NEXUS Network Monitor initialized...")
        self._log("Target: 8.8.8.8")
        self._log("Press START to begin continuous ping.")
        self._log("")

    def _create_stat(self, parent, title, value, row, column):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(
            row=row, column=column, sticky="nsew", padx=15, pady=18
        )

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#6B7280"
        ).pack()

        value_label = ctk.CTkLabel(
            frame,
            text=value,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#E5E7EB"
        )
        value_label.pack(pady=(5, 0))
        return value_label

    # -----------------------------
    # شروع Ping
    # -----------------------------
    def start_ping(self):
        if self.running:
            return

        host = self.host_entry.get().strip()
        if not host:
            self._log("ERROR: Target cannot be empty.")
            return

        self.running = True
        self.sent = 0
        self.received = 0
        self.lost = 0
        self.pings.clear()

        self.stat_sent.configure(text="0")
        self.stat_received.configure(text="0")
        self.stat_lost.configure(text="0")
        self.stat_avg.configure(text="—")
        self.ping_value.configure(text="— ms", text_color="#60A5FA")

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.host_entry.configure(state="disabled")
        self.status_label.configure(
            text="●  MONITORING", text_color="#34D399"
        )

        self._log(f"--- Started continuous ping to {host} ---")

        self.ping_thread = threading.Thread(
            target=self._ping_loop,
            args=(host,),
            daemon=True
        )
        self.ping_thread.start()

    # -----------------------------
    # توقف Ping
    # -----------------------------
    def stop_ping(self):
        self.running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.host_entry.configure(state="normal")
        self.status_label.configure(
            text="●  STOPPED", text_color="#F59E0B"
        )
        self._log("--- Monitoring stopped ---")

    # -----------------------------
    # حلقه اجرای Ping در پس‌زمینه
    # -----------------------------
    def _ping_loop(self, host):
        is_windows = platform.system().lower() == "windows"

        while self.running:
            if is_windows:
                command = ["ping", "-n", "1", "-w", "1000", host]
            else:
                command = ["ping", "-c", "1", "-W", "1", host]

            try:
                # در ویندوز، پنجره کنسول جداگانه برای ping باز نمی‌شود.
                run_options = {
                    "capture_output": True,
                    "text": True,
                    "timeout": 3,
                    "errors": "replace"
                }

                if is_windows:
                    run_options["creationflags"] = subprocess.CREATE_NO_WINDOW

                start_time = time.perf_counter()
                result = subprocess.run(command, **run_options)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                output = (result.stdout or "") + (result.stderr or "")

                # استخراج زمان پاسخ از خروجی ping ویندوز یا لینوکس
                match = re.search(
                    r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms",
                    output,
                    re.IGNORECASE
                )

                if result.returncode == 0:
                    if match:
                        ping_ms = float(match.group(1))
                    else:
                        ping_ms = elapsed_ms

                    self.result_queue.put(("success", ping_ms))
                else:
                    self.result_queue.put(("timeout", "Request timed out"))

            except subprocess.TimeoutExpired:
                self.result_queue.put(("timeout", "Ping process timed out"))
            except FileNotFoundError:
                self.result_queue.put(
                    ("error", "Ping command was not found on this system.")
                )
                break
            except Exception as error:
                self.result_queue.put(("error", str(error)))
                break

            # فاصله زمانی بین درخواست‌ها
            for _ in range(10):
                if not self.running:
                    break
                time.sleep(0.1)

        self.result_queue.put(("finished", None))

    # -----------------------------
    # دریافت نتیجه‌ها در نخ رابط کاربری
    # -----------------------------
    def _process_queue(self):
        try:
            while True:
                result_type, value = self.result_queue.get_nowait()

                if result_type == "success":
                    self.sent += 1
                    self.received += 1
                    self.pings.append(value)
                    self._update_success(value)

                elif result_type == "timeout":
                    self.sent += 1
                    self.lost += 1
                    self._update_timeout(str(value))

                elif result_type == "error":
                    self._log(f"ERROR: {value}")
                    self.stop_ping()

                elif result_type == "finished":
                    pass

        except queue.Empty:
            pass

        if self.winfo_exists():
            self.after(100, self._process_queue)

    # -----------------------------
    # به‌روزرسانی رابط کاربری
    # -----------------------------
    def _update_success(self, ping):
        self.ping_value.configure(
            text=f"{ping:.0f} ms", text_color="#34D399"
        )

        average = sum(self.pings) / len(self.pings)

        self.stat_sent.configure(text=str(self.sent))
        self.stat_received.configure(text=str(self.received))
        self.stat_lost.configure(text=str(self.lost))
        self.stat_avg.configure(text=f"{average:.0f} ms")

        self.status_label.configure(
            text="●  ONLINE", text_color="#34D399"
        )

        self._log(
            f"[{time.strftime('%H:%M:%S')}] Reply from target  "
            f"time={ping:.1f}ms"
        )

    def _update_timeout(self, message):
        self.ping_value.configure(
            text="TIMEOUT", text_color="#F87171"
        )

        self.stat_sent.configure(text=str(self.sent))
        self.stat_received.configure(text=str(self.received))
        self.stat_lost.configure(text=str(self.lost))

        self.status_label.configure(
            text="●  PACKET LOST", text_color="#F87171"
        )

        self._log(f"[{time.strftime('%H:%M:%S')}] {message}")

    # -----------------------------
    # نوشتن در کنسول داخلی برنامه
    # -----------------------------
    def _log(self, message):
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    # -----------------------------
    # بستن امن برنامه
    # -----------------------------
    def _close(self):
        self.running = False
        self.destroy()


if __name__ == "__main__":
    app = PingMonitor()
    app.mainloop()
