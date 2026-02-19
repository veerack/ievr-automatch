# base/qt_gui.py

import sys
import threading
import platform
import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QUrl, Signal, QPropertyAnimation, QItemSelectionModel, QRect
from PySide6.QtGui import QTextCursor, QIcon, QPalette, QColor, QFont, QDesktopServices, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QFormLayout,
    QLineEdit,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QStatusBar,
    QGroupBox,
    QFrame,
    QSizePolicy,
    QSlider,
    QScrollArea,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QListView,
    QAbstractItemView,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
)

from . import common
from .bot import bot_main
from .window_helpers import recalibrate_offsets_via_gui
from .tools import gui_test_focus, gui_test_play_click, gui_test_search_pixel, resource_path
from .ramen import run_ramen_trainer
from .beans.blue import run_blue_beans_trainer
from .beans.pink import run_pink_beans_trainer
# =========================
#   MAIN WINDOW
# =========================

class HoverListView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid() and self.selectionModel():
            self.selectionModel().select(
                index,
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
        super().mouseMoveEvent(event)

class ModeItemDelegate(QStyledItemDelegate):
    def __init__(self, wip_modes: set[str], parent=None):
        super().__init__(parent)
        self._wip_modes = set(wip_modes)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style() if opt.widget else QApplication.style()

        mode_data = index.data(Qt.UserRole)
        is_wip = mode_data in self._wip_modes

        # draw normal item (icon + text, selection bg, etc.)
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter)

        if not is_wip:
            return

        # draw yellow "W.I.P" pill on the right
        text_rect = style.subElementRect(QStyle.SE_ItemViewItemText, opt, None)
        metrics = opt.fontMetrics
        pill_text = "W.I.P"

        pad_h = 6
        pad_v = 2
        pill_w = metrics.horizontalAdvance(pill_text) + pad_h * 2
        pill_h = metrics.height() + pad_v * 2

        pill_x = text_rect.right() - pill_w - 8
        pill_y = text_rect.center().y() - pill_h // 2

        pill_rect = QRect(pill_x, pill_y, pill_w, pill_h)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QColor("#facc15"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(pill_rect, 8, 8)

        painter.setPen(QColor("#111827"))
        painter.drawText(pill_rect, Qt.AlignCenter, pill_text)
        painter.restore()
        
class IEVRModeCombo(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fade_anim = None

    def showPopup(self):
        super().showPopup()

        # The popup for the view is a separate window
        popup = self.view().window()
        if not popup:
            return

        popup.setWindowOpacity(0.0)
        anim = QPropertyAnimation(popup, b"windowOpacity", popup)
        anim.setDuration(140)          # tweak if you want faster/slower
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()
        self._fade_anim = anim         # keep a reference

    # Optional: simple hide; no animation needed
    # def hidePopup(self):
    #     super().hidePopup()

class IEVRMainWindow(QMainWindow):
    update_available = Signal(str)
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IEVR Helper")
        self.setWindowIcon(QIcon("assets/icons/icon.ico"))
        self.resize(1200, 680)

        # Bot state
        self.stop_event = threading.Event()
        self.bot_thread: threading.Thread | None = None
        self.matches_played = 0
        self.total_match_time = 0.0
        self.last_match_time = None
        self.match_history: list[dict] = []
        
        self.ramen_thread: threading.Thread | None = None
        
        self._build_ui()
        self.log_lines = []
        self._connect_signals()
        self._populate_system_info()

        # log timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_queues)
        self.timer.start(90)

        # game window status timer
        self.info_timer = QTimer(self)
        self.info_timer.timeout.connect(self._update_game_window_status)
        self.info_timer.start(1500)

        self.update_available.connect(self._show_update_badge)
        QTimer.singleShot(300, self._check_for_update)

        common.log("INFO", "Qt GUI initialized.")

    # ---------- SYSTEM INFO / GAME WINDOW ----------

    def _populate_system_info(self):
        # Usa direttamente quello che abbiamo trovato in common.HARDWARE_INFO
        info = common.HARDWARE_INFO

        os_label = info.get("os") or f"{platform.system()} {platform.release()}"
        self.lbl_os.setText(f"OS: {os_label}")

        self.lbl_keyboard.setText(f"Keyboard: {info.get('keyboard', 'Unknown')}")
        self.lbl_keyboard_conn.setText(
            f"Connected via: {info.get('keyboard_conn', 'Unknown')}"
        )
        self.lbl_mouse.setText(f"Mouse: {info.get('mouse', 'Unknown')}")
        self.lbl_mouse_conn.setText(
            f"Connected via: {info.get('mouse_conn', 'Unknown')}"
        )

        # Versione tool
        self.lbl_tool_version.setText(f"Tool version: {common.APP_VERSION}")

    def _update_game_window_status(self):
        active = False
        try:
            import pygetwindow as gw
            wins = gw.getWindowsWithTitle(common.GAME_WINDOW_TITLE)
            if wins:
                win = wins[0]
                # alcuni wrapper usano .isActive, altri .isActive()
                is_active = getattr(win, "isActive", None)
                active = is_active() if callable(is_active) else bool(is_active)
        except Exception:
            active = False

        if active:
            self.lbl_game_window.setText("Game window: Active")
            self.lbl_game_window.setStyleSheet("color: #22c55e;")
        else:
            self.lbl_game_window.setText("Game window: Inactive")
            self.lbl_game_window.setStyleSheet("color: #f97373;")

    # ---------- UPDATE CHECKER ----------

    def _check_for_update(self):
        def worker():
            latest = common.fetch_latest_version()
            if not latest:
                return

            latest = latest.strip()
            current = common.APP_VERSION.strip()

            if latest != current:
                common.log("DEBUG", f"GitHub latest={latest!r}, local={current!r}")
                # thread-safe: emette verso il main thread
                self.update_available.emit(latest)

        threading.Thread(target=worker, daemon=True).start()

    def _show_update_badge(self, latest_tag: str):
        self.btn_update.setVisible(True)
        self.lbl_tool_version.setText(
            f"Tool version: {common.APP_VERSION}  •  Latest: {latest_tag}"
        )

    def _open_releases_page(self):
        import webbrowser
        webbrowser.open(f"https://github.com/{common.GITHUB_REPO}/releases")

    # ---------------- UI BUILD ----------------

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ----- SIDEBAR -----
        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        # ----- MAIN AREA -----
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        header = self._build_header()
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.North)

        logs_tab = self._build_logs_tab()
        settings_tab = self._build_settings_tab()
        diag_tab = self._build_diag_tab()
        stats_tab = self._build_stats_tab()

        self.tabs.addTab(logs_tab, "Logs")
        self.tabs.addTab(settings_tab, "Settings")
        self.tabs.addTab(diag_tab, "Diagnostics")
        self.tabs.addTab(stats_tab, "Stats")

        main_layout.addWidget(self.tabs)

        # ----- STATUS BAR -----
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self.lbl_stats = QLabel("Matches: 0  •  Avg: --:--  •  Last: --:--")
        status_bar.addPermanentWidget(self.lbl_stats)

        root.addWidget(main)

    def on_run_diag(self):
        import sys as _sys
        import platform
        import pyautogui
        import pygetwindow as gw
        from ctypes import windll, wintypes, byref  # <— aggiunto

        # OS / Python
        self.lbl_diag_os.setText(f"{platform.system()} {platform.release()}")
        self.lbl_diag_py.setText(_sys.version.split()[0])

        # Screen
        sw, sh = pyautogui.size()
        self.lbl_diag_screen.setText(f"{sw} x {sh}")

        # Game window + resolution
        target_w, target_h = 1024, 576
        try:
            wins = gw.getWindowsWithTitle(common.GAME_WINDOW_TITLE)
        except Exception as e:
            self.lbl_diag_game_win.setText(f"Error: {e}")
            self.lbl_diag_game_win.setStyleSheet("color: #f97373; font-weight: 600;")
            self.lbl_diag_game_res.setText("Unknown")
            self.lbl_diag_game_res.setStyleSheet("color: #f97373; font-weight: 600;")
            self.lbl_diag_resolution_hint.setText(
                "⚠ Could not query the game window. Make sure the game is open "
                "on the primary monitor in windowed mode."
            )
            self.lbl_diag_resolution_hint.setStyleSheet("color: #f97373;")
        else:
            if wins:
                win = wins[0]
                self.lbl_diag_game_win.setText(f"YES ({win.title})")
                self.lbl_diag_game_win.setStyleSheet("color: #22c55e; font-weight: 600;")

                # ---- QUI USIAMO LA CLIENT AREA, NON win.width/height ----
                gw_w = gw_h = None
                try:
                    hwnd = win._hWnd  # handle della finestra (pygetwindow su Windows)
                    rect = wintypes.RECT()
                    windll.user32.GetClientRect(hwnd, byref(rect))
                    gw_w = rect.right - rect.left
                    gw_h = rect.bottom - rect.top
                except Exception:
                    # fallback: usiamo comunque width/height esterni se qualcosa va storto
                    gw_w, gw_h = win.width, win.height

                self.lbl_diag_game_res.setText(f"{gw_w} x {gw_h}")

                if gw_w == target_w and gw_h == target_h:
                    # OK
                    self.lbl_diag_game_res.setStyleSheet(
                        "color: #22c55e; font-weight: 600;"
                    )
                    self.lbl_diag_resolution_hint.setText(
                        "Resolution OK. Offsets are calibrated for 1024 x 576 windowed."
                    )
                    self.lbl_diag_resolution_hint.setStyleSheet("color: #9ca3af;")
                else:
                    # ⚠ sbagliata → rosso
                    self.lbl_diag_game_res.setStyleSheet(
                        "color: #f97373; font-weight: 600;"
                    )
                    self.lbl_diag_resolution_hint.setText(
                        "⚠ Game window is not 1024 x 576 in its client area. "
                        "For reliable clicks, set the game to 1024 x 576 windowed "
                        "and run 'Recalibrate offsets' from the Logs tab."
                    )
                    self.lbl_diag_resolution_hint.setStyleSheet("color: #f97373;")
            else:
                self.lbl_diag_game_win.setText("NO")
                self.lbl_diag_game_win.setStyleSheet(
                    "color: #f97373; font-weight: 600;"
                )
                self.lbl_diag_game_res.setText("Unknown")
                self.lbl_diag_game_res.setStyleSheet(
                    "color: #f97373; font-weight: 600;"
                )
                self.lbl_diag_resolution_hint.setText(
                    "⚠ Game window not found. Open it on the primary monitor "
                    "in 1024 x 576 windowed mode before starting the bot."
                )
                self.lbl_diag_resolution_hint.setStyleSheet("color: #f97373;")

        # FAILSAFE status
        fs_on = pyautogui.FAILSAFE
        self.lbl_diag_failsafe.setText("ON" if fs_on else "OFF")
        self.lbl_diag_failsafe.setStyleSheet(
            "color: #22c55e; font-weight: 600;" if fs_on
            else "color: #f97373; font-weight: 600;"
        )

        common.log("INFO", "Diagnostics completed.")

    def _build_stats_tab(self) -> QWidget:
        tab = QWidget()
        tab.setObjectName("statsTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ------- SUMMARY CARD -------
        summary_frame = QFrame()
        summary_frame.setObjectName("card")
        s_layout = QVBoxLayout(summary_frame)
        s_layout.setContentsMargins(10, 8, 10, 8)
        s_layout.setSpacing(4)

        self.lbl_stats_summary = QLabel("No matches recorded yet.")
        self.lbl_stats_summary.setObjectName("fieldDescription")
        s_layout.addWidget(self.lbl_stats_summary)

        layout.addWidget(summary_frame)

        # ------- OUTER CARD (same look as other cards) -------
        outer = QFrame()
        outer.setObjectName("card")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(4)

        # ------- INNER ROUNDED CONTAINER JUST FOR TABLE -------
        table_container = QFrame()
        table_container.setObjectName("tableContainer")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(4, 4, 4, 0)
        table_layout.setSpacing(0)

        # Table itself
        self.tbl_matches = QTableWidget()
        self.tbl_matches.setColumnCount(4)
        self.tbl_matches.setHorizontalHeaderLabels(
            ["#", "Time", "Duration (s)", "Running avg (s)"]
        )

        header = self.tbl_matches.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.tbl_matches.verticalHeader().setVisible(False)
        self.tbl_matches.setShowGrid(False)
        self.tbl_matches.setAlternatingRowColors(False)
        self.tbl_matches.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_matches.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl_matches.setFocusPolicy(Qt.NoFocus)
        self.tbl_matches.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tbl_matches.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        table_layout.addWidget(self.tbl_matches)
        outer_layout.addWidget(table_container)

        layout.addWidget(outer, 1)

        return tab
    
    def _build_diag_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Piccola descrizione
        desc = QLabel(
            "Quick check to make sure your setup matches the recommended settings."
        )
        desc.setObjectName("fieldDescription")
        layout.addWidget(desc)

        # Pulsante grande al centro
        self.btn_run_diag = QPushButton("Run Diagnostics")
        self.btn_run_diag.setObjectName("primaryButton")
        self.btn_run_diag.setMinimumHeight(36)
        self.btn_run_diag.clicked.connect(self.on_run_diag)
        layout.addWidget(self.btn_run_diag)

        # Card con le info
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)

        # Row helper
        def make_row(label_text):
            label = QLabel(label_text)
            value = QLabel("--")
            value.setStyleSheet("font-weight: 500;")
            form.addRow(label, value)
            return value

        self.lbl_diag_os = make_row("OS:")
        self.lbl_diag_py = make_row("Python:")
        self.lbl_diag_screen = make_row("Screen resolution:")
        self.lbl_diag_game_win = make_row("Game window detected:")
        self.lbl_diag_game_res = make_row("Game window resolution:")
        self.lbl_diag_failsafe = make_row("PyAutoGUI FAILSAFE:")

        card_layout.addLayout(form)

        # Hint sulla risoluzione
        self.lbl_diag_resolution_hint = QLabel("")
        self.lbl_diag_resolution_hint.setObjectName("fieldDescription")
        self.lbl_diag_resolution_hint.setWordWrap(True)
        card_layout.addWidget(self.lbl_diag_resolution_hint)

        layout.addWidget(card)

        layout.addStretch()
        return tab

    def _build_sidebar(self) -> QWidget:
        w = QWidget()
        w.setObjectName("sidebar")
        w.setFixedWidth(230)

        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Logo / title
        title = QLabel("IEVR Helper")
        title_font = QFont("Segoe UI", 14, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel("Select a mode below and start")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 11px;")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # --- MODE LABEL + COMBO (vertical, full width) ---
        self.combo_mode = IEVRModeCombo()
        self.combo_mode.setObjectName("modeCombo")

        # which modes are W.I.P
        wip_modes = {
            "beans_red",
            "beans_green",
            "beans_orange",
            "beans_yellow",
            "beans_light_blue",
        }

        # custom hover view + delegate
        view = HoverListView(self.combo_mode)
        view.setItemDelegate(ModeItemDelegate(wip_modes, view))
        self.combo_mode.setView(view)

        def add_mode(icon, text, data, wip=False):
            # label is ALWAYS plain text; W.I.P badge is drawn by delegate
            self.combo_mode.addItem(QIcon(resource_path(icon)), text, data)

        add_mode("assets/sidebar/inazuma.gif", "Ranked Match", "ranked")
        add_mode("assets/sidebar/ramen.png", "Ramen Trainer", "ramen")

        add_mode("assets/sidebar/red_bean.png", "Red Beans Trainer", "beans_red", wip=True)
        add_mode("assets/sidebar/green_bean.png", "Green Beans Trainer", "beans_green", wip=True)

        add_mode("assets/sidebar/blue_bean.png", "Blue Beans Trainer", "beans_blue")
        add_mode("assets/sidebar/pink_bean.png", "Pink Beans Trainer", "beans_pink")

        add_mode("assets/sidebar/orange_bean.png", "Orange Beans Trainer", "beans_orange", wip=True)
        add_mode("assets/sidebar/yellow_bean.png", "Yellow Beans Trainer", "beans_yellow", wip=True)
        add_mode("assets/sidebar/light_blue_bean.png", "Light Blue Beans Trainer", "beans_light_blue", wip=True)

        self.combo_mode.setMinimumHeight(28)
        self.combo_mode.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        layout.addWidget(self.combo_mode)

        # Track last valid selection
        self._last_valid_mode_index = self.combo_mode.currentIndex()

        # Intercept selection changes
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)

        layout.addSpacing(8)

        view = self.combo_mode.view()
        view.setMouseTracking(True)
        view.viewport().setMouseTracking(True)

        # Start / Stop
        self.btn_start = QPushButton("▶  Start")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setMinimumHeight(40)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹  Stop")
        self.btn_stop.setObjectName("secondaryButton")
        self.btn_stop.setMinimumHeight(34)
        self.btn_stop.setEnabled(False)
        layout.addWidget(self.btn_stop)

        layout.addSpacing(10)

        # --------- SYSTEM / TOOL INFO CARD ----------
        card = QFrame()
        card.setObjectName("infoCard")
        info_layout = QVBoxLayout(card)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(2)

        # Prima riga: stato input OS
        self.lbl_os_input = QLabel("OS input: ready")
        self.lbl_os_input.setStyleSheet("color: #e5e7eb; font-weight: 500; font-size: 11px;")
        info_layout.addWidget(self.lbl_os_input)

        info_layout.addSpacing(4)

        info = common.HARDWARE_INFO

        self.lbl_os = QLabel(f"OS: {info.get('os', 'Unknown')}")
        self.lbl_keyboard = QLabel(f"Keyboard: {info.get('keyboard', 'Unknown')}")
        self.lbl_keyboard_conn = QLabel(
            f"Connected via: {info.get('keyboard_conn', 'Unknown')}"
        )
        self.lbl_mouse = QLabel(f"Mouse: {info.get('mouse', 'Unknown')}")
        self.lbl_mouse_conn = QLabel(
            f"Connected via: {info.get('mouse_conn', 'Unknown')}"
        )
        self.lbl_game_window = QLabel("Game window: Inactive")
        self.lbl_game_window.setObjectName("gameStatusLabel")

        self.lbl_tool_version = QLabel(f"Tool version: {common.APP_VERSION}")

        # Update button (hidden by default)
        self.btn_update = QPushButton("UPDATE AVAILABLE")
        self.btn_update.setObjectName("updateButton")
        self.btn_update.setVisible(False)
        self.btn_update.clicked.connect(self._open_releases_page)

        for lbl in (
            self.lbl_os,
            self.lbl_keyboard,
            self.lbl_keyboard_conn,
            self.lbl_mouse,
            self.lbl_mouse_conn,
            self.lbl_game_window,
            self.lbl_tool_version,
        ):
            info_layout.addWidget(lbl)

        # unico pulsante update
        self.btn_update = QPushButton("UPDATE AVAILABLE")
        self.btn_update.setObjectName("updateButton")
        self.btn_update.setVisible(False)
        self.btn_update.setMinimumHeight(24)
        info_layout.addSpacing(4)
        info_layout.addWidget(self.btn_update)

        layout.addWidget(card)

        layout.addStretch()

        # Small footer
        footer_line = QFrame()
        footer_line.setFrameShape(QFrame.HLine)
        footer_line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(footer_line)

        # Clickable footer with custom link color (no green, custom hover)
        self.footer_label = QLabel()
        self.footer_label.setTextFormat(Qt.RichText)
        self.footer_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.footer_label.setOpenExternalLinks(False)  # we will handle opening

        self._footer_normal = (
            'Made by '
            '<a href="https://discord.com/users/144126010642792449">'
            '<span style="color:#3b82f6; text-decoration:none;">@veerack</span>'
            '</a><br>'
            '<span style="color:#6b7280;">NOT AFFILIATED WITH LEVEL-5.</span>'
        )
        self._footer_hover = (
            'Made by '
            '<a href="https://discord.com/users/144126010642792449">'
            '<span style="color:#1e40af; text-decoration:underline;">@veerack</span>'
            '</a><br>'
            '<span style="color:#6b7280;">NOT AFFILIATED WITH LEVEL-5.</span>'
        )

        self.footer_label.setText(self._footer_normal)
        self.footer_label.setStyleSheet("font-size: 14px; cursor: pointer;")
        self.footer_label.linkActivated.connect(self._open_footer_link)
        self.footer_label.linkHovered.connect(self._on_footer_hover)

        layout.addWidget(self.footer_label)

        self.btn_quit = QPushButton("Quit")
        self.btn_quit.setObjectName("dangerButton")
        self.btn_quit.setMinimumHeight(30)
        layout.addWidget(self.btn_quit)

        return w

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerCard")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(18)

        # ---------- LEFT SIDE: TITLE + TEXT ----------
        left = QWidget()
        l_layout = QVBoxLayout(left)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(4)

        # Big title line 🌩
        title = QLabel("HOW THIS WORKS?")
        title_font = QFont("Segoe UI Semibold", 20, QFont.Bold)
        title.setFont(title_font)
        l_layout.addWidget(title)

        # Description (same as before)
        description = QLabel(
            "- Leave the game open while you sleep/work and come back to some orbs.\n"
            "- No memory editing, no injection, no network tampering - just mouse & keyboard automation.\n"
            "- Tune timings in the Settings tab based on your PC load times and connection speed."
        )
        description.setStyleSheet("color: #9ca3af; font-size: 11px;")
        description.setWordWrap(True)
        l_layout.addWidget(description)

        # Window title + key line
        cfg_label = QLabel(
            f'Window title: "{common.GAME_WINDOW_TITLE}"   •   '
            f'Auto-mode key: "{common.AUTO_MODE_KEY.upper()}"'
        )
        cfg_label.setStyleSheet("color: #6b7280; font-size: 10px;")
        l_layout.addWidget(cfg_label)
        self._cfg_label = cfg_label

        header_layout.addWidget(left, 1)

        # ---------- RIGHT SIDE: STATUS PILL ----------
        right = QWidget()
        r_layout = QVBoxLayout(right)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(4)
        r_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet(
            "background-color: #6b7280; border-radius: 6px;"
        )
        row.addWidget(self.status_dot)

        self.lbl_status_header = QLabel("Status: idle")
        row.addWidget(self.lbl_status_header)
        row.addStretch()

        r_layout.addLayout(row)

        hint = QLabel(
            'Select a mode from the list, make sure the game is open and visible, then press Start.'
        )
        hint.setStyleSheet("color: #9ca3af; font-size: 10px;")
        r_layout.addWidget(hint)

        header_layout.addWidget(right, 0)

        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return header

    def _build_logs_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Tools row
        tools_row = QWidget()
        t_layout = QHBoxLayout(tools_row)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(6)

        self.btn_recalib = QPushButton("♻  Recalibrate offsets")
        self.btn_recalib.setObjectName("ghostButton")
        self.btn_test_focus = QPushButton("🎯  Test focus")
        self.btn_test_focus.setObjectName("ghostButton")
        self.btn_test_click = QPushButton("🖱  Test match button")
        self.btn_test_click.setObjectName("ghostButton")
        self.btn_test_pixel = QPushButton("🧪  Test search pixel")
        self.btn_test_pixel.setObjectName("ghostButton")
        self.btn_copy_logs = QPushButton("📋  Copy logs")
        self.btn_copy_logs.setObjectName("ghostButton")

        self.btn_save_logs = QPushButton("💾  Save logs")
        self.btn_save_logs.setObjectName("ghostButton")

        t_layout.addWidget(self.btn_copy_logs)
        t_layout.addWidget(self.btn_save_logs)

        for b in (
            self.btn_recalib,
            self.btn_test_focus,
            self.btn_test_click,
            self.btn_test_pixel,
        ):
            b.setMinimumHeight(28)
            t_layout.addWidget(b)

        t_layout.addStretch()
        layout.addWidget(tools_row)

        # Logs box
        logs_frame = QFrame()
        logs_frame.setFrameShape(QFrame.StyledPanel)
        logs_frame.setObjectName("card")
        lf_layout = QVBoxLayout(logs_frame)
        lf_layout.setContentsMargins(8, 8, 8, 8)
        lf_layout.setSpacing(4)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setObjectName("logText")
        lf_layout.addWidget(self.txt_logs)

        layout.addWidget(logs_frame, 1)

        return tab

    def _build_settings_tab(self):
        cfg = common.cfg

        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # ---- Scroll area ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(22)

        # -------- CORE TIMING CARD --------
        core_card = QGroupBox()
        core_card.setObjectName("card")
        core_layout = QVBoxLayout(core_card)
        core_layout.setSpacing(10)

        title = QLabel("Core timing")
        title.setObjectName("sectionTitle")
        core_layout.addWidget(title)

        theme_row = QWidget()
        tr_layout = QHBoxLayout(theme_row)
        tr_layout.setContentsMargins(0, 0, 0, 0)
        tr_layout.setSpacing(6)

        lbl_theme = QLabel("Theme:")
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["dark", "light"])
        self.combo_theme.setCurrentText("dark")

        tr_layout.addWidget(lbl_theme)
        tr_layout.addWidget(self.combo_theme)
        tr_layout.addStretch()

        core_layout.addWidget(theme_row)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)

        # Game window title
        self.edit_window_title = QLineEdit(cfg.GAME_WINDOW_TITLE)
        form.addRow("Game window title:", self.edit_window_title)

        # Auto-mode key
        self.edit_auto_key = QLineEdit(cfg.AUTO_MODE_KEY)
        self.edit_auto_key.setMaxLength(2)
        form.addRow("Auto-mode key:", self.edit_auto_key)

        core_layout.addLayout(form)

        # ---- Timings with sliders ----
        def timing_row(label_text, spin_attr_name, value, min_v, max_v, step, desc_text):
            container = QWidget()
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 4, 0, 0)
            v.setSpacing(2)

            lbl = QLabel(label_text)
            v.addWidget(lbl)

            h = QHBoxLayout()
            h.setSpacing(6)

            spin = QDoubleSpinBox()
            spin.setRange(min_v, max_v)
            spin.setSingleStep(step)
            spin.setValue(value)
            spin.setDecimals(1)
            spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
            spin.setFixedWidth(80)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(int(min_v))
            slider.setMaximum(int(max_v))
            slider.setValue(int(value))
            slider.setObjectName("modernSlider")

            def on_slider(val):
                spin.setValue(float(val))

            def on_spin(val):
                slider.setValue(int(val))

            slider.valueChanged.connect(on_slider)
            spin.valueChanged.connect(on_spin)

            h.addWidget(slider)
            h.addWidget(spin)
            v.addLayout(h)

            desc = QLabel(desc_text)
            desc.setObjectName("fieldDescription")
            v.addWidget(desc)

            setattr(self, spin_attr_name, spin)
            core_layout.addWidget(container)

        # Delay before start
        self.spin_delay_start = QDoubleSpinBox()
        self.spin_delay_start.setRange(0.0, 30.0)
        self.spin_delay_start.setSingleStep(0.5)
        self.spin_delay_start.setValue(cfg.DELAY_BEFORE_START)
        self.spin_delay_start.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_delay_start.setFixedWidth(80)
        delay_row = QWidget()
        delay_layout = QHBoxLayout(delay_row)
        delay_layout.setContentsMargins(0, 0, 0, 0)
        delay_layout.setSpacing(6)
        delay_layout.addWidget(QLabel("Delay before start (s):"))
        delay_layout.addWidget(self.spin_delay_start)
        delay_layout.addStretch()
        core_layout.addWidget(delay_row)
        desc_delay = QLabel("Time after pressing Start before the bot performs its first action.")
        desc_delay.setObjectName("fieldDescription")
        core_layout.addWidget(desc_delay)

        # First wait
        timing_row(
            "First wait – search (s):",
            "spin_first_wait",
            cfg.FIRST_WAIT,
            5.0,
            60.0,
            1.0,
            "Time after clicking Ranked Match before checking if the search started."
        )

        # Second wait
        timing_row(
            "Second wait – before auto (s):",
            "spin_second_wait",
            cfg.SECOND_WAIT,
            20.0,
            120.0,
            2.0,
            "Delay before pressing the auto-mode key once the match has loaded."
        )

        # Match duration
        timing_row(
            "Expected match duration (s):",
            "spin_match_duration",
            cfg.MATCH_DURATION,
            120.0,
            1500.0,
            10.0,
            "Used for stats and timeout checks. Does not have to be exact."
        )

        content_layout.addWidget(core_card)

        # -------- SAFETY LIMITS CARD --------
        safety_card = QGroupBox()
        safety_card.setObjectName("card")
        safety_layout = QVBoxLayout(safety_card)
        safety_layout.setSpacing(10)

        title2 = QLabel("Safety & limits")
        title2.setObjectName("sectionTitle")
        safety_layout.addWidget(title2)

        # Post-match clicks + slider
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        lbl_pm = QLabel("Post-match clicks:")
        v.addWidget(lbl_pm)

        h_pm = QHBoxLayout()
        h_pm.setSpacing(6)

        self.spin_post_clicks = QSpinBox()
        self.spin_post_clicks.setRange(5, 40)
        self.spin_post_clicks.setValue(cfg.POST_MATCH_CLICKS)
        self.spin_post_clicks.setButtonSymbols(QSpinBox.NoButtons)
        self.spin_post_clicks.setFixedWidth(60)

        slider_clicks = QSlider(Qt.Horizontal)
        slider_clicks.setMinimum(5)
        slider_clicks.setMaximum(40)
        slider_clicks.setValue(cfg.POST_MATCH_CLICKS)
        slider_clicks.setObjectName("modernSlider")

        slider_clicks.valueChanged.connect(self.spin_post_clicks.setValue)
        self.spin_post_clicks.valueChanged.connect(slider_clicks.setValue)

        h_pm.addWidget(slider_clicks)
        h_pm.addWidget(self.spin_post_clicks)
        v.addLayout(h_pm)

        desc3 = QLabel("Number of clicks to clear result screens and return to Ranked Match.")
        desc3.setObjectName("fieldDescription")
        v.addWidget(desc3)

        safety_layout.addWidget(container)

        # Post-match interval
        self.spin_post_interval = QDoubleSpinBox()
        self.spin_post_interval.setRange(0.05, 1.0)
        self.spin_post_interval.setSingleStep(0.05)
        self.spin_post_interval.setValue(cfg.POST_MATCH_CLICK_INTERVAL)
        self.spin_post_interval.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_post_interval.setFixedWidth(80)

        row_int = QWidget()
        h_int = QHBoxLayout(row_int)
        h_int.setContentsMargins(0, 0, 0, 0)
        h_int.setSpacing(6)
        h_int.addWidget(QLabel("Post-match click interval (s):"))
        h_int.addWidget(self.spin_post_interval)
        h_int.addStretch()
        safety_layout.addWidget(row_int)
        d_int = QLabel("Delay between each cleanup click at the end of a match.")
        d_int.setObjectName("fieldDescription")
        safety_layout.addWidget(d_int)

        # Search interval + slider
        container2 = QWidget()
        v2 = QVBoxLayout(container2)
        v2.setContentsMargins(0, 0, 0, 0)
        v2.setSpacing(2)

        lbl_si = QLabel("Search check interval (s):")
        v2.addWidget(lbl_si)

        h_si = QHBoxLayout()
        h_si.setSpacing(6)

        self.spin_search_interval = QDoubleSpinBox()
        self.spin_search_interval.setRange(5.0, 60.0)
        self.spin_search_interval.setSingleStep(1.0)
        self.spin_search_interval.setValue(cfg.SEARCH_CHECK_INTERVAL)
        self.spin_search_interval.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_search_interval.setFixedWidth(80)

        slider_si = QSlider(Qt.Horizontal)
        slider_si.setMinimum(5)
        slider_si.setMaximum(60)
        slider_si.setValue(int(cfg.SEARCH_CHECK_INTERVAL))
        slider_si.setObjectName("modernSlider")

        slider_si.valueChanged.connect(lambda v: self.spin_search_interval.setValue(float(v)))
        self.spin_search_interval.valueChanged.connect(lambda v: slider_si.setValue(int(v)))

        h_si.addWidget(slider_si)
        h_si.addWidget(self.spin_search_interval)
        v2.addLayout(h_si)

        d_si = QLabel("How often the bot checks whether the match/search has finished.")
        d_si.setObjectName("fieldDescription")
        v2.addWidget(d_si)

        safety_layout.addWidget(container2)

        # Level flag
        self.chk_lvl75 = QCheckBox("All players ≥ lvl 75 (skip extra spam)")
        self.chk_lvl75.setChecked(bool(cfg.LVL_75_PLUS))
        safety_layout.addWidget(self.chk_lvl75)

        d_lvl = QLabel("When enabled, the bot sends fewer confirm clicks on result screens.")
        d_lvl.setObjectName("fieldDescription")
        safety_layout.addWidget(d_lvl)

        # --- CHECKBOX LABEL ---
        self.chk_chiaki = QCheckBox("Chiaki4Deck Mode (PS4/5 Stream)")
        self.chk_chiaki.setChecked(bool(getattr(cfg, "CHIAKI4DECK", False)))
        safety_layout.addWidget(self.chk_chiaki)


        # --- DESCRIPTION LABEL ---
        d_chiaki = QLabel(
            """
            When enabled, the bot uses a virtual DS4 Controller instead of mouse/keyboard.<br>
            Requires ViGEmBus + vgamepad. Mouse-based clicks will NOT work in this mode.<br><br>
            <span style="color:#f87171; font-weight:600;">
            ⚠ Chiaki4Deck must be set to 1024x576 resolution in its app settings (WHICH IS 819x461 in "Video" settings),
            and in the "Stream" section, resolution must be AT LEAST 720p H265 Codec at 30 FPS.<br>
            Still in the Chiaki app, make sure you uncheck the checkbox "Hide cursor" in the "Video" tab to allow the script
            to move the mouse cursor on the window. Also remember to change GAME_WINDOW_TITLE to Chiaki4Deck window title in
            the settings here (first setting).
            </span><br>
            There's different versions out there, but what this app is familiar with is
            <a href="https://github.com/streetpea/chiaki-ng/releases">this one!</a>
            Make sure to download the "Latest" release.
            """
        )

        d_chiaki.setTextFormat(Qt.RichText)
        d_chiaki.setTextInteractionFlags(Qt.TextBrowserInteraction)
        d_chiaki.setOpenExternalLinks(True)
        d_chiaki.setWordWrap(True)
        d_chiaki.setObjectName("fieldDescription")
        safety_layout.addWidget(d_chiaki)
        
        # Timeout margin
        self.spin_timeout_margin = QDoubleSpinBox()
        self.spin_timeout_margin.setRange(30.0, 900.0)
        self.spin_timeout_margin.setSingleStep(10.0)
        self.spin_timeout_margin.setValue(cfg.MATCH_TIMEOUT_MARGIN)
        self.spin_timeout_margin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_timeout_margin.setFixedWidth(80)

        row_tm = QWidget()
        h_tm = QHBoxLayout(row_tm)
        h_tm.setContentsMargins(0, 0, 0, 0)
        h_tm.setSpacing(6)
        h_tm.addWidget(QLabel("Timeout margin (s):"))
        h_tm.addWidget(self.spin_timeout_margin)
        h_tm.addStretch()
        safety_layout.addWidget(row_tm)
        d_tm = QLabel("Extra time beyond expected match duration before forcing recovery.")
        d_tm.setObjectName("fieldDescription")
        safety_layout.addWidget(d_tm)

        # Max matches / runtime
        self.spin_max_matches = QSpinBox()
        self.spin_max_matches.setRange(0, 999)
        self.spin_max_matches.setValue(cfg.MAX_MATCHES_PER_RUN or 0)
        self.spin_max_matches.setButtonSymbols(QSpinBox.NoButtons)
        self.spin_max_matches.setFixedWidth(80)

        row_mm = QWidget()
        h_mm = QHBoxLayout(row_mm)
        h_mm.setContentsMargins(0, 0, 0, 0)
        h_mm.setSpacing(6)
        h_mm.addWidget(QLabel("Stop after N matches (0 = no limit):"))
        h_mm.addWidget(self.spin_max_matches)
        h_mm.addStretch()
        safety_layout.addWidget(row_mm)

        self.spin_max_runtime = QDoubleSpinBox()
        self.spin_max_runtime.setRange(0.0, 2880.0)
        self.spin_max_runtime.setSingleStep(10.0)
        self.spin_max_runtime.setValue(cfg.MAX_RUNTIME_MINUTES or 0.0)
        self.spin_max_runtime.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_max_runtime.setFixedWidth(80)

        row_rt = QWidget()
        h_rt = QHBoxLayout(row_rt)
        h_rt.setContentsMargins(0, 0, 0, 0)
        h_rt.setSpacing(6)
        h_rt.addWidget(QLabel("Stop after X minutes (0 = no limit):"))
        h_rt.addWidget(self.spin_max_runtime)
        h_rt.addStretch()
        safety_layout.addWidget(row_rt)

        content_layout.addWidget(safety_card)

        # -------- RAMEN NPC TRAINER CARD --------
        ramen_card = QGroupBox()
        ramen_card.setObjectName("card")
        ramen_layout = QVBoxLayout(ramen_card)
        ramen_layout.setSpacing(10)

        title_ramen = QLabel("Ramen NPC Trainer")
        title_ramen.setObjectName("sectionTitle")
        ramen_layout.addWidget(title_ramen)

        ramen_desc = QLabel(
            "Configure the timing for the Ramen NPC auto-trainer loop.\n"
            "The trainer will use these values when you start it from the sidebar."
        )
        ramen_desc.setObjectName("fieldDescription")
        ramen_layout.addWidget(ramen_desc)

        ramen_form = QFormLayout()
        ramen_form.setLabelAlignment(Qt.AlignLeft)
        ramen_form.setFormAlignment(Qt.AlignTop)

        # Initial delay
        self.spin_ramen_initial = QDoubleSpinBox()
        self.spin_ramen_initial.setRange(0.0, 60.0)
        self.spin_ramen_initial.setSingleStep(0.5)
        self.spin_ramen_initial.setValue(getattr(cfg, "RAMEN_INITIAL_DELAY", 10.0))
        self.spin_ramen_initial.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_ramen_initial.setFixedWidth(80)
        ramen_form.addRow("Initial delay (s):", self.spin_ramen_initial)

        # First ENTER block
        self.spin_ramen_first_enter_count = QSpinBox()
        self.spin_ramen_first_enter_count.setRange(0, 20)
        self.spin_ramen_first_enter_count.setValue(getattr(cfg, "RAMEN_FIRST_ENTER_COUNT", 4))
        self.spin_ramen_first_enter_count.setButtonSymbols(QSpinBox.NoButtons)
        self.spin_ramen_first_enter_count.setFixedWidth(60)

        self.spin_ramen_first_enter_delay = QDoubleSpinBox()
        self.spin_ramen_first_enter_delay.setRange(0.0, 5.0)
        self.spin_ramen_first_enter_delay.setSingleStep(0.1)
        self.spin_ramen_first_enter_delay.setValue(getattr(cfg, "RAMEN_FIRST_ENTER_DELAY", 1.0))
        self.spin_ramen_first_enter_delay.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_ramen_first_enter_delay.setFixedWidth(70)

        row_first = QWidget()
        row_first_layout = QHBoxLayout(row_first)
        row_first_layout.setContentsMargins(0, 0, 0, 0)
        row_first_layout.setSpacing(6)
        row_first_layout.addWidget(self.spin_ramen_first_enter_count)
        row_first_layout.addWidget(QLabel("× ENTER, delay (s):"))
        row_first_layout.addWidget(self.spin_ramen_first_enter_delay)
        row_first_layout.addStretch()

        ramen_form.addRow("First dialog skip:", row_first)

        # Wait after first ENTER spam
        self.spin_ramen_after_first_wait = QDoubleSpinBox()
        self.spin_ramen_after_first_wait.setRange(0.0, 30.0)
        self.spin_ramen_after_first_wait.setSingleStep(0.5)
        self.spin_ramen_after_first_wait.setValue(getattr(cfg, "RAMEN_AFTER_FIRST_WAIT", 5.0))
        self.spin_ramen_after_first_wait.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_ramen_after_first_wait.setFixedWidth(80)
        ramen_form.addRow("Wait after first ENTER (s):", self.spin_ramen_after_first_wait)

        # W presses (min/max + delay)
        self.spin_ramen_w_min = QSpinBox()
        self.spin_ramen_w_min.setRange(0, 30)
        self.spin_ramen_w_min.setValue(getattr(cfg, "RAMEN_W_MIN", 7))
        self.spin_ramen_w_min.setButtonSymbols(QSpinBox.NoButtons)
        self.spin_ramen_w_min.setFixedWidth(50)

        self.spin_ramen_w_max = QSpinBox()
        self.spin_ramen_w_max.setRange(0, 30)
        self.spin_ramen_w_max.setValue(getattr(cfg, "RAMEN_W_MAX", 8))
        self.spin_ramen_w_max.setButtonSymbols(QSpinBox.NoButtons)
        self.spin_ramen_w_max.setFixedWidth(50)

        self.spin_ramen_w_delay = QDoubleSpinBox()
        self.spin_ramen_w_delay.setRange(0.0, 5.0)
        self.spin_ramen_w_delay.setSingleStep(0.1)
        self.spin_ramen_w_delay.setValue(getattr(cfg, "RAMEN_W_DELAY", 1.5))
        self.spin_ramen_w_delay.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_ramen_w_delay.setFixedWidth(70)

        row_w = QWidget()
        row_w_layout = QHBoxLayout(row_w)
        row_w_layout.setContentsMargins(0, 0, 0, 0)
        row_w_layout.setSpacing(6)
        row_w_layout.addWidget(QLabel("From"))
        row_w_layout.addWidget(self.spin_ramen_w_min)
        row_w_layout.addWidget(QLabel("to"))
        row_w_layout.addWidget(self.spin_ramen_w_max)
        row_w_layout.addWidget(QLabel("× W, delay (s):"))
        row_w_layout.addWidget(self.spin_ramen_w_delay)
        row_w_layout.addStretch()

        ramen_form.addRow("Walk (W presses):", row_w)

        # Long wait (ramen animation)
        self.spin_ramen_long_min = QDoubleSpinBox()
        self.spin_ramen_long_min.setRange(0.0, 180.0)
        self.spin_ramen_long_min.setSingleStep(0.5)
        self.spin_ramen_long_min.setValue(getattr(cfg, "RAMEN_LONG_WAIT_MIN", 15.0))
        self.spin_ramen_long_min.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_ramen_long_min.setFixedWidth(70)

        self.spin_ramen_long_max = QDoubleSpinBox()
        self.spin_ramen_long_max.setRange(0.0, 180.0)
        self.spin_ramen_long_max.setSingleStep(0.5)
        self.spin_ramen_long_max.setValue(getattr(cfg, "RAMEN_LONG_WAIT_MAX", 16.0))
        self.spin_ramen_long_max.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_ramen_long_max.setFixedWidth(70)

        row_long = QWidget()
        row_long_layout = QHBoxLayout(row_long)
        row_long_layout.setContentsMargins(0, 0, 0, 0)
        row_long_layout.setSpacing(6)
        row_long_layout.addWidget(QLabel("From"))
        row_long_layout.addWidget(self.spin_ramen_long_min)
        row_long_layout.addWidget(QLabel("to"))
        row_long_layout.addWidget(self.spin_ramen_long_max)
        row_long_layout.addWidget(QLabel("s"))
        row_long_layout.addStretch()

        ramen_form.addRow("Ramen animation wait:", row_long)

        # Final ENTER block
        self.spin_ramen_final_enter_count = QSpinBox()
        self.spin_ramen_final_enter_count.setRange(0, 20)
        self.spin_ramen_final_enter_count.setValue(getattr(cfg, "RAMEN_FINAL_ENTER_COUNT", 2))
        self.spin_ramen_final_enter_count.setButtonSymbols(QSpinBox.NoButtons)
        self.spin_ramen_final_enter_count.setFixedWidth(60)

        self.spin_ramen_final_enter_delay = QDoubleSpinBox()
        self.spin_ramen_final_enter_delay.setRange(0.0, 5.0)
        self.spin_ramen_final_enter_delay.setSingleStep(0.1)
        self.spin_ramen_final_enter_delay.setValue(getattr(cfg, "RAMEN_FINAL_ENTER_DELAY", 1.5))
        self.spin_ramen_final_enter_delay.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_ramen_final_enter_delay.setFixedWidth(70)

        row_final = QWidget()
        row_final_layout = QHBoxLayout(row_final)
        row_final_layout.setContentsMargins(0, 0, 0, 0)
        row_final_layout.setSpacing(6)
        row_final_layout.addWidget(self.spin_ramen_final_enter_count)
        row_final_layout.addWidget(QLabel("× ENTER, delay (s):"))
        row_final_layout.addWidget(self.spin_ramen_final_enter_delay)
        row_final_layout.addStretch()

        ramen_form.addRow("Final confirm:", row_final)

        # Wait after final ENTER
        self.spin_ramen_after_final_wait = QDoubleSpinBox()
        self.spin_ramen_after_final_wait.setRange(0.0, 60.0)
        self.spin_ramen_after_final_wait.setSingleStep(0.5)
        self.spin_ramen_after_final_wait.setValue(getattr(cfg, "RAMEN_AFTER_FINAL_WAIT", 5.0))
        self.spin_ramen_after_final_wait.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.spin_ramen_after_final_wait.setFixedWidth(80)
        ramen_form.addRow("Wait after final ENTER (s):", self.spin_ramen_after_final_wait)

        ramen_layout.addLayout(ramen_form)
        content_layout.addWidget(ramen_card)

        # -------- PINK BEANS TRAINER CARD --------
        pink_card = QGroupBox()
        pink_card.setObjectName("card")
        pink_layout = QVBoxLayout(pink_card)
        pink_layout.setSpacing(10)

        title_pink = QLabel("Pink Beans Trainer")
        title_pink.setObjectName("sectionTitle")
        pink_layout.addWidget(title_pink)

        pink_desc = QLabel(
            "Configure the timing for the Pink Beans trainer loop.\n"
            "The trainer will use these values when you start it from the sidebar."
        )
        pink_desc.setObjectName("fieldDescription")
        pink_layout.addWidget(pink_desc)

        pink_form = QFormLayout()
        pink_form.setLabelAlignment(Qt.AlignLeft)
        pink_form.setFormAlignment(Qt.AlignTop)

        def _mk_spin(name, cfg_attr, minimum, maximum, step):
            spin = QDoubleSpinBox()
            spin.setRange(minimum, maximum)
            spin.setSingleStep(step)
            spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
            spin.setFixedWidth(80)
            spin.setDecimals(2)
            spin.setValue(float(getattr(common.cfg, cfg_attr, getattr(common, cfg_attr, 0.0))))
            setattr(self, name, spin)
            return spin

        # Riga 1: delay iniziale
        self.spin_pink_initial = _mk_spin(
            "spin_pink_initial", "PINK_INITIAL_DELAY", 0.0, 30.0, 0.5
        )
        pink_form.addRow("Initial delay before loop (s):", self.spin_pink_initial)

        # Sequenza ENTER / UP / ENTER...
        self.spin_pink_enter1 = _mk_spin(
            "spin_pink_enter1", "PINK_ENTER1_DELAY", 0.0, 10.0, 0.1
        )
        pink_form.addRow("After 1st ENTER (s):", self.spin_pink_enter1)

        self.spin_pink_enter2 = _mk_spin(
            "spin_pink_enter2", "PINK_ENTER2_DELAY", 0.0, 10.0, 0.1
        )
        pink_form.addRow("After 2nd ENTER (s):", self.spin_pink_enter2)

        self.spin_pink_up = _mk_spin(
            "spin_pink_up", "PINK_UP_DELAY", 0.0, 5.0, 0.05
        )
        pink_form.addRow("After UP (s):", self.spin_pink_up)

        self.spin_pink_enter3 = _mk_spin(
            "spin_pink_enter3", "PINK_ENTER3_DELAY", 0.0, 5.0, 0.05
        )
        pink_form.addRow("After 3rd ENTER (s):", self.spin_pink_enter3)

        self.spin_pink_enter4 = _mk_spin(
            "spin_pink_enter4", "PINK_ENTER4_DELAY", 0.0, 20.0, 0.5
        )
        pink_form.addRow("After 4th ENTER / animation (s):", self.spin_pink_enter4)

        # Esc / v / hold v / after
        self.spin_pink_esc_after = _mk_spin(
            "spin_pink_esc_after", "PINK_ESC_AFTER_DELAY", 0.0, 5.0, 0.05
        )
        pink_form.addRow("After ESC (s):", self.spin_pink_esc_after)

        self.spin_pink_v_after = _mk_spin(
            "spin_pink_v_after", "PINK_V_AFTER_DELAY", 0.0, 10.0, 0.1
        )
        pink_form.addRow("After single V (s):", self.spin_pink_v_after)

        self.spin_pink_v_hold = _mk_spin(
            "spin_pink_v_hold", "PINK_V_HOLD_DURATION", 0.0, 10.0, 0.1
        )
        pink_form.addRow("Hold V duration (s):", self.spin_pink_v_hold)

        self.spin_pink_after_hold = _mk_spin(
            "spin_pink_after_hold", "PINK_AFTER_HOLD_DELAY", 0.0, 10.0, 0.1
        )
        pink_form.addRow("After HOLD V (s):", self.spin_pink_after_hold)

        # Down / final enter
        self.spin_pink_down = _mk_spin(
            "spin_pink_down", "PINK_DOWN_DELAY", 0.0, 5.0, 0.05
        )
        pink_form.addRow("After DOWN (s):", self.spin_pink_down)

        self.spin_pink_final_enter = _mk_spin(
            "spin_pink_final_enter", "PINK_FINAL_ENTER_DELAY", 0.0, 10.0, 0.1
        )
        pink_form.addRow("After final ENTER (s):", self.spin_pink_final_enter)

        pink_layout.addLayout(pink_form)
        content_layout.addWidget(pink_card)

        # -------- BLUE BEANS TRAINER CARD --------
        blue_card = QGroupBox()
        blue_card.setObjectName("card")
        blue_layout = QVBoxLayout(blue_card)
        blue_layout.setSpacing(10)

        title_blue = QLabel("Blue Beans Trainer")
        title_blue.setObjectName("sectionTitle")
        blue_layout.addWidget(title_blue)

        blue_desc = QLabel(
            "Configure the timing for the Blue Beans trainer loop.\n"
            "The trainer will use these values when you start it from the sidebar."
        )
        blue_desc.setObjectName("fieldDescription")
        blue_layout.addWidget(blue_desc)

        blue_form = QFormLayout()
        blue_form.setLabelAlignment(Qt.AlignLeft)
        blue_form.setFormAlignment(Qt.AlignTop)

        self.spin_blue_initial = _mk_spin(
            "spin_blue_initial", "BLUE_INITIAL_DELAY", 0.0, 30.0, 0.5
        )
        blue_form.addRow("Initial delay before loop (s):", self.spin_blue_initial)

        self.spin_blue_enter1 = _mk_spin(
            "spin_blue_enter1", "BLUE_ENTER1_DELAY", 0.0, 10.0, 0.1
        )
        blue_form.addRow("After 1st ENTER (s):", self.spin_blue_enter1)

        self.spin_blue_enter2 = _mk_spin(
            "spin_blue_enter2", "BLUE_ENTER2_DELAY", 0.0, 10.0, 0.1
        )
        blue_form.addRow("After 2nd ENTER (s):", self.spin_blue_enter2)

        self.spin_blue_up = _mk_spin(
            "spin_blue_up", "BLUE_UP_DELAY", 0.0, 5.0, 0.05
        )
        blue_form.addRow("After UP (s):", self.spin_blue_up)

        self.spin_blue_enter3 = _mk_spin(
            "spin_blue_enter3", "BLUE_ENTER3_DELAY", 0.0, 5.0, 0.05
        )
        blue_form.addRow("After 3rd ENTER (s):", self.spin_blue_enter3)

        self.spin_blue_enter4 = _mk_spin(
            "spin_blue_enter4", "BLUE_ENTER4_DELAY", 0.0, 30.0, 0.5
        )
        blue_form.addRow("After 4th ENTER / animation (s):", self.spin_blue_enter4)

        self.spin_blue_a1 = _mk_spin(
            "spin_blue_a1", "BLUE_A1_DELAY", 0.0, 20.0, 0.1
        )
        blue_form.addRow("After first A (s):", self.spin_blue_a1)

        self.spin_blue_s1 = _mk_spin(
            "spin_blue_s1", "BLUE_S1_DELAY", 0.0, 20.0, 0.1
        )
        blue_form.addRow("After first S (s):", self.spin_blue_s1)

        self.spin_blue_a2 = _mk_spin(
            "spin_blue_a2", "BLUE_A2_DELAY", 0.0, 20.0, 0.1
        )
        blue_form.addRow("After second A (s):", self.spin_blue_a2)

        self.spin_blue_s2 = _mk_spin(
            "spin_blue_s2", "BLUE_S2_DELAY", 0.0, 30.0, 0.1
        )
        blue_form.addRow("After second S (s):", self.spin_blue_s2)

        self.spin_blue_a3 = _mk_spin(
            "spin_blue_a3", "BLUE_A3_DELAY", 0.0, 20.0, 0.1
        )
        blue_form.addRow("After third A (s):", self.spin_blue_a3)

        self.spin_blue_s3 = _mk_spin(
            "spin_blue_s3", "BLUE_S3_DELAY", 0.0, 20.0, 0.1
        )
        blue_form.addRow("After third S (s):", self.spin_blue_s3)

        self.spin_blue_a4 = _mk_spin(
            "spin_blue_a4", "BLUE_A4_DELAY", 0.0, 30.0, 0.1
        )
        blue_form.addRow("After fourth A (s):", self.spin_blue_a4)

        self.spin_blue_enter5 = _mk_spin(
            "spin_blue_enter5", "BLUE_ENTER5_DELAY", 0.0, 10.0, 0.1
        )
        blue_form.addRow("After final ENTER (s):", self.spin_blue_enter5)

        self.spin_blue_cooldown = _mk_spin(
            "spin_blue_cooldown", "BLUE_COOLDOWN_DELAY", 0.0, 300.0, 1.0
        )
        blue_form.addRow("Cooldown before next cycle (s):", self.spin_blue_cooldown)

        blue_layout.addLayout(blue_form)
        content_layout.addWidget(blue_card)

        # -------- APPLY BUTTON --------
        self.btn_save_settings = QPushButton("Apply Settings")
        self.btn_save_settings.setObjectName("primaryButton")
        self.btn_save_settings.setMinimumHeight(32)
        content_layout.addWidget(self.btn_save_settings)

        content_layout.addStretch()

        scroll.setWidget(content)
        tab_layout.addWidget(scroll)

        return tab

    # ---------------- SIGNALS ----------------

    def _connect_signals(self):
        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_quit.clicked.connect(self.close)

        self.btn_save_settings.clicked.connect(self.on_save_settings)

        self.btn_recalib.clicked.connect(self.on_recalibrate)
        self.btn_test_focus.clicked.connect(self.on_test_focus)
        self.btn_test_click.clicked.connect(self.on_test_play_click)
        self.btn_test_pixel.clicked.connect(self.on_test_pixel)
        self.btn_update.clicked.connect(self._open_releases_page)
        self.btn_copy_logs.clicked.connect(self.on_copy_logs)
        self.btn_save_logs.clicked.connect(self.on_save_logs)
        self.combo_theme.currentTextChanged.connect(self.on_change_theme)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)

    def _open_releases_page(self):
        QDesktopServices.openUrl(QUrl(common.APP_RELEASE_URL))

    # ---------------- BOT CONTROL ----------------

    def _open_footer_link(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    def _on_footer_hover(self, link: str):
        # link is non-empty when hovering; empty string when leaving
        if link:
            self.footer_label.setText(self._footer_hover)
        else:
            self.footer_label.setText(self._footer_normal)

    def _on_mode_changed(self, index: int):
        data = self.combo_mode.itemData(index)

        wip_modes = {
            "beans_red",
            "beans_green",
            "beans_orange",
            "beans_yellow",
            "beans_light_blue",
        }

        if data in wip_modes:
            QMessageBox.information(
                self,
                "Trainer in development",
                "This trainer is still being developed, will come in a future update."
            )

            # revert to last valid mode
            self.combo_mode.blockSignals(True)
            self.combo_mode.setCurrentIndex(self._last_valid_mode_index)
            self.combo_mode.blockSignals(False)
            return

        # valid selection → update tracker
        self._last_valid_mode_index = index

    def on_start(self):
        if (self.bot_thread and self.bot_thread.is_alive()) or \
           (self.ramen_thread and self.ramen_thread.is_alive()):
            common.log("INFO", "A mode is already running.")
            return

        mode = "ranked"
        if hasattr(self, "combo_mode") and self.combo_mode is not None:
            data = self.combo_mode.currentData()
            mode = data or "ranked"

        self.stop_event.clear()

        if mode == "ranked":
            self._start_ranked()
            self.set_status("Status: running", "#22c55e")
        elif mode == "ramen":
            self._start_ramen()
            self.set_status("Status: ramen trainer running", "#22c55e")
        elif mode == "beans_blue":
            self._start_blue_beans()
            self.set_status("Status: blue beans trainer running", "#22c55e")
        elif mode == "beans_pink":
            self._start_pink_beans()
            self.set_status("Status: pink beans trainer running", "#22c55e")
        else:
            common.log("WARN", f"Mode '{mode}' is not implemented yet.")
            self.set_status("Status: mode not implemented", "#facc15")
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def _start_ranked(self):
        """Start the Ranked auto-match bot."""
        self.bot_thread = threading.Thread(
            target=bot_main, args=(self.stop_event,), daemon=True
        )
        self.bot_thread.start()
        common.log("INFO", "Ranked bot thread started from Qt GUI.")

    def _start_ramen(self):
        """Start the Ramen NPC trainer."""
        self.ramen_thread = threading.Thread(
            target=run_ramen_trainer,
            args=(self.stop_event,),
            daemon=True,
        )
        self.ramen_thread.start()
        common.log("INFO", "Ramen trainer thread started from Qt GUI.")

    def _start_blue_beans(self):
        """Start the Blue Beans trainer."""
        self.ramen_thread = threading.Thread(
            target=run_blue_beans_trainer,
            args=(self.stop_event,),
            daemon=True,
        )
        self.ramen_thread.start()
        common.log("INFO", "Blue Beans trainer thread started from Qt GUI.")

    def _start_pink_beans(self):
        """Start the Pink Beans trainer."""
        self.ramen_thread = threading.Thread(
            target=run_pink_beans_trainer,
            args=(self.stop_event,),
            daemon=True,
        )
        self.ramen_thread.start()
        common.log("INFO", "Pink Beans trainer thread started from Qt GUI.")

    def on_stop(self):
        ranked_running = self.bot_thread and self.bot_thread.is_alive()
        ramen_running = self.ramen_thread and self.ramen_thread.is_alive()

        if not (ranked_running or ramen_running):
            common.log("INFO", "No mode is currently running.")
            return

        self.stop_event.set()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if ramen_running:
            self.set_status("Status: stopping ramen...", "#facc15")
        elif ranked_running:
            self.set_status("Status: stopping...", "#facc15")
        else:
            self.set_status("Status: stopping...", "#facc15")

        common.log("INFO", "Stop requested from Qt GUI.")

    # ---------------- STATUS & LOGS ----------------

    def set_status(self, text: str, color: str):
        """
        text is currently passed like 'Status: idle' from callers.
        We show only the short part ('idle') in the header pill.
        """
        short = text.split(":", 1)[-1].strip() if ":" in text else text
        self.lbl_status_header.setText(short.capitalize())
        self.status_dot.setStyleSheet(
            f"background-color: {color}; border-radius: 6px;"
        )

    def poll_queues(self):
        # log queue
        while True:
            try:
                level, msg = common.log_queue.get_nowait()
            except Exception:
                break
            else:
                self.append_log(level, msg)

        # stats queue
        while True:
            try:
                data = common.stats_queue.get_nowait()
            except Exception:
                break
            else:
                self.update_stats(data)

    def append_log(self, level: str, msg: str):
        self.log_lines.append(msg)  # <--- salva anche in memoria

        level = (level or "").upper()
        color_map = {
            "INFO": "#38bdf8",
            "STATE": "#22c55e",
            "ACTION": "#a855f7",
            "DEBUG": "#9ca3af",
            "WARN": "#facc15",
            "ERROR": "#f97373",
        }
        color = color_map.get(level, "#e5e7eb")
        safe = (
            msg.rstrip("\n")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        html = f'<span style="color:{color};">{safe}</span>'
        self.txt_logs.append(html)

        cursor = self.txt_logs.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.txt_logs.setTextCursor(cursor)

    def on_copy_logs(self):
        text = "\n".join(self.log_lines)
        QApplication.clipboard().setText(text)
        common.log("INFO", "Logs copied to clipboard.")

    def on_save_logs(self):
        if not self.log_lines:
            common.log("WARN", "There are no logs to save.")
            return

        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save logs",
            "ievr_logs.txt",
            "Text files (*.txt);;All files (*)"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.log_lines))
            common.log("INFO", f"Logs saved to: {path}")
        except Exception as e:
            common.log("ERROR", f"Failed to save logs: {e}")

    def on_change_theme(self, value: str):
        app = QApplication.instance()
        apply_theme(app, value)
        common.log("INFO", f"Theme switched to {value}.")
        
    # ---------------- STATS ----------------

    @staticmethod
    def _format_mmss(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def update_stats(self, data):
        """
        data può essere:
        - float: solo durata (compatibile con bot.py attuale)
        - dict: {"duration": float, "timestamp": float}
        """
        if isinstance(data, dict):
            duration = float(data.get("duration", 0.0))
            ts = float(data.get("timestamp", time.time()))
        else:
            duration = float(data)
            ts = time.time()

        # counters
        self.matches_played += 1
        self.last_match_time = duration
        self.total_match_time += duration
        avg = self.total_match_time / self.matches_played if self.matches_played else 0.0

        # status bar in basso
        self.lbl_stats.setText(
            f"Matches: {self.matches_played}  •  "
            f"Avg: {self._format_mmss(avg)}  •  "
            f"Last: {self._format_mmss(duration)}"
        )

        # aggiungi alla history e aggiorna tab
        entry = {
            "index": self.matches_played,
            "timestamp": ts,
            "duration": duration,
            "avg": avg,
        }
        self.match_history.append(entry)
        self._refresh_stats_tab()

    def _refresh_stats_tab(self):
        # no matches → basic message + empty table
        if not self.match_history:
            self.lbl_stats_summary.setText("No matches recorded yet.")
            self.tbl_matches.setRowCount(0)
            return

        total_matches = self.matches_played
        total_seconds = self.total_match_time
        avg = total_seconds / total_matches if total_matches else 0.0
        hours = total_seconds / 3600.0
        matches_per_hour = (total_matches / hours) if hours > 0 else 0.0

        # summary line above the table
        self.lbl_stats_summary.setText(
            f"Matches this session: {total_matches}  •  "
            f"Total time: {self._format_mmss(total_seconds)}  •  "
            f"Avg match: {self._format_mmss(avg)}  •  "
            f"~{matches_per_hour:.1f} matches/hour"
        )

        # rebuild table
        self.tbl_matches.setRowCount(len(self.match_history))

        for row, entry in enumerate(self.match_history):
            # nice formatted time
            ts_str = datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S")

            idx_item = QTableWidgetItem(str(entry["index"]))
            ts_item = QTableWidgetItem(ts_str)
            dur_item = QTableWidgetItem(f"{entry['duration']:.1f}")
            avg_item = QTableWidgetItem(f"{entry['avg']:.1f}")

            # alignment: # centered, numbers centered, time centered
            idx_item.setTextAlignment(Qt.AlignCenter)
            ts_item.setTextAlignment(Qt.AlignCenter)
            dur_item.setTextAlignment(Qt.AlignCenter)
            avg_item.setTextAlignment(Qt.AlignCenter)

            # non-editable + consistent color
            for item in (idx_item, ts_item, dur_item, avg_item):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setForeground(QColor("#e5e7eb"))

            self.tbl_matches.setItem(row, 0, idx_item)
            self.tbl_matches.setItem(row, 1, ts_item)
            self.tbl_matches.setItem(row, 2, dur_item)
            self.tbl_matches.setItem(row, 3, avg_item)


    # ---------------- SETTINGS SAVE ----------------

    def on_save_settings(self):
        try:
            # =============== CORE / RANKED SETTINGS FROM UI ===============
            common.GAME_WINDOW_TITLE = self.edit_window_title.text().strip()
            new_key = self.edit_auto_key.text().strip()
            common.AUTO_MODE_KEY = new_key or "u"

            common.DELAY_BEFORE_START = float(self.spin_delay_start.value())
            common.FIRST_WAIT = float(self.spin_first_wait.value())
            common.SECOND_WAIT = float(self.spin_second_wait.value())
            common.MATCH_DURATION = float(self.spin_match_duration.value())
            common.POST_MATCH_CLICKS = int(self.spin_post_clicks.value())
            common.POST_MATCH_CLICK_INTERVAL = float(self.spin_post_interval.value())
            common.SEARCH_CHECK_INTERVAL = float(self.spin_search_interval.value())
            common.LVL_75_PLUS = self.chk_lvl75.isChecked()
            common.MATCH_TIMEOUT_MARGIN = float(self.spin_timeout_margin.value())
            common.CHIAKI4DECK = self.chk_chiaki.isChecked()

            max_matches = int(self.spin_max_matches.value())
            common.MAX_MATCHES_PER_RUN = None if max_matches == 0 else max_matches

            max_runtime = float(self.spin_max_runtime.value())
            common.MAX_RUNTIME_MINUTES = None if max_runtime == 0.0 else max_runtime

            # ================= PS REMOTE PLAY INSTALL FLOW =================
            if common.CHIAKI4DECK:
                # re-init backend to test environment
                common.input_backend = common.InputBackend(True)
                status = common.check_chiaki4deck_env()

                # ---------------- ALREADY OK ----------------
                if status == "ok":
                    pass  # nothing special to do

                # ---------------- NO VGAMEPAD: install Python package ----------------
                elif status == "no_vgamepad":
                    reply = QMessageBox.question(
                        self,
                        "Chiaki4Deck setup required",
                        (
                            "Chiaki4Deck mode needs the Python package 'vgamepad'.\n\n"
                            "It is not installed in your Python environment.\n\n"
                            "Do you want me to try installing it automatically?"
                        ),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )

                    if reply == QMessageBox.No:
                        self.chk_chiaki.setChecked(False)
                        common.CHIAKI4DECK = False
                        return

                    QMessageBox.information(
                        self,
                        "Installing vgamepad…",
                        "I will now run 'pip install vgamepad'.\n"
                        "Please wait until the installation finishes.",
                    )

                    ok, output = common.install_vgamepad_blocking()
                    common.log("INFO", f"vgamepad install output:\n{output}")

                    # Re-test after package install
                    common.input_backend = common.InputBackend(True)
                    status = common.check_chiaki4deck_env()
                    common.log("DEBUG", f"Chiaki env AFTER vgamepad install: {status!r}, ok={ok}")

                    # 1) pip clearly failed → still no_vgamepad
                    if status == "no_vgamepad":
                        QMessageBox.critical(
                            self,
                            "vgamepad not available",
                            "The 'vgamepad' package could not be imported even after running "
                            "'pip install vgamepad'.\n\n"
                            "Check the logs for details (Python environment, permissions, etc.).\n"
                            "Chiaki4Deck mode will NOT be enabled."
                        )
                        self.chk_chiaki.setChecked(False)
                        common.CHIAKI4DECK = False
                        return

                    # 2) vgamepad OK but driver missing → let the driver branch handle it
                    if status == "no_driver":
                        pass  # will fall through to the 'if status == \"no_driver\"' block below

                    # 3) any other weird status
                    elif status != "ok":
                        QMessageBox.critical(
                            self,
                            "Chiaki4Deck not available",
                            "Something went wrong while setting up the virtual controller.\n\n"
                            "Chiaki4Deck mode will NOT be enabled."
                        )
                        self.chk_chiaki.setChecked(False)
                        common.CHIAKI4DECK = False
                        return

                # ---------------- NO DRIVER: run ViGEmBus installer ----------------
                if status == "no_driver":
                    reply = QMessageBox.question(
                        self,
                        "ViGEmBus driver required",
                        (
                            "The 'vgamepad' package is present, but the ViGEmBus driver "
                            "is not installed or not running.\n\n"
                            "I can run the bundled ViGEmBus installer for you now.\n"
                            "Windows will likely show a UAC prompt – please accept it.\n\n"
                            "Do you want to continue?"
                        ),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )

                    if reply == QMessageBox.No:
                        self.chk_chiaki.setChecked(False)
                        common.CHIAKI4DECK = False
                        return

                    ok, msg = common.install_vigem_driver()
                    if not ok:
                        QMessageBox.critical(self, "Driver install failed", msg)
                        self.chk_chiaki.setChecked(False)
                        common.CHIAKI4DECK = False
                        return

                    QMessageBox.information(
                        self,
                        "Driver installer launched",
                        "The ViGEmBus driver installer has been started.\n\n"
                        "Complete the wizard, then reboot your PC if requested.\n"
                        "After reboot, reopen IEVR Helper and enable Chiaki4Deck again."
                    )
                    # Disable for this session
                    self.chk_chiaki.setChecked(False)
                    common.CHIAKI4DECK = False
                    return

                # ---------------- UNSUPPORTED / OTHER ERROR ----------------
                if status not in ("ok", "no_vgamepad", "no_driver"):
                    QMessageBox.critical(
                        self,
                        "Chiaki4Deck not available",
                        "This platform does not support the virtual controller "
                        "(vgamepad / ViGEmBus). Chiaki4Deck mode will not be enabled."
                    )
                    self.chk_chiaki.setChecked(False)
                    common.CHIAKI4DECK = False
                    return

            # ================= RAMEN TRAINER =================
            common.RAMEN_INITIAL_DELAY = float(self.spin_ramen_initial.value())
            common.RAMEN_FIRST_ENTER_COUNT = int(self.spin_ramen_first_enter_count.value())
            common.RAMEN_FIRST_ENTER_DELAY = float(self.spin_ramen_first_enter_delay.value())
            common.RAMEN_AFTER_FIRST_WAIT = float(self.spin_ramen_after_first_wait.value())
            common.RAMEN_W_MIN = int(self.spin_ramen_w_min.value())
            common.RAMEN_W_MAX = int(self.spin_ramen_w_max.value())
            common.RAMEN_W_DELAY = float(self.spin_ramen_w_delay.value())
            common.RAMEN_LONG_WAIT_MIN = float(self.spin_ramen_long_min.value())
            common.RAMEN_LONG_WAIT_MAX = float(self.spin_ramen_long_max.value())
            common.RAMEN_FINAL_ENTER_COUNT = int(self.spin_ramen_final_enter_count.value())
            common.RAMEN_FINAL_ENTER_DELAY = float(self.spin_ramen_final_enter_delay.value())
            common.RAMEN_AFTER_FINAL_WAIT = float(self.spin_ramen_after_final_wait.value())

            # ================= PINK BEANS TRAINER =================
            common.PINK_INITIAL_DELAY = float(self.spin_pink_initial.value())
            common.PINK_ENTER1_DELAY = float(self.spin_pink_enter1.value())
            common.PINK_ENTER2_DELAY = float(self.spin_pink_enter2.value())
            common.PINK_UP_DELAY = float(self.spin_pink_up.value())
            common.PINK_ENTER3_DELAY = float(self.spin_pink_enter3.value())
            common.PINK_ENTER4_DELAY = float(self.spin_pink_enter4.value())

            common.PINK_ESC_AFTER_DELAY = float(self.spin_pink_esc_after.value())
            common.PINK_V_AFTER_DELAY = float(self.spin_pink_v_after.value())
            common.PINK_V_HOLD_DURATION = float(self.spin_pink_v_hold.value())
            common.PINK_AFTER_HOLD_DELAY = float(self.spin_pink_after_hold.value())

            common.PINK_DOWN_DELAY = float(self.spin_pink_down.value())
            common.PINK_FINAL_ENTER_DELAY = float(self.spin_pink_final_enter.value())

            # ================= BLUE BEANS TRAINER =================
            common.BLUE_INITIAL_DELAY  = float(self.spin_blue_initial.value())
            common.BLUE_ENTER1_DELAY   = float(self.spin_blue_enter1.value())
            common.BLUE_ENTER2_DELAY   = float(self.spin_blue_enter2.value())
            common.BLUE_UP_DELAY       = float(self.spin_blue_up.value())
            common.BLUE_ENTER3_DELAY   = float(self.spin_blue_enter3.value())
            common.BLUE_ENTER4_DELAY   = float(self.spin_blue_enter4.value())

            common.BLUE_A1_DELAY       = float(self.spin_blue_a1.value())
            common.BLUE_S1_DELAY       = float(self.spin_blue_s1.value())
            common.BLUE_A2_DELAY       = float(self.spin_blue_a2.value())
            common.BLUE_S2_DELAY       = float(self.spin_blue_s2.value())
            common.BLUE_A3_DELAY       = float(self.spin_blue_a3.value())
            common.BLUE_S3_DELAY       = float(self.spin_blue_s3.value())
            common.BLUE_A4_DELAY       = float(self.spin_blue_a4.value())

            common.BLUE_ENTER5_DELAY   = float(self.spin_blue_enter5.value())
            common.BLUE_COOLDOWN_DELAY = float(self.spin_blue_cooldown.value())

            # ================= MIRROR INTO cfg (dynamic) =================
            cfg = common.cfg

            # copy every ALL-CAPS attribute that also exists in cfg
            for name in dir(common):
                if not name.isupper():
                    continue
                if not hasattr(cfg, name):
                    continue
                setattr(cfg, name, getattr(common, name))

            # ================= SAVE TO settings.py (dynamic) =================
            # take all ALL-CAPS attributes from cfg as settings
            values = {
                name: getattr(cfg, name)
                for name in dir(cfg)
                if name.isupper()
            }
            common.save_settings_to_file(values)

            # update header label using current values
            self._cfg_label.setText(
                f'Window title: "{common.GAME_WINDOW_TITLE}"   •   '
                f'Auto-mode key: "{common.AUTO_MODE_KEY.upper()}"'
            )
            self.set_status("Status: idle (settings updated)", "#22c55e")
            common.log("INFO", "Settings saved to settings.py and applied.")

        except Exception as e:
            common.log("ERROR", f"Failed to save settings: {e}")
            self.set_status("Status: error while saving", "#f97373")

    # ---------------- TOOL CALLBACKS ----------------

    def on_recalibrate(self):
        if self.bot_thread and self.bot_thread.is_alive():
            common.log("WARN", "Stop the bot before recalibrating offsets.")
            return

        def _run():
            self.set_status("Status: recalibrating...", "#f97316")
            try:
                recalibrate_offsets_via_gui()
            finally:
                self.set_status("Status: idle", "#6b7280")

        threading.Thread(target=_run, daemon=True).start()

    def on_test_focus(self):
        common.log("INFO", "Testing focus on game window...")
        gui_test_focus()

    def on_test_play_click(self):
        common.log("INFO", "Testing 'Ranked Match' button click...")
        gui_test_play_click()

    def on_test_pixel(self):
        common.log("INFO", "Testing search pixel read...")
        gui_test_search_pixel()


# =========================
#   APP ENTRY
# =========================

def _apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    # ---- Base palette (for native widgets, scrollbars etc.) ----
    palette = QPalette()
    bg = QColor(5, 7, 22)          # near-black
    bg_alt = QColor(9, 12, 34)     # slightly lighter
    text = QColor(229, 231, 235)   # light text
    mid = QColor(30, 41, 59)       # border
    accent = QColor(59, 130, 246)  # blue

    palette.setColor(QPalette.Window, bg)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, QColor(10, 12, 30))
    palette.setColor(QPalette.AlternateBase, bg_alt)
    palette.setColor(QPalette.ToolTipBase, text)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, bg_alt)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.BrightText, QColor(248, 113, 113))
    palette.setColor(QPalette.Highlight, accent)
    palette.setColor(QPalette.HighlightedText, QColor(15, 23, 42))

    app.setPalette(palette)
    arrow_path = resource_path("assets/icons/arrow_down_light.png")

    # ---- Launcher-style stylesheet ----
    app.setStyleSheet(
        """
        /* ROOT WINDOW ------------------------------------------------------ */
        QMainWindow {
            background-color: #020617;
        }

        QWidget#sidebar {
            background-color: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #020617,
                stop:0.5 #020617,
                stop:1 #020617
            );
            border-right: 1px solid #111827;
        }

        /* HEADER CARD ------------------------------------------------------ */
        QWidget#headerCard {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #020617,
                stop:0.35 #020617,
                stop:1 #0b1120
            );
            border: 1px solid #1f2937;
            border-radius: 14px;
        }

        QLabel {
            color: #e5e7eb;
        }

        /* TABS / CONTENT --------------------------------------------------- */
        QTabWidget::pane {
            border: 1px solid #111827;
            border-radius: 10px;
            background-color: #020617;
            margin-top: 6px;
        }

        QTabBar::tab {
            padding: 7px 18px;
            border: 0px;
            color: #9ca3af;
            font-weight: 500;
        }

        QTabBar::tab:selected {
            color: #e5e7eb;
            border-bottom: 2px solid #3b82f6;
        }

        QTabBar::tab:hover:!selected {
            color: #e5e7eb;
        }

        /* CARDS ------------------------------------------------------------ */
        QFrame#card,
        QGroupBox {
            background-color: rgba(15, 23, 42, 0.96);
            border: 1px solid #1f2937;
            border-radius: 12px;
        }
        
        QWidget#statsTab {
            background-color: transparent;
        }
        
        /* GLASSY STATS TAB ------------------------------------------------- */
        QWidget#statsTab QFrame#card {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(30, 64, 175, 0.25),
                stop:1 rgba(15, 23, 42, 0.10)
            );
            border: 1px solid rgba(148, 163, 184, 0.45);
            border-radius: 18px;
        }

        QWidget#statsTab QLabel#fieldDescription {
            color: #cbd5f5;
        }

        QWidget#statsTab QTableWidget {
            background-color: transparent;
            gridline-color: rgba(148, 163, 184, 0.35);
            border: none;
            selection-background-color: rgba(59, 130, 246, 0.35);
            selection-color: #e5e7eb;
        }

        QWidget#statsTab QHeaderView::section {
            background-color: rgba(15, 23, 42, 0.65);
            border: 0px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.4);
            padding: 4px 6px;
            color: #e5e7eb;
            font-weight: 500;
        }

        QGroupBox {
            margin-top: 22px;
            padding: 10px 12px 12px 12px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0px 4px;
            color: #e5e7eb;
            font-weight: 600;
        }

        /* TABLE CONTAINER + TABLE ------------------------------------ */
        QFrame#tableContainer {
            background-color: rgba(15, 23, 42, 0.96);
            border-radius: 12px;
            border: 1px solid #1e293b;
        }

        QTableWidget {
            background-color: transparent;
            gridline-color: #1e293b;
            border: none;
        }

        /* Header sections */
        QHeaderView::section {
            background-color: rgba(15, 23, 42, 0.98);
            color: #e5e7eb;
            padding: 6px 12px;
            border: none;
            border-right: 1px solid #111827;
            font-weight: 600;
        }
        QHeaderView::section:last {
            border-right: none;
        }
        
        /* TABLE WIDGET ------------------------------------------------------- */
        QTableWidget {
            background-color: transparent;
            border: none;
            gridline-color: #111827;
            selection-background-color: rgba(37, 99, 235, 0.30);
            selection-color: #e5e7eb;
            font-size: 11px;
        }

        /* Header: text only + bottom divider (NO rectangle) */
        QHeaderView::section {
            background-color: transparent;
            color: #e5e7eb;
            padding: 6px 12px;
            border: none;
            border-bottom: 1px solid #1f2937;
            font-weight: 600;
        }

        /* Corner cell in the top-left */
        QTableCornerButton::section {
            background-color: transparent;
            border: none;
            border-bottom: 1px solid #1f2937;
        }
        
        /* Table items */
        QTableWidget::item {
            padding: 6px 10px;
        }

        /* Hover / selected row */
        QTableWidget::item:selected {
            background-color: rgba(37, 99, 235, 0.25);
            color: #e5e7eb;
        }

        /* LOG TEXT --------------------------------------------------------- */
        QTextEdit#logText {
            background-color: transparent;
            border: none;
            font-family: Consolas, "Cascadia Code", monospace;
            font-size: 11px;
            color: #e5e7eb;
        }

        /* FORM CONTROLS ---------------------------------------------------- */
        QLineEdit,
        QDoubleSpinBox,
        QSpinBox {
            background-color: #020617;
            border: 1px solid #374151;
            border-radius: 6px;
            padding: 4px 7px;
            selection-background-color: #2563eb;
        }

        QLineEdit:focus,
        QDoubleSpinBox:focus,
        QSpinBox:focus {
            border: 1px solid #3b82f6;
        }

        QCheckBox {
            color: #d1d5db;
        }

        /* BUTTONS ---------------------------------------------------------- */
        QPushButton {
            border-radius: 8px;
            padding: 7px 12px;
            border: 1px solid transparent;
            color: #e5e7eb;
            background-color: #111827;
        }

        QPushButton#primaryButton {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #2563eb,
                stop:1 #1d4ed8
            );
            border: 1px solid #1d4ed8;
            font-weight: 600;
        }
        QPushButton#primaryButton:hover {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #3b82f6,
                stop:1 #2563eb
            );
        }
        QPushButton#primaryButton:pressed {
            background-color: #1e40af;
        }

        QPushButton#secondaryButton {
            background-color: #020617;
            border: 1px solid #1f2937;
            color: #e5e7eb;
        }
        QPushButton#secondaryButton:hover {
            background-color: #111827;
        }

        QPushButton#dangerButton {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #ef4444,
                stop:1 #b91c1c
            );
            border: 1px solid #b91c1c;
            font-weight: 600;
        }
        QPushButton#dangerButton:hover {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #f87171,
                stop:1 #ef4444
            );
        }

        QPushButton#ghostButton {
            background-color: #020617;
            border: 1px solid #1f2937;
            color: #d1d5db;
            font-weight: 500;
        }
        QPushButton#ghostButton:hover {
            border-color: #3b82f6;
        }

        QPushButton:disabled {
            background-color: #020617;
            color: #6b7280;
            border-color: #111827;
        }

        /* STATUS BAR ------------------------------------------------------- */
        QStatusBar {
            background-color: #020617;
            border-top: 1px solid #111827;
        }
        QStatusBar QLabel {
            color: #9ca3af;
            font-size: 10px;
        }

        /* -------- SETTINGS MODERN -------- */
        QLabel#sectionTitle {
            font-size: 17px;
            font-weight: 600;
            margin-bottom: 6px;
            color: #e5e7eb;
        }

        QLabel#fieldDescription {
            font-size: 11px;
            color: #9ca3af;
            margin-bottom: 10px;
        }

        /* Better sliders */
        QSlider::groove:horizontal {
            border: 1px solid #1f2937;
            height: 6px;
            background: #0f172a;
            border-radius: 3px;
        }

        QSlider::handle:horizontal {
            background: #3b82f6;
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }

        QSlider::handle:horizontal:hover {
            background: #60a5fa;
        }

        QSlider::sub-page:horizontal {
            background: #2563eb;
            border-radius: 3px;
        }
        QLabel#appTitle {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        QLabel#sidebarSubtitle {
            font-size: 11px;
            color: #9ca3af;
            margin-top: -2px;
        }

        QLabel#sidebarStatus {
            font-size: 11px;
            color: #6b7280;
            margin-top: 6px;
        }

        QLabel#statusText {
            background-color: rgba(15, 23, 42, 0.98);
            border: 1px solid #1f2937;
            border-radius: 999px;
            padding: 3px 12px;
            font-size: 11px;
            font-weight: 500;
        }

        QLabel#headerTitle {
            font-size: 20px;
            font-weight: 700;
        }
        QFrame#infoCard {
            background-color: #020617;
            border: 1px solid #111827;
            border-radius: 10px;
        }
        QFrame#infoCard QLabel {
            font-size: 10px;
            color: #9ca3af;
        }

        QPushButton#updateButton {
            background-color: #facc15;
            color: #111827;
            font-weight: 600;
            border-radius: 6px;
            border: 1px solid #eab308;
            padding: 4px 8px;
        }
        QPushButton#updateButton:hover {
            background-color: #fde047;
        }
        /* MODE DROPDOWN --------------------------------------------------- */
        QComboBox#modeCombo {
            background-color: #020617;
            border: 1px solid #374151;
            border-radius: 6px;
            padding: 4px 32px 4px 10px;   /* room on right for arrow */
            color: #e5e7eb;
            min-height: 26px;
        }

        QComboBox#modeCombo:focus {
            border: 1px solid #3b82f6;
        }

        QComboBox#modeCombo::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 26px;
            border: none;
            background: transparent;
        }

        QComboBox#modeCombo::down-arrow {
            image: url("assets/icons/arrow_down_light.png");
            width: 12px;
            height: 12px;
        }

        /* POPUP LIST ------------------------------------------------------- */
        QComboBox#modeCombo QAbstractItemView {
            background-color: #020617;
            border: 1px solid #1f2937;
            padding: 4px 0;
            outline: 0;
        }

        /* items */
        QComboBox#modeCombo QAbstractItemView::item {
            min-height: 30px;
            padding: 6px 14px;
            padding-left: 32px; /* space for icon */
            color: #e5e7eb;
        }

        QComboBox#modeCombo QListView::item {
            icon-size: 18px;
        }

        /* this will now act as HOVER because we select on mouse move */
        QComboBox#modeCombo QAbstractItemView::item:selected {
            background-color: rgba(37, 99, 235, 0.85);
            color: #ffffff;
        }
        """
    )

def apply_theme(app: QApplication, mode: str):
    if mode == "light":
        app.setStyleSheet("")  # usa default theme
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor("#fafafa"))
        pal.setColor(QPalette.WindowText, QColor("#111111"))
        pal.setColor(QPalette.Base, QColor("#ffffff"))
        pal.setColor(QPalette.AlternateBase, QColor("#f0f0f0"))
        pal.setColor(QPalette.Text, QColor("#000000"))
        pal.setColor(QPalette.Button, QColor("#e8e8e8"))
        pal.setColor(QPalette.ButtonText, QColor("#000000"))
        app.setPalette(pal)
    else:
        _apply_dark_theme(app)

def run_app():
    app = QApplication(sys.argv)
    _apply_dark_theme(app)

    win = IEVRMainWindow()
    win.show()

    sys.exit(app.exec())