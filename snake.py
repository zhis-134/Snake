# -*- coding: utf-8 -*-
"""
贪吃蛇 (Snake) —— Python + tkinter 版

运行方式：
    python snake.py

操作：
    方向键 ↑ ↓ ← →  或  W A S D   控制移动
    P                              暂停 / 继续
    R  或  空格                    重新开始
    ESC                            退出

依赖：只用 Python 自带的 tkinter，不需要安装任何第三方库。
"""

import random
import tkinter as tk

# ---------------- 可调参数（想改手感就动这里） ----------------
CELL = 22          # 每个格子的边长（像素）
COLS = 22          # 横向格子数
ROWS = 22          # 纵向格子数
START_SPEED = 160  # 每走一步的间隔（毫秒），数字越小蛇越快
MIN_SPEED = 65     # 最快能快到多少
SPEED_STEP = 5     # 每吃一个食物，加快多少毫秒

# ---------------- 配色 ----------------
C_BG = "#12161c"      # 背景
C_GRID = "#1b212a"    # 网格线
C_SNAKE = "#3fb950"   # 蛇身
C_HEAD = "#7ee787"    # 蛇头
C_FOOD = "#f85149"    # 食物
C_FG = "#e6edf3"      # 文字
C_OVER = "#0d1117"    # 结束遮罩


class SnakeGame:
    """整个游戏就是一个类。tkinter 里，'类' 相当于 C 语言的结构体 + 配套函数。"""

    def __init__(self, root):
        self.root = root
        self.root.title("贪吃蛇 —— Python + tkinter")
        self.root.resizable(False, False)

        self.w = COLS * CELL   # 画布宽
        self.h = ROWS * CELL   # 画布高

        # 顶部信息栏（得分 / 最高分）
        self.label = tk.Label(root, font=("Microsoft YaHei", 12, "bold"),
                              bg="#0d1117", fg=C_FG, anchor="center", height=2)
        self.label.pack(fill="x")

        # 画布：游戏画面就画在这上面
        self.canvas = tk.Canvas(root, width=self.w, height=self.h,
                                bg=C_BG, highlightthickness=0)
        self.canvas.pack()

        self.draw_board()     # 画一次背景和网格（以后不再重画）
        self.bind_keys()
        self.best = 0         # 本次运行的最高分
        self.gen = 0          # 用来作废过期的定时器，防止"重开后两条蛇在跑"
        self.reset()

    # ========== 键盘 ==========
    def bind_keys(self):
        dirs = {
            "Up": (0, -1), "Down": (0, 1), "Left": (-1, 0), "Right": (1, 0),
            "w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0),
            "W": (0, -1), "S": (0, 1), "A": (-1, 0), "D": (1, 0),
        }
        for key, d in dirs.items():
            # lambda 里用 d=d 把当前值"抓"住，否则所有键都会用最后一个 d
            self.root.bind("<%s>" % key, lambda e, d=d: self.turn(d))

        self.root.bind("<p>", lambda e: self.toggle_pause())
        self.root.bind("<P>", lambda e: self.toggle_pause())
        self.root.bind("<r>", lambda e: self.reset())
        self.root.bind("<R>", lambda e: self.reset())
        self.root.bind("<space>", lambda e: self.reset())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

    # ========== 一局开始 ==========
    def reset(self):
        self.gen += 1              # 让上一局残留的定时器失效
        cx, cy = COLS // 2, ROWS // 2

        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]  # 列表头 = 蛇头
        self.direction = (1, 0)    # 当前方向：向右
        self.queue = []            # 按键缓冲（最多存 2 个，解决"快速连按"问题）
        self.score = 0
        self.speed = START_SPEED
        self.paused = False
        self.running = True

        self.canvas.delete("over")   # 清掉上一局的"游戏结束"遮罩
        self.food = self.spawn_food()
        self.redraw()
        self.schedule(self.gen)

    def spawn_food(self):
        """在所有空格子里随机挑一个放食物。"""
        occupied = set(self.snake)
        empty = [(x, y) for x in range(COLS) for y in range(ROWS)
                 if (x, y) not in occupied]
        return random.choice(empty) if empty else None

    # ========== 方向控制 ==========
    def turn(self, d):
        # 拿"最后被接受的方向"来比，而不是当前方向 —— 这样快速连按也不会出 bug
        last = self.queue[-1] if self.queue else self.direction

        # 不能 180 度掉头（向右走时按左，等于直接撞进自己脖子）
        if d[0] + last[0] == 0 and d[1] + last[1] == 0:
            return
        if d == last:
            return
        if len(self.queue) < 2:     # 最多缓冲 2 步，多了会让操作发飘
            self.queue.append(d)

    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        self.redraw()
        if not self.paused:
            self.schedule(self.gen)

    # ========== 心跳（每次移动一格） ==========
    def schedule(self, gen):
        """预约下一次 tick。gen 是"代号"，重开一局后旧代号自动作废。"""
        self.root.after(self.speed, lambda: self.tick(gen))

    def tick(self, gen):
        if gen != self.gen or not self.running or self.paused:
            return
        self.step()
        self.redraw()
        if self.running and not self.paused:
            self.schedule(gen)

    def step(self):
        if self.queue:
            self.direction = self.queue.pop(0)

        hx, hy = self.snake[0]
        nx, ny = hx + self.direction[0], hy + self.direction[1]

        # 撞墙？
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            self.game_over("撞墙了！")
            return

        # 撞自己？尾巴这一格会移走，所以最末一节不算（snake[:-1]）
        if (nx, ny) in self.snake[:-1]:
            self.game_over("咬到自己了！")
            return

        self.snake.insert(0, (nx, ny))     # 头往前长一格
        if (nx, ny) == self.food:
            self.score += 1
            self.best = max(self.best, self.score)
            self.speed = max(MIN_SPEED, self.speed - SPEED_STEP)  # 越吃越快
            self.food = self.spawn_food()
            if self.food is None:
                self.game_over("满屏通关！")
        else:
            self.snake.pop()               # 没吃到就把尾巴缩掉，总长度不变

    def game_over(self, reason):
        self.running = False
        cx, cy = self.w // 2, self.h // 2
        self.canvas.create_rectangle(0, cy - 62, self.w, cy + 62,
                                     fill=C_OVER, outline="", tags="over")
        self.canvas.create_text(cx, cy - 24, text="游戏结束", fill=C_FOOD,
                                font=("Microsoft YaHei", 26, "bold"), tags="over")
        self.canvas.create_text(cx, cy + 12, text=reason, fill=C_FG,
                                font=("Microsoft YaHei", 13), tags="over")
        self.canvas.create_text(cx, cy + 42, text="按 R 或空格 重新开始",
                                fill="#8b949e",
                                font=("Microsoft YaHei", 11), tags="over")
        self.redraw()

    # ========== 画面 ==========
    def draw_board(self):
        """背景和网格只画一次。"""
        self.canvas.create_rectangle(0, 0, self.w, self.h, fill=C_BG, outline="")
        for x in range(0, self.w + 1, CELL):
            self.canvas.create_line(x, 0, x, self.h, fill=C_GRID)
        for y in range(0, self.h + 1, CELL):
            self.canvas.create_line(0, y, self.w, y, fill=C_GRID)

    def redraw(self):
        """每帧重画会动的东西（蛇、食物）。背景不动，所以只删 'dyn' 标签的。"""
        self.canvas.delete("dyn")

        if self.food:
            fx, fy = self.food
            self.canvas.create_oval(fx * CELL + 3, fy * CELL + 3,
                                    (fx + 1) * CELL - 3, (fy + 1) * CELL - 3,
                                    fill=C_FOOD, outline="", tags="dyn")

        for i, (x, y) in enumerate(self.snake):
            color = C_HEAD if i == 0 else C_SNAKE
            self.canvas.create_rectangle(x * CELL + 1, y * CELL + 1,
                                         (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                                         fill=color, outline="", tags="dyn")

        tip = "（已暂停，按 P 继续）" if self.paused else ""
        self.label.config(
            text="得分: %d      最高: %d      %s" % (self.score, self.best, tip))

        if self.paused:
            self.canvas.create_text(self.w // 2, self.h // 2, text="暂停中",
                                    fill=C_FG, font=("Microsoft YaHei", 24, "bold"),
                                    tags="dyn")


def main():
    root = tk.Tk()
    root.configure(bg="#0d1117")
    SnakeGame(root)
    root.mainloop()   # 进入"事件循环"：程序停在这里，等键盘和定时器消息


if __name__ == "__main__":
    main()
