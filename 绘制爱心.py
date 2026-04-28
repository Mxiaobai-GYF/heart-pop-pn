"""
绘制爱心.py
────────────────────────────────────────────────
阶段 1：用许多随机颜色小窗口（内含可编辑文字）拼出爱心图案
阶段 2：像橡皮擦一样逐渐清除爱心，再在全屏随机位置随机生成窗口
右上角提供一键结束按钮
────────────────────────────────────────────────
依赖：tkinter（Python 标准库，无需额外安装）
"""

import tkinter as tk
import random
import math
import threading
import time

# ──────────────────────────────────────────────
# 全局配置
# ──────────────────────────────────────────────
MINI_W, MINI_H = 36, 22          # 每个小窗口的宽高（缩小以增加密度）
ROWS, COLS     = 55, 80          # 爱心网格点阵尺寸（大幅增加）
HEART_SCALE    = 1.0             # 爱心缩放

SPAWN_INTERVAL = 0.01            # 阶段1：每个小窗口出现间隔(s)（加快）
ERASE_INTERVAL = 0.008           # 阶段2a：清除间隔(s)
RANDOM_INTERVAL= 0.12            # 阶段2b：随机窗口生成间隔(s)
MAX_RANDOM_WIN = 40              # 阶段2b：最多同时存在随机窗口数

# 随机颜色候选（鲜艳系）
PALETTE = [
    "#FF6B6B","#FF8E53","#FFC300","#2ECC71","#1ABC9C",
    "#3498DB","#9B59B6","#E91E63","#00BCD4","#8BC34A",
    "#FF5722","#607D8B","#F06292","#AED581","#4FC3F7",
    "#FFB74D","#BA68C8","#4DB6AC","#DCE775","#FF8A65",
]
#双引号内文字可修改
LOVE_WORDS = [
    "我爱你"
]

all_mini_wins = []   # 所有存活的小窗口
stop_event    = threading.Event()

# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def heart_points(sw, sh, rows=ROWS, cols=COLS):
    """
    轮廓式爱心采样：用参数方程密集采样爱心轮廓上的点，
    以窗口大小为最小间距去重，按 y→x 排序保证从左到右、从上到下出现。
    参数方程：x = 16sin³(t)，y = 13cos(t)-5cos(2t)-2cos(3t)-cos(4t)
    """
    cx, cy = sw // 2, sh // 2

    # 横向缩放减小（从 0.025 改为 0.017），爱心更窄更挺拔
    scale_x = (sw * 0.017) * HEART_SCALE
    scale_y = (sh * 0.028) * HEART_SCALE

    # 密集采样 3000 个点保证轮廓连续
    N = 3000

    raw = []
    for i in range(N):
        t = (i / N) * 2 * math.pi
        hx =  16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2*t)
               - 2 * math.cos(3*t) - math.cos(4*t))
        px = int(cx + hx * scale_x - MINI_W // 2)
        py = int(cy + hy * scale_y - MINI_H // 2)
        raw.append((px, py))

    # 以窗口大小为格子去重
    seen = set()
    pts  = []
    for p in raw:
        key = (round(p[0] / (MINI_W + 2)), round(p[1] / (MINI_H + 2)))
        if key not in seen:
            seen.add(key)
            pts.append(p)

    # 按 y 升序、x 升序排序 → 从上到下、从左到右依次出现
    pts.sort(key=lambda p: (p[1], p[0]))
    return pts


def rand_color():
    return random.choice(PALETTE)


def rand_text():
    return random.choice(LOVE_WORDS)


def make_mini_window(root, x, y, bg=None, text=None, title="♥"):
    """创建一个小 Toplevel 窗口，内含可编辑文字"""
    if stop_event.is_set():
        return None
    bg   = bg   or rand_color()
    text = text or rand_text()
    win  = tk.Toplevel(root)
    win.overrideredirect(True)          # 去掉系统标题栏
    win.geometry(f"{MINI_W}x{MINI_H}+{x}+{y}")
    win.configure(bg=bg)
    win.attributes("-topmost", False)
    win.resizable(False, False)

    # 可编辑文字框
    entry = tk.Entry(
        win,
        font=("微软雅黑", 7, "bold"),
        bg=bg, fg="white",
        bd=0, relief="flat",
        justify="center",
        insertbackground="white",
    )
    entry.insert(0, text)
    entry.pack(fill="both", expand=True, padx=1, pady=2)

    # 拖动支持
    def on_drag_start(e):
        win._drag_x = e.x_root - win.winfo_x()
        win._drag_y = e.y_root - win.winfo_y()
    def on_drag_move(e):
        win.geometry(f"+{e.x_root - win._drag_x}+{e.y_root - win._drag_y}")
    entry.bind("<ButtonPress-1>", on_drag_start)
    entry.bind("<B1-Motion>",     on_drag_move)

    all_mini_wins.append(win)
    return win


def safe_destroy(win):
    try:
        win.destroy()
    except Exception:
        pass
    if win in all_mini_wins:
        all_mini_wins.remove(win)

# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────

def main():
    root = tk.Tk()
    root.withdraw()   # 隐藏主窗口本体

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    # ── 右上角控制面板 ──
    ctrl = tk.Toplevel(root)
    ctrl.overrideredirect(True)
    ctrl.attributes("-topmost", True)
    ctrl.configure(bg="#222222")
    ctrl_w, ctrl_h = 160, 44
    ctrl.geometry(f"{ctrl_w}x{ctrl_h}+{sw - ctrl_w - 10}+10")

    def quit_all():
        stop_event.set()
        # 瞬间销毁所有子窗口，直接 destroy root 即可级联关闭全部
        try:
            root.destroy()
        except Exception:
            pass

    btn_quit = tk.Button(
        ctrl, text="✕  结束程序",
        command=quit_all,
        bg="#E74C3C", fg="white",
        font=("微软雅黑", 11, "bold"),
        relief="flat", cursor="hand2",
        activebackground="#C0392B",
    )
    btn_quit.pack(fill="both", expand=True, padx=4, pady=4)

    # ── 后台动画线程 ──
    def animation():
        # ============ 阶段 1：绘制爱心 ============
        pts = heart_points(sw, sh)   # 按 y→x 排序，从上到下从左到右出现

        heart_wins = []
        for px, py in pts:
            if stop_event.is_set():
                return
            bg   = rand_color()
            text = rand_text()
            # tkinter 操作必须在主线程，用 after 调度
            root.after(0, lambda x=px, y=py, b=bg, t=text:
                       heart_wins.append(make_mini_window(root, x, y, b, t)))
            time.sleep(SPAWN_INTERVAL)

        # 稍作停顿，让用户欣赏爱心
        time.sleep(1.5)

        # ============ 阶段 2a：擦除爱心 ============
        random.shuffle(heart_wins)
        for w in heart_wins:
            if stop_event.is_set():
                return
            root.after(0, lambda win=w: safe_destroy(win))
            time.sleep(ERASE_INTERVAL)

        time.sleep(0.5)

        # ============ 阶段 2b：全屏随机窗口 ============
        margin = 20
        while not stop_event.is_set():
            # 控制上限
            while len(all_mini_wins) >= MAX_RANDOM_WIN and not stop_event.is_set():
                # 删掉最老的
                if all_mini_wins:
                    root.after(0, lambda w=all_mini_wins[0]: safe_destroy(w))
                time.sleep(0.05)

            if stop_event.is_set():
                break
            rx = random.randint(margin, sw - MINI_W - margin)
            ry = random.randint(margin, sh - MINI_H - margin)
            root.after(0, lambda x=rx, y=ry: make_mini_window(root, x, y))
            time.sleep(RANDOM_INTERVAL)

    t = threading.Thread(target=animation, daemon=True)
    t.start()

    root.mainloop()


if __name__ == "__main__":
    main()
