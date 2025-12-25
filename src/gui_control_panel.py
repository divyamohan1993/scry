"""
Scry - Modern GUI Control Panel
A sleek, dark-themed admin control panel for managing environment variables.
Features auto-save, toggle switches, and intuitive controls.
"""

import os
import sys
import re
import tkinter as tk
from tkinter import ttk, messagebox, font
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure we can import from the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import set_key
except ImportError:
    print("Error: python-dotenv not found. Install with: pip install python-dotenv")
    sys.exit(1)


# =============================================================================
# CONFIGURATION SCHEMA
# =============================================================================
# Defines all configuration variables, their types, defaults, and UI metadata
CONFIG_SCHEMA = {
    "API Configuration": [
        {
            "key": "GEMINI_API_KEY",
            "type": "password",
            "default": "",
            "desc": "Your Gemini AI API Key",
            "tooltip": "Get your free key from: https://aistudio.google.com/",
        },
    ],
    "Timing Settings": [
        {
            "key": "INITIAL_WAIT",
            "type": "int",
            "default": 10,
            "min": 0,
            "max": 60,
            "desc": "Initial Wait (seconds)",
            "tooltip": "Seconds to wait before starting after launch",
        },
        {
            "key": "POST_ACTION_WAIT",
            "type": "int",
            "default": 10,
            "min": 0,
            "max": 60,
            "desc": "Post-Action Wait",
            "tooltip": "Seconds to wait after performing an action",
        },
        {
            "key": "SWITCH_QUESTION_WAIT",
            "type": "int",
            "default": 5,
            "min": 0,
            "max": 30,
            "desc": "Switch Question Wait",
            "tooltip": "Seconds to wait when switching between questions",
        },
        {
            "key": "POLL_INTERVAL",
            "type": "int",
            "default": 3,
            "min": 1,
            "max": 30,
            "desc": "Poll Interval",
            "tooltip": "Seconds between screen checks in Auto Mode",
        },
    ],
    "API & Retry": [
        {
            "key": "MAX_RETRIES",
            "type": "int",
            "default": 2,
            "min": 0,
            "max": 10,
            "desc": "Max Retries",
            "tooltip": "Maximum number of retries for API calls on failure",
        },
    ],
    "Mouse & Typing": [
        {
            "key": "MOUSE_MOVE_DURATION",
            "type": "float",
            "default": 0.8,
            "min": 0.1,
            "max": 3.0,
            "step": 0.1,
            "desc": "Mouse Move Duration",
            "tooltip": "Duration of mouse movement animation (seconds)",
        },
        {
            "key": "TYPING_WPM_MIN",
            "type": "int",
            "default": 30,
            "min": 10,
            "max": 200,
            "desc": "Min Typing Speed (WPM)",
            "tooltip": "Minimum typing speed in Words Per Minute",
        },
        {
            "key": "TYPING_WPM_MAX",
            "type": "int",
            "default": 100,
            "min": 20,
            "max": 300,
            "desc": "Max Typing Speed (WPM)",
            "tooltip": "Maximum typing speed in Words Per Minute",
        },
    ],
    "Feature Flags": [
        {
            "key": "HANDLE_DESCRIPTIVE_ANSWERS",
            "type": "bool",
            "default": True,
            "desc": "Handle Descriptive Answers",
            "tooltip": "Whether to handle descriptive/essay questions",
        },
        {
            "key": "ENABLE_DETAILED_MODE",
            "type": "bool",
            "default": True,
            "desc": "Enable Detailed Mode",
            "tooltip": "Enable handling of detailed/long answers with marks-based length",
        },
        {
            "key": "URGENT_MODE",
            "type": "bool",
            "default": False,
            "desc": "Urgent Mode",
            "tooltip": "Reduces delays for time-critical situations, faster typing",
        },
    ],
    "Input Modes": [
        {
            "key": "MANUAL_MODE",
            "type": "bool",
            "default": False,
            "desc": "Manual Mode (Hotkeys Only)",
            "tooltip": "True = Hotkey-triggered, False = Automatic Loop",
        },
        {
            "key": "HOTKEY_MCQ",
            "type": "str",
            "default": "q",
            "desc": "MCQ Hotkey",
            "tooltip": "Hotkey to trigger MCQ detection (single key)",
        },
        {
            "key": "HOTKEY_DESCRIPTIVE",
            "type": "str",
            "default": "z",
            "desc": "Descriptive Hotkey",
            "tooltip": "Hotkey to trigger Descriptive question detection",
        },
        {
            "key": "HOTKEY_DELAY",
            "type": "float",
            "default": 2.0,
            "min": 0.5,
            "max": 10.0,
            "step": 0.5,
            "desc": "Hotkey Delay",
            "tooltip": "Delay in seconds after hotkey press before screen capture",
        },
    ],
    "Developer Options": [
        {
            "key": "DEVELOPER_MODE",
            "type": "bool",
            "default": False,
            "desc": "Developer Mode",
            "tooltip": "Show console window and extra logging (True for development)",
        },
        {
            "key": "VERBOSE_STARTUP",
            "type": "bool",
            "default": False,
            "desc": "Verbose Startup",
            "tooltip": "Show detailed startup logs",
        },
        {
            "key": "DEV_MAX_ITERATIONS",
            "type": "int",
            "default": 2,
            "min": 1,
            "max": 100,
            "desc": "Dev Max Iterations",
            "tooltip": "Maximum loop iterations in developer mode",
        },
        {
            "key": "DEV_SAVE_SCREENSHOTS",
            "type": "bool",
            "default": True,
            "desc": "Save Screenshots",
            "tooltip": "Save screenshots to disk for debugging",
        },
    ],
    "Auto-Update": [
        {
            "key": "GITHUB_REPO_OWNER",
            "type": "str",
            "default": "your-username",
            "desc": "GitHub Repo Owner",
            "tooltip": "GitHub username/organization for update checks",
        },
        {
            "key": "GITHUB_REPO_NAME",
            "type": "str",
            "default": "scry",
            "desc": "GitHub Repo Name",
            "tooltip": "GitHub repository name for update checks",
        },
        {
            "key": "UPDATE_CHECK_INTERVAL_SECONDS",
            "type": "int",
            "default": 1800,
            "min": 0,
            "max": 86400,
            "desc": "Update Check Interval",
            "tooltip": "How often to check for updates (seconds). 0 = disabled",
        },
    ],
}


# =============================================================================
# COLOR THEME
# =============================================================================
class Theme:
    """Modern dark theme colors"""
    BG_DARK = "#0f0f0f"
    BG_MEDIUM = "#1a1a1a"
    BG_LIGHT = "#252525"
    BG_CARD = "#1e1e1e"
    
    ACCENT = "#6366f1"  # Indigo
    ACCENT_HOVER = "#818cf8"
    ACCENT_ACTIVE = "#4f46e5"
    
    SUCCESS = "#22c55e"
    WARNING = "#f59e0b"
    ERROR = "#ef4444"
    INFO = "#3b82f6"
    
    TEXT_PRIMARY = "#f5f5f5"
    TEXT_SECONDARY = "#a1a1aa"
    TEXT_MUTED = "#71717a"
    
    BORDER = "#333333"
    BORDER_FOCUS = "#6366f1"
    
    TOGGLE_ON = "#22c55e"
    TOGGLE_OFF = "#3f3f46"
    TOGGLE_THUMB = "#ffffff"


# =============================================================================
# CUSTOM WIDGETS
# =============================================================================
class ToggleSwitch(tk.Canvas):
    """Modern animated toggle switch widget"""
    
    def __init__(self, parent, variable: tk.BooleanVar, command=None, **kwargs):
        self.width = kwargs.pop('width', 50)
        self.height = kwargs.pop('height', 26)
        super().__init__(parent, width=self.width, height=self.height,
                         bg=Theme.BG_CARD, highlightthickness=0, **kwargs)
        
        self.variable = variable
        self.command = command
        self.thumb_pos = self.width - 23 if variable.get() else 3
        
        self.bind("<Button-1>", self.toggle)
        self.variable.trace_add("write", self._on_variable_change)
        
        self._draw()
    
    def _draw(self):
        """Draw the toggle switch"""
        self.delete("all")
        
        # Background track
        bg_color = Theme.TOGGLE_ON if self.variable.get() else Theme.TOGGLE_OFF
        self.create_rounded_rect(0, 0, self.width, self.height, 13, fill=bg_color, outline="")
        
        # Thumb
        thumb_x = self.thumb_pos
        self.create_oval(thumb_x, 3, thumb_x + 20, 23, fill=Theme.TOGGLE_THUMB, outline="")
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Create a rounded rectangle"""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def toggle(self, event=None):
        """Toggle the switch state"""
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()
    
    def _on_variable_change(self, *args):
        """Animate to new position"""
        target = self.width - 23 if self.variable.get() else 3
        self._animate_to(target)
    
    def _animate_to(self, target):
        """Animate the thumb to target position"""
        diff = target - self.thumb_pos
        if abs(diff) < 2:
            self.thumb_pos = target
            self._draw()
            return
        
        self.thumb_pos += diff / 4
        self._draw()
        self.after(10, lambda: self._animate_to(target))


class ModernEntry(tk.Frame):
    """Modern styled entry widget with floating label effect"""
    
    def __init__(self, parent, label: str, variable: tk.StringVar, 
                 show: str = "", command=None, **kwargs):
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)
        
        self.variable = variable
        self.command = command
        self.label_text = label
        
        # Label
        self.label = tk.Label(self, text=label, bg=Theme.BG_CARD,
                              fg=Theme.TEXT_SECONDARY, font=("Segoe UI", 9))
        self.label.pack(anchor="w", padx=2)
        
        # Entry frame for border effect
        self.entry_frame = tk.Frame(self, bg=Theme.BORDER, padx=1, pady=1)
        self.entry_frame.pack(fill="x", pady=(2, 0))
        
        # Entry
        self.entry = tk.Entry(
            self.entry_frame,
            textvariable=variable,
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            insertbackground=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 11),
            relief="flat",
            show=show,
        )
        self.entry.pack(fill="x", padx=1, pady=1, ipady=6)
        
        # Bind events
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<KeyRelease>", self._on_key)
    
    def _on_focus_in(self, event):
        self.entry_frame.configure(bg=Theme.BORDER_FOCUS)
        self.label.configure(fg=Theme.ACCENT)
    
    def _on_focus_out(self, event):
        self.entry_frame.configure(bg=Theme.BORDER)
        self.label.configure(fg=Theme.TEXT_SECONDARY)
        if self.command:
            self.command()
    
    def _on_key(self, event):
        # Auto-save on typing (debounced by focus out)
        pass


class ModernSpinbox(tk.Frame):
    """Modern styled spinbox with increment/decrement buttons"""
    
    def __init__(self, parent, label: str, variable, 
                 from_: float, to: float, increment: float = 1,
                 command=None, **kwargs):
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)
        
        self.variable = variable
        self.command = command
        self.from_ = from_
        self.to = to
        self.increment = increment
        
        # Label
        self.label = tk.Label(self, text=label, bg=Theme.BG_CARD,
                              fg=Theme.TEXT_SECONDARY, font=("Segoe UI", 9))
        self.label.pack(anchor="w", padx=2)
        
        # Control frame
        self.control_frame = tk.Frame(self, bg=Theme.BG_CARD)
        self.control_frame.pack(fill="x", pady=(2, 0))
        
        # Decrement button
        self.btn_dec = tk.Button(
            self.control_frame,
            text="−",
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=3,
            command=self.decrement,
            activebackground=Theme.ACCENT,
            activeforeground="white",
        )
        self.btn_dec.pack(side="left")
        
        # Value display
        self.value_frame = tk.Frame(self.control_frame, bg=Theme.BORDER, padx=1, pady=1)
        self.value_frame.pack(side="left", fill="x", expand=True, padx=4)
        
        self.value_label = tk.Label(
            self.value_frame,
            textvariable=variable,
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 11),
            pady=6,
        )
        self.value_label.pack(fill="x")
        
        # Increment button
        self.btn_inc = tk.Button(
            self.control_frame,
            text="+",
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            width=3,
            command=self.increment_value,
            activebackground=Theme.ACCENT,
            activeforeground="white",
        )
        self.btn_inc.pack(side="right")
    
    def increment_value(self):
        try:
            current = float(self.variable.get()) if isinstance(self.variable, tk.StringVar) else self.variable.get()
            new_val = min(self.to, current + self.increment)
            if isinstance(self.variable, tk.IntVar):
                self.variable.set(int(new_val))
            elif isinstance(self.variable, tk.DoubleVar):
                self.variable.set(round(new_val, 2))
            else:
                self.variable.set(str(round(new_val, 2)))
            if self.command:
                self.command()
        except ValueError:
            pass
    
    def decrement(self):
        try:
            current = float(self.variable.get()) if isinstance(self.variable, tk.StringVar) else self.variable.get()
            new_val = max(self.from_, current - self.increment)
            if isinstance(self.variable, tk.IntVar):
                self.variable.set(int(new_val))
            elif isinstance(self.variable, tk.DoubleVar):
                self.variable.set(round(new_val, 2))
            else:
                self.variable.set(str(round(new_val, 2)))
            if self.command:
                self.command()
        except ValueError:
            pass


class ModernSlider(tk.Frame):
    """Modern styled slider with value display"""
    
    def __init__(self, parent, label: str, variable, 
                 from_: float, to: float, resolution: float = 1,
                 command=None, **kwargs):
        super().__init__(parent, bg=Theme.BG_CARD, **kwargs)
        
        self.variable = variable
        self.command = command
        
        # Header with label and value
        self.header = tk.Frame(self, bg=Theme.BG_CARD)
        self.header.pack(fill="x")
        
        self.label = tk.Label(self.header, text=label, bg=Theme.BG_CARD,
                              fg=Theme.TEXT_SECONDARY, font=("Segoe UI", 9))
        self.label.pack(side="left")
        
        self.value_label = tk.Label(self.header, textvariable=variable, bg=Theme.BG_CARD,
                                    fg=Theme.ACCENT, font=("Segoe UI", 10, "bold"))
        self.value_label.pack(side="right")
        
        # Slider
        self.slider = tk.Scale(
            self,
            from_=from_,
            to=to,
            resolution=resolution,
            orient="horizontal",
            variable=variable,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            troughcolor=Theme.BG_LIGHT,
            highlightthickness=0,
            showvalue=False,
            sliderrelief="flat",
            command=self._on_change,
        )
        self.slider.pack(fill="x", pady=(4, 0))
    
    def _on_change(self, value):
        if self.command:
            self.command()


class SectionHeader(tk.Frame):
    """Collapsible section header"""
    
    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, bg=Theme.BG_DARK, **kwargs)
        
        self.title_label = tk.Label(
            self,
            text=f"  {title}",
            bg=Theme.BG_DARK,
            fg=Theme.ACCENT,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        self.title_label.pack(fill="x", pady=(16, 8), padx=8)
        
        # Separator line
        self.separator = tk.Frame(self, bg=Theme.BORDER, height=1)
        self.separator.pack(fill="x", padx=8)


class StatusBar(tk.Frame):
    """Status bar with save indicator"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Theme.BG_MEDIUM, **kwargs)
        
        self.status_label = tk.Label(
            self,
            text="Ready",
            bg=Theme.BG_MEDIUM,
            fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side="left", padx=12, pady=8)
        
        self.save_indicator = tk.Label(
            self,
            text="●",
            bg=Theme.BG_MEDIUM,
            fg=Theme.SUCCESS,
            font=("Segoe UI", 12),
        )
        self.save_indicator.pack(side="right", padx=12)
        
        self.save_text = tk.Label(
            self,
            text="Auto-save ON",
            bg=Theme.BG_MEDIUM,
            fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 9),
        )
        self.save_text.pack(side="right")
    
    def set_status(self, text: str, color: str = None):
        self.status_label.configure(text=text)
        if color:
            self.status_label.configure(fg=color)
    
    def flash_save(self):
        """Flash the save indicator"""
        self.save_indicator.configure(fg=Theme.ACCENT)
        self.save_text.configure(text="Saved!", fg=Theme.ACCENT)
        self.after(1000, self._reset_save_indicator)
    
    def _reset_save_indicator(self):
        self.save_indicator.configure(fg=Theme.SUCCESS)
        self.save_text.configure(text="Auto-save ON", fg=Theme.TEXT_MUTED)


# =============================================================================
# MAIN APPLICATION
# =============================================================================
class ControlPanelApp:
    """Main application class"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Scry Control Panel")
        self.root.geometry("680x800")
        self.root.configure(bg=Theme.BG_DARK)
        self.root.minsize(600, 600)
        
        # Try to set icon
        try:
            icon_path = PROJECT_ROOT / "src" / "assets" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass
        
        self.env_path = PROJECT_ROOT / ".env"
        self.variables: Dict[str, tk.Variable] = {}
        self.save_pending = False
        
        self._create_widgets()
        self._load_values()
    
    def _create_widgets(self):
        """Create all UI widgets"""
        
        # Header
        header = tk.Frame(self.root, bg=Theme.BG_MEDIUM)
        header.pack(fill="x")
        
        title = tk.Label(
            header,
            text="⚙️  Scry Control Panel",
            bg=Theme.BG_MEDIUM,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 18, "bold"),
            pady=16,
        )
        title.pack()
        
        subtitle = tk.Label(
            header,
            text="Configure your environment settings. Changes are saved automatically.",
            bg=Theme.BG_MEDIUM,
            fg=Theme.TEXT_MUTED,
            font=("Segoe UI", 10),
        )
        subtitle.pack(pady=(0, 12))
        
        # Scrollable content area
        canvas_container = tk.Frame(self.root, bg=Theme.BG_DARK)
        canvas_container.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(canvas_container, bg=Theme.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)
        
        self.content_frame = tk.Frame(self.canvas, bg=Theme.BG_DARK)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        
        # Bind resize events
        self.content_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Bind mouse wheel
        self.root.bind("<MouseWheel>", self._on_mousewheel)
        
        # Create sections
        for section_name, variables in CONFIG_SCHEMA.items():
            self._create_section(section_name, variables)
        
        # Status bar
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill="x", side="bottom")
        
        # Add button bar
        button_bar = tk.Frame(self.root, bg=Theme.BG_MEDIUM)
        button_bar.pack(fill="x", side="bottom", before=self.status_bar)
        
        # Reload button
        reload_btn = tk.Button(
            button_bar,
            text="↻ Reload",
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 10),
            relief="flat",
            padx=16,
            pady=8,
            command=self._load_values,
            activebackground=Theme.ACCENT,
            activeforeground="white",
        )
        reload_btn.pack(side="left", padx=12, pady=12)
        
        # Open .env button
        open_btn = tk.Button(
            button_bar,
            text="📄 Open .env",
            bg=Theme.BG_LIGHT,
            fg=Theme.TEXT_PRIMARY,
            font=("Segoe UI", 10),
            relief="flat",
            padx=16,
            pady=8,
            command=self._open_env_file,
            activebackground=Theme.ACCENT,
            activeforeground="white",
        )
        open_btn.pack(side="left", padx=8, pady=12)
        
        # Reset defaults button
        reset_btn = tk.Button(
            button_bar,
            text="⟲ Reset Defaults",
            bg=Theme.WARNING,
            fg="#000000",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=16,
            pady=8,
            command=self._reset_defaults,
            activebackground=Theme.ERROR,
            activeforeground="white",
        )
        reset_btn.pack(side="right", padx=12, pady=12)
    
    def _create_section(self, section_name: str, variables: list):
        """Create a section with controls for each variable"""
        
        header = SectionHeader(self.content_frame, section_name)
        header.pack(fill="x")
        
        # Card container for this section
        card = tk.Frame(self.content_frame, bg=Theme.BG_CARD, padx=16, pady=12)
        card.pack(fill="x", padx=16, pady=(0, 8))
        
        for i, var_config in enumerate(variables):
            if i > 0:
                # Separator between items
                sep = tk.Frame(card, bg=Theme.BORDER, height=1)
                sep.pack(fill="x", pady=12)
            
            self._create_control(card, var_config)
    
    def _create_control(self, parent: tk.Frame, config: dict):
        """Create appropriate control widget based on variable type"""
        
        key = config["key"]
        var_type = config["type"]
        default = config.get("default", "")
        desc = config.get("desc", key)
        tooltip = config.get("tooltip", "")
        
        # Create control row
        row = tk.Frame(parent, bg=Theme.BG_CARD)
        row.pack(fill="x", pady=4)
        
        if var_type == "bool":
            # Toggle switch layout
            label_frame = tk.Frame(row, bg=Theme.BG_CARD)
            label_frame.pack(side="left", fill="x", expand=True)
            
            label = tk.Label(label_frame, text=desc, bg=Theme.BG_CARD,
                           fg=Theme.TEXT_PRIMARY, font=("Segoe UI", 11))
            label.pack(anchor="w")
            
            if tooltip:
                hint = tk.Label(label_frame, text=tooltip, bg=Theme.BG_CARD,
                              fg=Theme.TEXT_MUTED, font=("Segoe UI", 9))
                hint.pack(anchor="w")
            
            var = tk.BooleanVar(value=default)
            self.variables[key] = var
            
            toggle = ToggleSwitch(row, var, command=lambda k=key: self._save_value(k))
            toggle.pack(side="right", padx=(16, 0))
            
        elif var_type in ("int", "float"):
            min_val = config.get("min", 0)
            max_val = config.get("max", 100)
            step = config.get("step", 1 if var_type == "int" else 0.1)
            
            if var_type == "int":
                var = tk.IntVar(value=default)
            else:
                var = tk.DoubleVar(value=default)
            self.variables[key] = var
            
            # For small ranges, use spinbox; else slider
            if (max_val - min_val) > 50:
                slider = ModernSlider(
                    row, desc, var, min_val, max_val, step,
                    command=lambda k=key: self._save_value(k)
                )
                slider.pack(fill="x")
                
                if tooltip:
                    hint = tk.Label(row, text=tooltip, bg=Theme.BG_CARD,
                                  fg=Theme.TEXT_MUTED, font=("Segoe UI", 9))
                    hint.pack(anchor="w")
            else:
                spinbox = ModernSpinbox(
                    row, desc, var, min_val, max_val, step,
                    command=lambda k=key: self._save_value(k)
                )
                spinbox.pack(fill="x")
                
                if tooltip:
                    hint = tk.Label(row, text=tooltip, bg=Theme.BG_CARD,
                                  fg=Theme.TEXT_MUTED, font=("Segoe UI", 9))
                    hint.pack(anchor="w", pady=(4, 0))
        
        elif var_type == "password":
            var = tk.StringVar(value=str(default))
            self.variables[key] = var
            
            entry = ModernEntry(row, desc, var, show="•",
                              command=lambda k=key: self._save_value(k))
            entry.pack(fill="x")
            
            if tooltip:
                hint = tk.Label(row, text=tooltip, bg=Theme.BG_CARD,
                              fg=Theme.TEXT_MUTED, font=("Segoe UI", 9))
                hint.pack(anchor="w", pady=(4, 0))
        
        else:  # str
            var = tk.StringVar(value=str(default))
            self.variables[key] = var
            
            entry = ModernEntry(row, desc, var,
                              command=lambda k=key: self._save_value(k))
            entry.pack(fill="x")
            
            if tooltip:
                hint = tk.Label(row, text=tooltip, bg=Theme.BG_CARD,
                              fg=Theme.TEXT_MUTED, font=("Segoe UI", 9))
                hint.pack(anchor="w", pady=(4, 0))
    
    def _on_frame_configure(self, event):
        """Update scroll region when content changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Adjust content width when canvas is resized"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _load_values(self):
        """Load current values from .env file"""
        try:
            if self.env_path.exists():
                values = {}
                with open(self.env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            values[k.strip()] = v.strip()
                
                # Update variables
                for key, var in self.variables.items():
                    if key in values:
                        val = values[key]
                        if isinstance(var, tk.BooleanVar):
                            var.set(val.lower() in ("true", "1", "yes", "on"))
                        elif isinstance(var, tk.IntVar):
                            try:
                                var.set(int(val))
                            except ValueError:
                                pass
                        elif isinstance(var, tk.DoubleVar):
                            try:
                                var.set(float(val))
                            except ValueError:
                                pass
                        else:
                            var.set(val)
                
                self.status_bar.set_status(f"Loaded from: {self.env_path}", Theme.SUCCESS)
            else:
                self.status_bar.set_status("No .env file found - using defaults", Theme.WARNING)
        except Exception as e:
            self.status_bar.set_status(f"Error loading: {e}", Theme.ERROR)
    
    def _save_value(self, key: str):
        """Save a single value to .env file"""
        try:
            # Ensure .env exists
            if not self.env_path.exists():
                with open(self.env_path, "w") as f:
                    f.write("# Scry Configuration\n")
            
            var = self.variables[key]
            if isinstance(var, tk.BooleanVar):
                value = "True" if var.get() else "False"
            else:
                value = str(var.get())
            
            set_key(str(self.env_path), key, value)
            
            self.status_bar.flash_save()
            self.status_bar.set_status(f"Saved: {key}", Theme.SUCCESS)
        except Exception as e:
            self.status_bar.set_status(f"Error saving: {e}", Theme.ERROR)
    
    def _open_env_file(self):
        """Open .env file in system editor"""
        try:
            if sys.platform == "win32":
                os.startfile(str(self.env_path))
            elif sys.platform == "darwin":
                os.system(f"open '{self.env_path}'")
            else:
                os.system(f"xdg-open '{self.env_path}'")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
    
    def _reset_defaults(self):
        """Reset all values to defaults"""
        if not messagebox.askyesno("Confirm Reset", 
            "This will reset ALL settings to their default values.\n\n"
            "Your API key will be preserved.\n\n"
            "Continue?"):
            return
        
        # Preserve API key
        api_key = self.variables.get("GEMINI_API_KEY")
        saved_key = api_key.get() if api_key else ""
        
        # Reset all values
        for section_vars in CONFIG_SCHEMA.values():
            for config in section_vars:
                key = config["key"]
                default = config.get("default", "")
                
                if key in self.variables:
                    var = self.variables[key]
                    if isinstance(var, tk.BooleanVar):
                        var.set(bool(default))
                    elif isinstance(var, tk.IntVar):
                        var.set(int(default))
                    elif isinstance(var, tk.DoubleVar):
                        var.set(float(default))
                    else:
                        var.set(str(default))
                    
                    self._save_value(key)
        
        # Restore API key
        if saved_key and api_key:
            api_key.set(saved_key)
            self._save_value("GEMINI_API_KEY")
        
        self.status_bar.set_status("Reset to defaults complete", Theme.SUCCESS)


def main():
    """Main entry point"""
    root = tk.Tk()
    
    # Style configuration for ttk widgets
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Vertical.TScrollbar",
                   background=Theme.BG_LIGHT,
                   troughcolor=Theme.BG_DARK,
                   arrowcolor=Theme.TEXT_SECONDARY)
    
    app = ControlPanelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
