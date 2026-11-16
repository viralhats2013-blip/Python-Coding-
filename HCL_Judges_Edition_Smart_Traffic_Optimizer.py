import tkinter as tk
from tkinter import ttk
import random
import time

# ============================================================
# HCL JIGSAW - SMART TRAFFIC FLOW OPTIMIZER
# Enhanced educational simulation with adaptive signal timing
# ============================================================

WIDTH, HEIGHT = 900, 540
CX, CY = WIDTH // 2, HEIGHT // 2
ROAD_WIDTH = 190
TICK_MS = 35
CAR_SPEED = 2.8
MAX_QUEUE = 8
VEHICLE_GAP = 34

ROADS = ["NORTH", "EAST", "SOUTH", "WEST"]
ROAD_COLORS = {
    "NORTH": "#38bdf8",
    "EAST": "#f59e0b",
    "SOUTH": "#34d399",
    "WEST": "#a78bfa",
}
BG = "#eef3f8"
PANEL = "#ffffff"
DARK = "#172033"
MUTED = "#64748b"
GREEN = "#22c55e"
RED = "#ef4444"


class SmartTrafficApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HCL | Smart Traffic Flow Optimizer")
        self.root.geometry("1120x850")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.mode = tk.StringVar(value="Smart")
        self.running = False
        self.after_id = None
        self.vehicles = []
        self.vehicle_id = 0

        self.queues = {road: 0 for road in ROADS}
        self.active_index = 0
        self.phase_elapsed = 0.0
        self.elapsed = 0.0
        self.total_passed = 0
        self.total_spawned = 0
        self.total_wait = 0.0
        self.last_tick = time.time()

        self.fixed_green = 8.0
        self.current_green = self.fixed_green
        self.last_decision = "Waiting to start"
        self.history = {road: 0 for road in ROADS}

        self.build_ui()
        self.draw_junction()
        self.refresh()

    # ------------------------- UI ----------------------------

    def build_ui(self):
        header = tk.Frame(self.root, bg="#10233f", height=75)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="SMART TRAFFIC FLOW OPTIMIZER",
            bg="#10233f", fg="white",
            font=("Arial", 20, "bold")
        ).pack(side="left", padx=22, pady=16)

        tk.Label(
            header, text="HCL JIGSAW  |  AI SIMULATION",
            bg="#10233f", fg="#9bd5ff",
            font=("Arial", 10, "bold")
        ).pack(side="right", padx=22)

        controls = tk.Frame(self.root, bg=BG)
        controls.pack(fill="x", padx=18, pady=10)

        tk.Label(controls, text="SIGNAL MODE", bg=BG, fg=MUTED,
                 font=("Arial", 9, "bold")).pack(side="left", padx=(0, 8))

        self.mode_box = ttk.Combobox(
            controls, textvariable=self.mode,
            values=["Smart", "Fixed"], state="readonly", width=12
        )
        self.mode_box.pack(side="left", padx=4)
        self.mode_box.bind("<<ComboboxSelected>>", self.mode_changed)

        self.make_button(controls, "START", self.start, "#16a34a").pack(side="left", padx=5)
        self.make_button(controls, "PAUSE", self.pause, "#d97706").pack(side="left", padx=5)
        self.make_button(controls, "RESET", self.reset, "#475569").pack(side="left", padx=5)

        self.run_label = tk.Label(
            controls, text="● STOPPED", bg=BG, fg=RED,
            font=("Arial", 10, "bold")
        )
        self.run_label.pack(side="right", padx=10)

        # KPI cards
        kpi_row = tk.Frame(self.root, bg=BG)
        kpi_row.pack(fill="x", padx=18, pady=(0, 9))

        self.kpi_values = {}
        for title, key in [
            ("VEHICLES PASSED", "passed"),
            ("VEHICLES WAITING", "waiting"),
            ("TOTAL GENERATED", "generated"),
            ("SIMULATION TIME", "time"),
        ]:
            card = tk.Frame(kpi_row, bg=PANEL, highlightbackground="#d8e1ec",
                            highlightthickness=1, padx=12, pady=8)
            card.pack(side="left", expand=True, fill="x", padx=4)
            tk.Label(card, text=title, bg=PANEL, fg=MUTED,
                     font=("Arial", 8, "bold")).pack(anchor="w")
            value = tk.Label(card, text="0", bg=PANEL, fg=DARK,
                             font=("Arial", 19, "bold"))
            value.pack(anchor="w", pady=(3, 0))
            self.kpi_values[key] = value

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=18, pady=4)

        left = tk.Frame(main, bg=PANEL, highlightbackground="#d8e1ec",
                        highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(left, text="LIVE INTERSECTION SIMULATION", bg=PANEL,
                 fg=DARK, font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=9)

        self.canvas = tk.Canvas(
            left, width=WIDTH, height=HEIGHT,
            bg="#dce8d5", highlightthickness=0
        )
        self.canvas.pack(padx=8, pady=(0, 8))

        right = tk.Frame(main, bg=BG, width=250)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        self.make_panel_title(right, "LIVE ROAD ANALYTICS")
        self.road_rows = {}
        for road in ROADS:
            row = tk.Frame(right, bg=PANEL, padx=10, pady=8,
                           highlightbackground="#d8e1ec", highlightthickness=1)
            row.pack(fill="x", pady=4)
            top = tk.Frame(row, bg=PANEL)
            top.pack(fill="x")
            tk.Label(top, text=road, bg=PANEL, fg=ROAD_COLORS[road],
                     font=("Arial", 9, "bold")).pack(side="left")
            count = tk.Label(top, text="0 vehicles", bg=PANEL, fg=DARK,
                             font=("Arial", 9, "bold"))
            count.pack(side="right")
            bar = ttk.Progressbar(row, maximum=MAX_QUEUE, length=190)
            bar.pack(fill="x", pady=6)
            density = tk.Label(row, text="LOW DENSITY", bg=PANEL, fg=GREEN,
                                font=("Arial", 8, "bold"))
            density.pack(anchor="w")
            self.road_rows[road] = (count, bar, density)

        self.make_panel_title(right, "AI SIGNAL DECISION")
        decision = tk.Frame(right, bg="#eaf4ff", padx=11, pady=10)
        decision.pack(fill="x", pady=4)
        self.active_text = tk.Label(
            decision, text="GREEN: NORTH", bg="#eaf4ff", fg="#075985",
            font=("Arial", 12, "bold")
        )
        self.active_text.pack(anchor="w")
        self.timer_text = tk.Label(
            decision, text="Green time: 8.0 sec", bg="#eaf4ff", fg=DARK,
            font=("Arial", 10)
        )
        self.timer_text.pack(anchor="w", pady=3)
        self.reason_text = tk.Label(
            decision, text="Waiting to start", bg="#eaf4ff", fg=MUTED,
            font=("Arial", 8), wraplength=205, justify="left"
        )
        self.reason_text.pack(anchor="w", pady=(3, 0))

        self.make_panel_title(right, "PERFORMANCE")
        perf = tk.Frame(right, bg=PANEL, padx=11, pady=10,
                        highlightbackground="#d8e1ec", highlightthickness=1)
        perf.pack(fill="x", pady=4)
        self.performance_text = tk.Label(
            perf, text="Smart signal adapts to queue size.\nFixed signal uses equal timing.",
            bg=PANEL, fg=DARK, font=("Arial", 9), justify="left",
            wraplength=205
        )
        self.performance_text.pack(anchor="w")

        footer = tk.Label(
            self.root,
            text="AI RULE: Higher vehicle queues receive longer green signals, within a safe time limit.",
            bg="#10233f", fg="white", font=("Arial", 9),
            padx=12, pady=9
        )
        footer.pack(fill="x", side="bottom")

    def make_button(self, parent, text, command, color):
        return tk.Button(
            parent, text=text, command=command,
            bg=color, fg="white", activebackground=color,
            activeforeground="white", relief="flat",
            font=("Arial", 9, "bold"), padx=14, pady=7,
            cursor="hand2"
        )

    def make_panel_title(self, parent, title):
        tk.Label(parent, text=title, bg=BG, fg=DARK,
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(9, 3))

    # ---------------------- Road drawing ---------------------

    def draw_junction(self):
        c = self.canvas
        c.delete("all")

        c.create_rectangle(
            CX - ROAD_WIDTH // 2, 0,
            CX + ROAD_WIDTH // 2, HEIGHT,
            fill="#454b52", outline=""
        )
        c.create_rectangle(
            0, CY - ROAD_WIDTH // 2,
            WIDTH, CY + ROAD_WIDTH // 2,
            fill="#454b52", outline=""
        )

        # Simple lane markings (no raised divider or garden)
        c.create_line(0, CY, WIDTH, CY, fill="#cbd5e1",
                      dash=(13, 13), width=2)
        c.create_line(CX, 0, CX, HEIGHT, fill="#cbd5e1",
                      dash=(13, 13), width=2)

        c.create_text(CX + 135, 20, text="NORTH ROAD", fill=DARK,
                      font=("Arial", 9, "bold"))
        c.create_text(CX - 135, HEIGHT - 18, text="SOUTH ROAD", fill=DARK,
                      font=("Arial", 9, "bold"))
        c.create_text(65, CY - 115, text="WEST ROAD", fill=DARK,
                      font=("Arial", 9, "bold"))
        c.create_text(WIDTH - 65, CY + 115, text="EAST ROAD", fill=DARK,
                      font=("Arial", 9, "bold"))

        # Stop lines
        c.create_line(CX - 72, CY - 105, CX + 72, CY - 105,
                      fill="white", width=4)
        c.create_line(CX - 72, CY + 105, CX + 72, CY + 105,
                      fill="white", width=4)
        c.create_line(CX - 105, CY - 72, CX - 105, CY + 72,
                      fill="white", width=4)
        c.create_line(CX + 105, CY - 72, CX + 105, CY + 72,
                      fill="white", width=4)

        self.signal_lights = {}
        positions = {
            "NORTH": (CX + 125, CY - 130),
            "EAST": (CX + 130, CY + 125),
            "SOUTH": (CX - 125, CY + 130),
            "WEST": (CX - 130, CY - 125),
        }
        for road, (x, y) in positions.items():
            c.create_rectangle(x - 24, y - 19, x + 24, y + 19,
                               fill="#172033", outline="white", width=2)
            red = c.create_oval(x - 16, y - 9, x - 4, y + 3,
                                fill="#702b2b", outline="")
            green = c.create_oval(x + 4, y - 9, x + 16, y + 3,
                                  fill="#245b3b", outline="")
            self.signal_lights[road] = (red, green)

        self.vehicle_items = []

    # ---------------------- Simulation -----------------------

    def mode_changed(self, _event=None):
        self.phase_elapsed = 0
        self.current_green = self.calculate_green(ROADS[self.active_index])
        self.last_decision = f"{self.mode.get()} mode selected."

    def start(self):
        if not self.running:
            self.running = True
            self.last_tick = time.time()
            self.run_label.config(text="● RUNNING", fg=GREEN)
            self.after_id = self.root.after(TICK_MS, self.tick)

    def pause(self):
        self.running = False
        self.run_label.config(text="● PAUSED", fg="#d97706")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def reset(self):
        self.pause()
        self.vehicles.clear()
        self.queues = {road: 0 for road in ROADS}
        self.vehicle_id = 0
        self.active_index = 0
        self.phase_elapsed = 0
        self.elapsed = 0
        self.total_passed = 0
        self.total_spawned = 0
        self.total_wait = 0
        self.current_green = self.calculate_green("NORTH")
        self.last_decision = "Simulation reset. Press START."
        self.draw_junction()
        self.refresh()

    def calculate_green(self, road):
        if self.mode.get() == "Fixed":
            return self.fixed_green

        queue = self.queues[road]
        # Simple adaptive rule: queue length determines green duration.
        return min(18.0, max(5.0, 5.0 + queue * 1.6))

    def spawn_vehicles(self):
        chances = {
            "NORTH": 0.12,
            "EAST": 0.15,
            "SOUTH": 0.10,
            "WEST": 0.13,
        }
        for road in ROADS:
            if self.queues[road] >= MAX_QUEUE:
                continue
            if random.random() < chances[road]:
                self.vehicle_id += 1
                stop = self.stop_position(road)
                pos = max(0.0, stop - self.queues[road] * VEHICLE_GAP)
                self.vehicles.append({
                    "id": self.vehicle_id,
                    "road": road,
                    "pos": pos,
                    "kind": random.choices(
                        ["car", "bike", "bus"],
                        weights=[7, 2, 1], k=1
                    )[0],
                    "wait": 0.0,
                })
                self.queues[road] += 1
                self.total_spawned += 1

    def stop_position(self, road):
        if road == "NORTH":
            return CY - 115
        if road == "SOUTH":
            return HEIGHT + 25 - (CY + 115)
        if road == "EAST":
            return WIDTH + 25 - (CX + 115)
        return CX - 115 + 25

    def path_length(self, road):
        return HEIGHT + 50 if road in ("NORTH", "SOUTH") else WIDTH + 50

    def vehicle_xy(self, vehicle):
        p, road = vehicle["pos"], vehicle["road"]
        if road == "NORTH":
            return CX - 48, -25 + p, False
        if road == "SOUTH":
            return CX + 48, HEIGHT + 25 - p, False
        if road == "EAST":
            return WIDTH + 25 - p, CY - 48, True
        return -25 + p, CY + 48, True

    def draw_vehicle(self, x, y, vehicle, horizontal):
        kind = vehicle["kind"]
        color = ROAD_COLORS[vehicle["road"]]
        if kind == "bus":
            length, width = (34, 14) if horizontal else (14, 34)
        elif kind == "bike":
            length, width = (18, 9) if horizontal else (9, 18)
        else:
            length, width = (24, 13) if horizontal else (13, 24)

        items = [self.canvas.create_rectangle(
            x - length / 2, y - width / 2,
            x + length / 2, y + width / 2,
            fill=color, outline="#111827", width=1
        )]
        if kind != "bike":
            if horizontal:
                items.append(self.canvas.create_rectangle(
                    x - 5, y - 4, x + 5, y + 4,
                    fill="#e0f2fe", outline=""
                ))
            else:
                items.append(self.canvas.create_rectangle(
                    x - 4, y - 5, x + 4, y + 5,
                    fill="#e0f2fe", outline=""
                ))
        return items

    def tick(self):
        if not self.running:
            return

        dt = TICK_MS / 1000
        self.elapsed += dt
        self.phase_elapsed += dt
        self.spawn_vehicles()

        active = ROADS[self.active_index]
        stop = self.stop_position(active)
        green_active = self.phase_elapsed < self.current_green

        # Release the first waiting vehicle when the signal is green.
        waiting = sorted(
            [v for v in self.vehicles
             if v["road"] == active and v["pos"] <= stop],
            key=lambda item: item["id"]
        )
        moving_on_active = [
            v for v in self.vehicles
            if v["road"] == active and v["pos"] > stop
        ]

        if green_active and waiting:
            safe_to_release = (
                not moving_on_active or
                min(v["pos"] - stop for v in moving_on_active) >= VEHICLE_GAP
            )
            if safe_to_release:
                first = waiting[0]
                first["pos"] = stop + 1
                self.queues[active] = max(0, self.queues[active] - 1)

        # Move released vehicles and count waiting time for queued vehicles.
        for vehicle in self.vehicles[:]:
            road = vehicle["road"]
            vehicle_stop = self.stop_position(road)

            if vehicle["pos"] <= vehicle_stop:
                vehicle["wait"] += dt
                # Only the first vehicle in a queue can approach the stop line.
                ahead = [
                    other for other in self.vehicles
                    if other["road"] == road
                    and other["id"] < vehicle["id"]
                    and other["pos"] <= vehicle_stop
                ]
                if not ahead and road == active and green_active:
                    vehicle["pos"] = min(vehicle_stop, vehicle["pos"] + CAR_SPEED)
            else:
                vehicle["pos"] += CAR_SPEED

            if vehicle["pos"] > self.path_length(road):
                self.vehicles.remove(vehicle)
                self.total_passed += 1
                self.total_wait += vehicle["wait"]

        # Change signal after its green period and allow the crossing to clear.
        crossing_busy = any(
            v["road"] == active and
            stop < v["pos"] < stop + 170
            for v in self.vehicles
        )
        if self.phase_elapsed >= self.current_green and not crossing_busy:
            self.active_index = (self.active_index + 1) % len(ROADS)
            next_road = ROADS[self.active_index]
            self.phase_elapsed = 0.0
            self.current_green = self.calculate_green(next_road)
            self.last_decision = (
                f"{next_road} selected. Queue: {self.queues[next_road]} "
                f"vehicle(s); green time: {self.current_green:.1f} seconds."
            )

        self.refresh()
        self.after_id = self.root.after(TICK_MS, self.tick)

    # ---------------------- Dashboard ------------------------

    def density_label(self, count):
        if count <= 2:
            return "LOW DENSITY", GREEN
        if count <= 5:
            return "MEDIUM DENSITY", "#d97706"
        return "HIGH DENSITY", RED

    def refresh(self):
        active = ROADS[self.active_index]

        self.kpi_values["passed"].config(text=str(self.total_passed))
        self.kpi_values["waiting"].config(text=str(sum(self.queues.values())))
        self.kpi_values["generated"].config(text=str(self.total_spawned))
        self.kpi_values["time"].config(text=f"{self.elapsed:.1f}s")

        for road in ROADS:
            count, bar, density = self.road_rows[road]
            q = self.queues[road]
            label, color = self.density_label(q)
            count.config(text=f"{q} vehicles")
            bar["value"] = q
            density.config(text=label, fg=color)

        for road, (red, green) in self.signal_lights.items():
            is_active = road == active
            self.canvas.itemconfigure(red, fill="#702b2b" if is_active else "#ef4444")
            self.canvas.itemconfigure(green, fill="#22c55e" if is_active else "#245b3b")

        for item in self.vehicle_items:
            self.canvas.delete(item)
        self.vehicle_items = []

        for vehicle in self.vehicles:
            x, y, horizontal = self.vehicle_xy(vehicle)
            self.vehicle_items.extend(
                self.draw_vehicle(x, y, vehicle, horizontal)
            )

        remaining = max(0.0, self.current_green - self.phase_elapsed)
        self.active_text.config(text=f"GREEN: {active}")
        self.timer_text.config(text=f"Green time remaining: {remaining:.1f} sec")
        self.reason_text.config(text=self.last_decision)

        avg_wait = (
            self.total_wait / self.total_passed
            if self.total_passed else 0.0
        )
        mode_description = (
            "Adaptive timing: queue length controls green time."
            if self.mode.get() == "Smart"
            else "Fixed timing: every road receives the same green time."
        )
        self.performance_text.config(
            text=f"{mode_description}\n\nAverage wait of passed vehicles: "
                 f"{avg_wait:.1f} sec"
        )


if __name__ == "__main__":
    window = tk.Tk()
    app = SmartTrafficApp(window)
    window.mainloop()
