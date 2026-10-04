import sys
import time
import re
import os
import serial
import serial.tools.list_ports
import numpy as np

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtMultimedia import QSound
import pyqtgraph as pg
import pyqtgraph.opengl as gl


# =========================================================
# MAD HAT CNC SENDER
# =========================================================

APP_NAME = "MAD HAT CNC SENDER"
APP_VERSION = "V2.0"

LOGO_PATH = "Assets/madhat-cnc-logo.png"

BAUD_RATES = [
    "115200",
    "250000",
    "57600",
    "38400",
    "19200",
    "9600"
]


# =========================================================
# DARK MAD HAT STYLE
# =========================================================

APP_STYLE = """
QWidget {
    background: #111111;
    color: #eeeeee;
    font-family: Arial;
    font-size: 10pt;
}

QMainWindow {
    background: #0d0d0d;
}

QFrame#Header {
    background: #181818;
    border-bottom: 2px solid #f0a500;
}

QFrame#Card {
    background: #1a1a1a;
    border: 1px solid #303030;
    border-radius: 6px;
}

QFrame#Card:hover {
    border: 1px solid #444444;
}

QLabel#Brand {
    color: #f0a500;
    font-size: 21pt;
    font-weight: bold;
}

QLabel#BrandSub {
    color: #aaaaaa;
    font-size: 8pt;
}

QLabel#SectionTitle {
    color: #f0a500;
    font-size: 9pt;
    font-weight: bold;
}

QLabel#SmallLabel {
    color: #888888;
    font-size: 8pt;
}

QLabel#BigDRO {
    color: #ffffff;
    font-family: Consolas;
    font-size: 19pt;
    font-weight: bold;
}

QLabel#Status {
    color: #f0a500;
    font-size: 12pt;
    font-weight: bold;
}

QLabel#Value {
    color: #eeeeee;
    font-family: Consolas;
    font-size: 11pt;
}

QPushButton {
    background: #242424;
    border: 1px solid #3b3b3b;
    border-radius: 5px;
    padding: 7px;
    color: #eeeeee;
    font-weight: bold;
}

QPushButton:hover {
    background: #303030;
    border: 1px solid #f0a500;
}

QPushButton:pressed {
    background: #f0a500;
    color: #111111;
}

QPushButton:disabled {
    background: #171717;
    color: #555555;
    border: 1px solid #242424;
}

QPushButton#Play {
    background: #f0a500;
    color: #111111;
    font-size: 12pt;
}

QPushButton#Pause {
    background: #805800;
    color: #ffffff;
    font-size: 11pt;
}

QPushButton#Stop {
    background: #662222;
    color: #ffffff;
    font-size: 11pt;
}

QPushButton#Stop:hover {
    background: #8a2929;
}

QPushButton#Emergency {
    background: #8b0000;
    color: #ffffff;
    font-size: 11pt;
}

QPushButton#Emergency:hover {
    background: #b00000;
}

QPushButton#Jog {
    min-width: 62px;
    min-height: 42px;
    font-size: 11pt;
}

QPushButton#Zero {
    color: #f0a500;
}

QPushButton#Home {
    color: #f0a500;
}

QPushButton#Danger {
    color: #ff7777;
}

QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {
    background: #151515;
    border: 1px solid #383838;
    border-radius: 4px;
    padding: 6px;
    color: #eeeeee;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {
    border: 1px solid #f0a500;
}

QTextEdit,
QPlainTextEdit {
    background: #0a0a0a;
    border: 1px solid #303030;
    color: #dddddd;
    font-family: Consolas;
    font-size: 9pt;
}

QProgressBar {
    background: #0b0b0b;
    border: 1px solid #333333;
    border-radius: 5px;
    height: 15px;
    text-align: center;
    color: #ffffff;
}

QProgressBar::chunk {
    background: #f0a500;
    border-radius: 4px;
}

QSlider::groove:horizontal {
    height: 5px;
    background: #333333;
}

QSlider::handle:horizontal {
    background: #f0a500;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:vertical {
    background: #151515;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #444444;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #f0a500;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QTabWidget::pane {
    border: 1px solid #303030;
    background: #111111;
}

QTabBar::tab {
    background: #202020;
    color: #999999;
    padding: 7px 15px;
    border: 1px solid #303030;
}

QTabBar::tab:selected {
    color: #f0a500;
    background: #181818;
}

QGroupBox {
    border: 1px solid #303030;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #f0a500;
}
"""


# =========================================================
# CNC SENDER THREAD
# =========================================================

class SenderThread(QtCore.QThread):

    log_signal = QtCore.pyqtSignal(str)
    progress_signal = QtCore.pyqtSignal(int)
    line_signal = QtCore.pyqtSignal(int)
    feed_signal = QtCore.pyqtSignal(float)
    speed_signal = QtCore.pyqtSignal(float)
    status_signal = QtCore.pyqtSignal(float, float, float)
    machine_state_signal = QtCore.pyqtSignal(str)
    done_signal = QtCore.pyqtSignal()
    stopped_signal = QtCore.pyqtSignal()
    error_signal = QtCore.pyqtSignal(str)

    RX_BUFFER = 128
    SAFETY = 10

    def __init__(self, ser, gcode_lines):

        super().__init__()

        self.ser = ser
        self.gcode_lines = gcode_lines

        self._stop = False
        self._pause_requested = False

        self.in_flight = []
        self.bytes_in_flight = 0
        self.current_index = -1

    def stop(self):

        self._stop = True

    def run(self):

        idx = 0
        total = len(self.gcode_lines)

        last_status = time.time()

        while not self._stop:

            # -------------------------------------------------
            # SEND GCODE
            # -------------------------------------------------

            while (
                idx < total
                and
                self.bytes_in_flight < self.RX_BUFFER - self.SAFETY
                and
                not self._stop
            ):

                raw = self.gcode_lines[idx].strip()

                line_number = idx

                idx += 1

                if not raw:
                    continue

                raw = re.sub(
                    r"\([^)]*\)",
                    "",
                    raw
                )

                raw = raw.split(";")[0].strip()

                if not raw:
                    continue

                clean = re.sub(
                    r"^N\d+\s*",
                    "",
                    raw,
                    flags=re.IGNORECASE
                )

                line = clean + "\n"

                size = len(
                    line.encode(
                        "ascii",
                        errors="ignore"
                    )
                )

                if (
                    self.bytes_in_flight + size
                    >
                    self.RX_BUFFER - self.SAFETY
                ):

                    idx -= 1
                    break

                feed = re.search(
                    r"\bF([-+]?\d*\.?\d+)",
                    clean.upper()
                )

                if feed:

                    self.feed_signal.emit(
                        float(feed.group(1))
                    )

                speed = re.search(
                    r"\bS([-+]?\d*\.?\d+)",
                    clean.upper()
                )

                if speed:

                    self.speed_signal.emit(
                        float(speed.group(1))
                    )

                sent = False

                while (
                    not sent
                    and
                    not self._stop
                ):

                    try:

                        self.ser.write(
                            line.encode()
                        )

                        sent = True

                    except serial.SerialTimeoutException:

                        time.sleep(0.01)

                    except serial.SerialException as e:

                        self.error_signal.emit(
                            f"Serial write error: {e}"
                        )

                        self._stop = True
                        break

                if self._stop:
                    break

                self.in_flight.append(
                    (
                        line_number,
                        size
                    )
                )

                self.bytes_in_flight += size

                self.current_index = line_number

                self.line_signal.emit(
                    line_number
                )

                self.log_signal.emit(
                    f">> N{line_number + 1}: {clean}"
                )

                progress = int(
                    (
                        (line_number + 1)
                        /
                        max(total, 1)
                    )
                    * 100
                )

                self.progress_signal.emit(
                    min(progress, 100)
                )

            # -------------------------------------------------
            # READ GRBL
            # -------------------------------------------------

            try:

                while self.ser.in_waiting:

                    response = (
                        self.ser.readline()
                        .decode(errors="ignore")
                        .strip()
                    )

                    if not response:
                        continue

                    if response.startswith("<"):

                        self.parse_status(
                            response
                        )

                    elif response.lower().startswith("ok"):

                        self.log_signal.emit(
                            f"<< {response}"
                        )

                        if self.in_flight:

                            _, size = self.in_flight.pop(0)

                            self.bytes_in_flight -= size

                    elif response.lower().startswith("error"):

                        self.log_signal.emit(
                            f"<< {response}"
                        )

                        if self.in_flight:

                            _, size = self.in_flight.pop(0)

                            self.bytes_in_flight -= size

                    elif response.lower().startswith("alarm"):

                        self.log_signal.emit(
                            f"<< {response}"
                        )

                    else:

                        self.log_signal.emit(
                            f"<< {response}"
                        )

            except serial.SerialException as e:

                self.error_signal.emit(
                    f"Serial read error: {e}"
                )

                self._stop = True

            # -------------------------------------------------
            # STATUS QUERY
            # -------------------------------------------------

            if time.time() - last_status >= 0.10:

                try:

                    self.ser.write(
                        b"?"
                    )

                except Exception:
                    pass

                last_status = time.time()

            # -------------------------------------------------
            # COMPLETE
            # -------------------------------------------------

            if (
                idx >= total
                and
                not self.in_flight
            ):

                break

            time.sleep(0.001)

        if self._stop:

            self.log_signal.emit(
                "JOB STOPPED"
            )

            self.stopped_signal.emit()

        else:

            self.progress_signal.emit(100)

            self.log_signal.emit(
                "JOB COMPLETE"
            )

            self.done_signal.emit()

    def parse_status(self, status):

        state = re.match(
            r"<([^|,]+)",
            status
        )

        if state:

            self.machine_state_signal.emit(
                state.group(1)
            )

        mpos = re.search(
            r"MPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        wpos = re.search(
            r"WPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        wco = re.search(
            r"WCO:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        x = y = z = 0.0

        if wpos:

            x, y, z = map(
                float,
                wpos.groups()
            )

        elif mpos and wco:

            mx, my, mz = map(
                float,
                mpos.groups()
            )

            wx, wy, wz = map(
                float,
                wco.groups()
            )

            x = mx - wx
            y = my - wy
            z = mz - wz

        elif mpos:

            x, y, z = map(
                float,
                mpos.groups()
            )

        self.status_signal.emit(
            x,
            y,
            z
        )

        fs = re.search(
            r"FS:([0-9.]+),([0-9.]+)",
            status
        )

        if fs:

            self.feed_signal.emit(
                float(fs.group(1))
            )

            self.speed_signal.emit(
                float(fs.group(2))
            )


# =========================================================
# GCODE EDITOR
# =========================================================

class GCodeEditor(QtWidgets.QPlainTextEdit):

    line_clicked = QtCore.pyqtSignal(int)

    def __init__(self):

        super().__init__()

        self.setLineWrapMode(
            QtWidgets.QPlainTextEdit.NoWrap
        )

        self.setReadOnly(True)

        self.setFont(
            QtGui.QFont(
                "Consolas",
                9
            )
        )

        self.current_line = -1

    def highlight_line(self, line_number):

        self.current_line = line_number

        selection = QtWidgets.QTextEdit.ExtraSelection()

        selection.format.setBackground(
            QtGui.QColor("#f0a500")
        )

        selection.format.setForeground(
            QtGui.QColor("#111111")
        )

        selection.format.setProperty(
            QtGui.QTextFormat.FullWidthSelection,
            True
        )

        block = (
            self.document()
            .findBlockByNumber(
                line_number
            )
        )

        if block.isValid():

            selection.cursor = QtGui.QTextCursor(
                block
            )

            self.setExtraSelections(
                [selection]
            )

            self.setTextCursor(
                selection.cursor
            )

            self.ensureCursorVisible()

    def clear_highlight(self):

        self.current_line = -1

        self.setExtraSelections([])


# =========================================================
# MAIN WINDOW
# =========================================================

class CNCSender(QtWidgets.QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            f"{APP_NAME} {APP_VERSION}"
        )

        self.resize(
            1550,
            900
        )

        self.setMinimumSize(
            1100,
            700
        )

        self.ser = None
        self.sender = None

        self.gcode_lines = []
        self.current_file = ""

        self.job_start_time = None
        self.last_wco = None

        self.jog_buttons = []
        self.zero_buttons = []

        self.is_paused = False

        self.feed_override = 100
        self.spindle_override = 100

        self._build_ui()

        self.status_timer = QtCore.QTimer()

        self.status_timer.timeout.connect(
            self.poll_status
        )

        self.progress_timer = QtCore.QTimer()

        self.progress_timer.timeout.connect(
            self.update_progress_info
        )

        self.apply_styles()

        self.setAcceptDrops(True)

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):

        central = QtWidgets.QWidget()

        self.setCentralWidget(
            central
        )

        main = QtWidgets.QVBoxLayout(
            central
        )

        main.setContentsMargins(
            8,
            8,
            8,
            4
        )

        main.setSpacing(7)

        # =====================================================
        # HEADER
        # =====================================================

        header = QtWidgets.QFrame()

        header.setObjectName(
            "Header"
        )

        header.setFixedHeight(72)

        header_layout = QtWidgets.QHBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            12,
            5,
            15,
            5
        )

        logo = QtWidgets.QLabel()

        pixmap = QtGui.QPixmap(
            LOGO_PATH
        )

        if not pixmap.isNull():

            pixmap = pixmap.scaled(
                58,
                58,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )

            logo.setPixmap(
                pixmap
            )

        logo.setFixedWidth(70)

        logo.setAlignment(
            QtCore.Qt.AlignCenter
        )

        header_layout.addWidget(
            logo
        )

        brand_layout = QtWidgets.QVBoxLayout()

        brand = QtWidgets.QLabel(
            "MAD HAT"
        )

        brand.setObjectName(
            "Brand"
        )

        brand_sub = QtWidgets.QLabel(
            "CNC CONTROL SOFTWARE"
        )

        brand_sub.setObjectName(
            "BrandSub"
        )

        brand_layout.addWidget(
            brand
        )

        brand_layout.addWidget(
            brand_sub
        )

        header_layout.addLayout(
            brand_layout
        )

        header_layout.addStretch()

        self.header_status = QtWidgets.QLabel(
            "● DISCONNECTED"
        )

        self.header_status.setObjectName(
            "Status"
        )

        header_layout.addWidget(
            self.header_status
        )

        header_layout.addSpacing(20)

        version = QtWidgets.QLabel(
            APP_VERSION
        )

        version.setStyleSheet(
            "color:#777777;"
        )

        header_layout.addWidget(
            version
        )

        main.addWidget(
            header
        )

        # =====================================================
        # WORKSPACE
        # =====================================================

        workspace = QtWidgets.QHBoxLayout()

        workspace.setSpacing(7)

        main.addLayout(
            workspace,
            1
        )

        # =====================================================
        # LEFT SCROLL
        # =====================================================

        left_scroll = QtWidgets.QScrollArea()

        left_scroll.setFixedWidth(350)

        left_scroll.setWidgetResizable(True)

        left_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )

        left_scroll.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        left_container = QtWidgets.QWidget()

        left_scroll.setWidget(
            left_container
        )

        left = QtWidgets.QVBoxLayout(
            left_container
        )

        left.setContentsMargins(
            0,
            0,
            2,
            0
        )

        left.setSpacing(7)

        workspace.addWidget(
            left_scroll
        )

        # =====================================================
        # CONNECTION
        # =====================================================

        connection = self.make_card()

        c = QtWidgets.QVBoxLayout(
            connection
        )

        c.addWidget(
            self.section_title(
                "CONNECTION"
            )
        )

        port_row = QtWidgets.QHBoxLayout()

        self.port_box = QtWidgets.QComboBox()

        self.refresh_ports()

        self.refresh_btn = QtWidgets.QPushButton(
            "⟳"
        )

        self.refresh_btn.setFixedWidth(
            40
        )

        port_row.addWidget(
            self.port_box,
            1
        )

        port_row.addWidget(
            self.refresh_btn
        )

        c.addLayout(
            port_row
        )

        baud_row = QtWidgets.QHBoxLayout()

        baud_row.addWidget(
            self.small_label(
                "BAUD"
            )
        )

        self.baud_box = QtWidgets.QComboBox()

        self.baud_box.addItems(
            BAUD_RATES
        )

        self.baud_box.setCurrentText(
            "115200"
        )

        baud_row.addWidget(
            self.baud_box
        )

        c.addLayout(
            baud_row
        )

        conn_buttons = QtWidgets.QHBoxLayout()

        self.connect_btn = QtWidgets.QPushButton(
            "CONNECT"
        )

        self.disconnect_btn = QtWidgets.QPushButton(
            "DISCONNECT"
        )

        self.disconnect_btn.setEnabled(
            False
        )

        conn_buttons.addWidget(
            self.connect_btn
        )

        conn_buttons.addWidget(
            self.disconnect_btn
        )

        c.addLayout(
            conn_buttons
        )

        self.refresh_btn.clicked.connect(
            self.refresh_ports
        )

        self.connect_btn.clicked.connect(
            self.connect
        )

        self.disconnect_btn.clicked.connect(
            self.disconnect
        )

        left.addWidget(
            connection
        )

        # =====================================================
        # JOB FILE
        # =====================================================

        file_card = self.make_card()

        f = QtWidgets.QVBoxLayout(
            file_card
        )

        f.addWidget(
            self.section_title(
                "JOB FILE"
            )
        )

        file_buttons = QtWidgets.QHBoxLayout()

        self.load_btn = QtWidgets.QPushButton(
            "LOAD G-CODE"
        )

        self.clear_btn = QtWidgets.QPushButton(
            "CLEAR"
        )

        file_buttons.addWidget(
            self.load_btn,
            1
        )

        file_buttons.addWidget(
            self.clear_btn
        )

        f.addLayout(
            file_buttons
        )

        self.file_label = QtWidgets.QLabel(
            "No file loaded"
        )

        self.file_label.setWordWrap(
            True
        )

        self.file_label.setObjectName(
            "SmallLabel"
        )

        f.addWidget(
            self.file_label
        )

        self.load_btn.clicked.connect(
            self.load_gcode
        )

        self.clear_btn.clicked.connect(
            self.clear_gcode
        )

        left.addWidget(
            file_card
        )

        # =====================================================
        # JOB CONTROL
        # =====================================================

        job_card = self.make_card()

        j = QtWidgets.QVBoxLayout(
            job_card
        )

        j.addWidget(
            self.section_title(
                "JOB CONTROL"
            )
        )

        row1 = QtWidgets.QHBoxLayout()

        self.play_btn = QtWidgets.QPushButton(
            "▶ PLAY"
        )

        self.play_btn.setObjectName(
            "Play"
        )

        self.pause_btn = QtWidgets.QPushButton(
            "Ⅱ PAUSE"
        )

        self.pause_btn.setObjectName(
            "Pause"
        )

        self.stop_btn = QtWidgets.QPushButton(
            "■ STOP"
        )

        self.stop_btn.setObjectName(
            "Stop"
        )

        row1.addWidget(
            self.play_btn
        )

        row1.addWidget(
            self.pause_btn
        )

        row1.addWidget(
            self.stop_btn
        )

        j.addLayout(
            row1
        )

        row2 = QtWidgets.QHBoxLayout()

        self.resume_btn = QtWidgets.QPushButton(
            "▶ RESUME"
        )

        self.resume_btn.setEnabled(
            False
        )

        self.check_btn = QtWidgets.QPushButton(
            "CHECK"
        )

        row2.addWidget(
            self.resume_btn
        )

        row2.addWidget(
            self.check_btn
        )

        j.addLayout(
            row2
        )

        self.progress_bar = QtWidgets.QProgressBar()

        j.addWidget(
            self.progress_bar
        )

        time_row = QtWidgets.QHBoxLayout()

        self.run_time_label = QtWidgets.QLabel(
            "RUN 00:00:00"
        )

        self.eta_label = QtWidgets.QLabel(
            "ETA --:--:--"
        )

        time_row.addWidget(
            self.run_time_label
        )

        time_row.addStretch()

        time_row.addWidget(
            self.eta_label
        )

        j.addLayout(
            time_row
        )

        self.play_btn.clicked.connect(
            self.play
        )

        self.pause_btn.clicked.connect(
            self.pause_job
        )

        self.resume_btn.clicked.connect(
            self.resume_job
        )

        self.stop_btn.clicked.connect(
            self.stop
        )

        self.check_btn.clicked.connect(
            self.check_gcode
        )

        left.addWidget(
            job_card
        )

        # =====================================================
        # MACHINE COMMANDS
        # =====================================================

        machine_card = self.make_card()

        mc = QtWidgets.QVBoxLayout(
            machine_card
        )

        mc.addWidget(
            self.section_title(
                "MACHINE CONTROL"
            )
        )

        machine_grid = QtWidgets.QGridLayout()

        self.home_btn = QtWidgets.QPushButton(
            "$H  HOME"
        )

        self.home_btn.setObjectName(
            "Home"
        )

        self.unlock_btn = QtWidgets.QPushButton(
            "$X  UNLOCK"
        )

        self.reset_btn = QtWidgets.QPushButton(
            "SOFT RESET"
        )

        self.reset_btn.setObjectName(
            "Danger"
        )

        self.zero_all_btn = QtWidgets.QPushButton(
            "ZERO ALL"
        )

        self.go_zero_btn = QtWidgets.QPushButton(
            "GO TO ZERO"
        )

        machine_grid.addWidget(
            self.home_btn,
            0,
            0
        )

        machine_grid.addWidget(
            self.unlock_btn,
            0,
            1
        )

        machine_grid.addWidget(
            self.zero_all_btn,
            1,
            0
        )

        machine_grid.addWidget(
            self.go_zero_btn,
            1,
            1
        )

        machine_grid.addWidget(
            self.reset_btn,
            2,
            0,
            1,
            2
        )

        mc.addLayout(
            machine_grid
        )

        self.home_btn.clicked.connect(
            self.home_machine
        )

        self.unlock_btn.clicked.connect(
            lambda:
            self.send_command("$X")
        )

        self.reset_btn.clicked.connect(
            self.soft_reset
        )

        self.zero_all_btn.clicked.connect(
            self.zero_all
        )

        self.go_zero_btn.clicked.connect(
            self.go_zero
        )

        self.zero_buttons.extend(
            [
                self.home_btn,
                self.unlock_btn,
                self.reset_btn,
                self.zero_all_btn,
                self.go_zero_btn
            ]
        )

        left.addWidget(
            machine_card
        )

        # =====================================================
        # JOG
        # =====================================================

        jog_card = self.make_card()

        g = QtWidgets.QVBoxLayout(
            jog_card
        )

        g.addWidget(
            self.section_title(
                "JOG CONTROL"
            )
        )

        distance_row = QtWidgets.QHBoxLayout()

        distance_row.addWidget(
            self.small_label(
                "STEP"
            )
        )

        self.jog_distance_box = QtWidgets.QComboBox()

        self.jog_distance_box.addItems(
            [
                "0.1",
                "0.5",
                "1",
                "5",
                "10",
                "25",
                "50",
                "100"
            ]
        )

        self.jog_distance_box.setCurrentText(
            "1"
        )

        distance_row.addWidget(
            self.jog_distance_box
        )

        distance_row.addWidget(
            self.small_label(
                "mm"
            )
        )

        g.addLayout(
            distance_row
        )

        speed_row = QtWidgets.QHBoxLayout()

        speed_row.addWidget(
            self.small_label(
                "FEED"
            )
        )

        self.jog_speed_box = QtWidgets.QSpinBox()

        self.jog_speed_box.setRange(
            1,
            30000
        )

        self.jog_speed_box.setValue(
            1000
        )

        speed_row.addWidget(
            self.jog_speed_box
        )

        speed_row.addWidget(
            self.small_label(
                "mm/min"
            )
        )

        g.addLayout(
            speed_row
        )

        jog_grid = QtWidgets.QGridLayout()

        jog_grid.addWidget(
            self.make_jog("Y+"),
            0,
            1
        )

        jog_grid.addWidget(
            self.make_jog("X-"),
            1,
            0
        )

        jog_grid.addWidget(
            self.make_jog("X+"),
            1,
            2
        )

        jog_grid.addWidget(
            self.make_jog("Y-"),
            2,
            1
        )

        jog_grid.addWidget(
            self.make_jog("Z+"),
            3,
            0
        )

        jog_grid.addWidget(
            self.make_jog("Z-"),
            3,
            2
        )

        g.addLayout(
            jog_grid
        )

        left.addWidget(
            jog_card
        )

        # =====================================================
        # ZERO AXES
        # =====================================================

        zero_card = self.make_card()

        z = QtWidgets.QVBoxLayout(
            zero_card
        )

        z.addWidget(
            self.section_title(
                "WORK ZERO"
            )
        )

        zero_grid = QtWidgets.QGridLayout()

        for column, axis in enumerate(
            ["X", "Y", "Z"]
        ):

            btn = QtWidgets.QPushButton(
                f"{axis} ZERO"
            )

            btn.setObjectName(
                "Zero"
            )

            btn.clicked.connect(
                lambda checked=False,
                a=axis:
                self.zero_axis(a)
            )

            self.zero_buttons.append(
                btn
            )

            zero_grid.addWidget(
                btn,
                0,
                column
            )

        z.addLayout(
            zero_grid
        )

        left.addWidget(
            zero_card
        )

        # =====================================================
        # SPINDLE
        # =====================================================

        spindle_card = self.make_card()

        sp = QtWidgets.QVBoxLayout(
            spindle_card
        )

        sp.addWidget(
            self.section_title(
                "SPINDLE"
            )
        )

        rpm_row = QtWidgets.QHBoxLayout()

        rpm_row.addWidget(
            self.small_label(
                "RPM"
            )
        )

        self.rpm_box = QtWidgets.QSpinBox()

        self.rpm_box.setRange(
            0,
            100000
        )

        self.rpm_box.setValue(
            10000
        )

        rpm_row.addWidget(
            self.rpm_box
        )

        sp.addLayout(
            rpm_row
        )

        spindle_buttons = QtWidgets.QGridLayout()

        self.spindle_cw_btn = QtWidgets.QPushButton(
            "M3  CW"
        )

        self.spindle_ccw_btn = QtWidgets.QPushButton(
            "M4  CCW"
        )

        self.spindle_off_btn = QtWidgets.QPushButton(
            "M5  OFF"
        )

        spindle_buttons.addWidget(
            self.spindle_cw_btn,
            0,
            0
        )

        spindle_buttons.addWidget(
            self.spindle_ccw_btn,
            0,
            1
        )

        spindle_buttons.addWidget(
            self.spindle_off_btn,
            1,
            0,
            1,
            2
        )

        sp.addLayout(
            spindle_buttons
        )

        self.spindle_cw_btn.clicked.connect(
            self.spindle_cw
        )

        self.spindle_ccw_btn.clicked.connect(
            self.spindle_ccw
        )

        self.spindle_off_btn.clicked.connect(
            lambda:
            self.send_command("M5")
        )

        left.addWidget(
            spindle_card
        )

        # =====================================================
        # COOLANT
        # =====================================================

        coolant_card = self.make_card()

        co = QtWidgets.QVBoxLayout(
            coolant_card
        )

        co.addWidget(
            self.section_title(
                "COOLANT"
            )
        )

        coolant_grid = QtWidgets.QGridLayout()

        flood = QtWidgets.QPushButton(
            "M8 FLOOD"
        )

        mist = QtWidgets.QPushButton(
            "M7 MIST"
        )

        off = QtWidgets.QPushButton(
            "M9 OFF"
        )

        coolant_grid.addWidget(
            flood,
            0,
            0
        )

        coolant_grid.addWidget(
            mist,
            0,
            1
        )

        coolant_grid.addWidget(
            off,
            1,
            0,
            1,
            2
        )

        co.addLayout(
            coolant_grid
        )

        flood.clicked.connect(
            lambda:
            self.send_command("M8")
        )

        mist.clicked.connect(
            lambda:
            self.send_command("M7")
        )

        off.clicked.connect(
            lambda:
            self.send_command("M9")
        )

        left.addWidget(
            coolant_card
        )

        # =====================================================
        # OVERRIDES
        # =====================================================

        override_card = self.make_card()

        ov = QtWidgets.QVBoxLayout(
            override_card
        )

        ov.addWidget(
            self.section_title(
                "REALTIME OVERRIDES"
            )
        )

        feed_title = QtWidgets.QHBoxLayout()

        feed_title.addWidget(
            self.small_label(
                "FEED OVERRIDE"
            )
        )

        self.feed_override_label = QtWidgets.QLabel(
            "100%"
        )

        self.feed_override_label.setObjectName(
            "Value"
        )

        feed_title.addStretch()

        feed_title.addWidget(
            self.feed_override_label
        )

        ov.addLayout(
            feed_title
        )

        feed_buttons = QtWidgets.QHBoxLayout()

        feed_minus = QtWidgets.QPushButton(
            "-10%"
        )

        feed_reset = QtWidgets.QPushButton(
            "100%"
        )

        feed_plus = QtWidgets.QPushButton(
            "+10%"
        )

        feed_buttons.addWidget(
            feed_minus
        )

        feed_buttons.addWidget(
            feed_reset
        )

        feed_buttons.addWidget(
            feed_plus
        )

        ov.addLayout(
            feed_buttons
        )

        feed_minus.clicked.connect(
            lambda:
            self.feed_override_change(-10)
        )

        feed_reset.clicked.connect(
            lambda:
            self.feed_override_set(100)
        )

        feed_plus.clicked.connect(
            lambda:
            self.feed_override_change(10)
        )

        spindle_title = QtWidgets.QHBoxLayout()

        spindle_title.addWidget(
            self.small_label(
                "SPINDLE OVERRIDE"
            )
        )

        self.spindle_override_label = QtWidgets.QLabel(
            "100%"
        )

        self.spindle_override_label.setObjectName(
            "Value"
        )

        spindle_title.addStretch()

        spindle_title.addWidget(
            self.spindle_override_label
        )

        ov.addLayout(
            spindle_title
        )

        spindle_buttons = QtWidgets.QHBoxLayout()

        sm = QtWidgets.QPushButton(
            "-10%"
        )

        sr = QtWidgets.QPushButton(
            "100%"
        )

        sx = QtWidgets.QPushButton(
            "+10%"
        )

        spindle_buttons.addWidget(
            sm
        )

        spindle_buttons.addWidget(
            sr
        )

        spindle_buttons.addWidget(
            sx
        )

        ov.addLayout(
            spindle_buttons
        )

        sm.clicked.connect(
            lambda:
            self.spindle_override_change(-10)
        )

        sr.clicked.connect(
            lambda:
            self.spindle_override_set(100)
        )

        sx.clicked.connect(
            lambda:
            self.spindle_override_change(10)
        )

        left.addWidget(
            override_card
        )

        left.addStretch()

        # =====================================================
        # RIGHT SIDE
        # =====================================================

        right = QtWidgets.QVBoxLayout()

        right.setSpacing(
            7
        )

        workspace.addLayout(
            right,
            1
        )

        # =====================================================
        # DRO
        # =====================================================

        dro_card = self.make_card()

        dro_layout = QtWidgets.QHBoxLayout(
            dro_card
        )

        state_box = QtWidgets.QVBoxLayout()

        state_box.addWidget(
            self.section_title(
                "MACHINE"
            )
        )

        self.state_label = QtWidgets.QLabel(
            "DISCONNECTED"
        )

        self.state_label.setObjectName(
            "Status"
        )

        state_box.addWidget(
            self.state_label
        )

        dro_layout.addLayout(
            state_box
        )

        dro_layout.addStretch()

        self.dro_x = self.make_dro("X")
        self.dro_y = self.make_dro("Y")
        self.dro_z = self.make_dro("Z")

        dro_layout.addLayout(
            self.dro_x
        )

        dro_layout.addLayout(
            self.dro_y
        )

        dro_layout.addLayout(
            self.dro_z
        )

        fs = QtWidgets.QVBoxLayout()

        fs.addWidget(
            self.section_title(
                "LIVE"
            )
        )

        self.feed_label = QtWidgets.QLabel(
            "F 0"
        )

        self.feed_label.setObjectName(
            "Value"
        )

        self.speed_label = QtWidgets.QLabel(
            "S 0"
        )

        self.speed_label.setObjectName(
            "Value"
        )

        fs.addWidget(
            self.feed_label
        )

        fs.addWidget(
            self.speed_label
        )

        dro_layout.addSpacing(
            15
        )

        dro_layout.addLayout(
            fs
        )

        right.addWidget(
            dro_card
        )

        # =====================================================
        # TABS
        # =====================================================

        tabs = QtWidgets.QTabWidget()

        # =====================================================
        # 3D TOOLPATH TAB
        # =====================================================

        visual_page = QtWidgets.QWidget()

        vp = QtWidgets.QVBoxLayout(
            visual_page
        )

        visual_header = QtWidgets.QHBoxLayout()

        visual_header.addWidget(
            self.section_title(
                "3D TOOLPATH VISUALISER"
            )
        )

        visual_header.addStretch()

        self.view_top_btn = QtWidgets.QPushButton(
            "TOP"
        )

        self.view_front_btn = QtWidgets.QPushButton(
            "FRONT"
        )

        self.view_right_btn = QtWidgets.QPushButton(
            "RIGHT"
        )

        self.view_iso_btn = QtWidgets.QPushButton(
            "ISO"
        )

        self.fit_btn = QtWidgets.QPushButton(
            "FIT"
        )

        self.clear_view_btn = QtWidgets.QPushButton(
            "CLEAR"
        )

        self.view_top_btn.setFixedWidth(
            60
        )

        self.view_front_btn.setFixedWidth(
            65
        )

        self.view_right_btn.setFixedWidth(
            65
        )

        self.view_iso_btn.setFixedWidth(
            60
        )

        self.fit_btn.setFixedWidth(
            55
        )

        self.clear_view_btn.setFixedWidth(
            65
        )

        visual_header.addWidget(
            self.view_top_btn
        )

        visual_header.addWidget(
            self.view_front_btn
        )

        visual_header.addWidget(
            self.view_right_btn
        )

        visual_header.addWidget(
            self.view_iso_btn
        )

        visual_header.addWidget(
            self.fit_btn
        )

        visual_header.addWidget(
            self.clear_view_btn
        )

        vp.addLayout(
            visual_header
        )

        # -----------------------------------------------------
        # 3D VIEW
        # -----------------------------------------------------

        self.plot = gl.GLViewWidget()

        self.plot.setBackgroundColor(
            (8, 8, 8)
        )

        self.plot.setCameraPosition(
            distance=200,
            elevation=30,
            azimuth=-45
        )

        vp.addWidget(
            self.plot,
            1
        )

        # -----------------------------------------------------
        # GRID
        # -----------------------------------------------------

        self.grid = gl.GLGridItem()

        self.grid.setSize(
            200,
            200
        )

        self.grid.setSpacing(
            10,
            10
        )

        self.plot.addItem(
            self.grid
        )

        # -----------------------------------------------------
        # AXES
        # -----------------------------------------------------

        self.axis_x = gl.GLLinePlotItem(
            pos=np.array(
                [
                    [0, 0, 0],
                    [100, 0, 0]
                ],
                dtype=float
            ),
            color=(1.0, 0.25, 0.15, 1.0),
            width=2,
            antialias=True,
            mode="lines"
        )

        self.axis_y = gl.GLLinePlotItem(
            pos=np.array(
                [
                    [0, 0, 0],
                    [0, 100, 0]
                ],
                dtype=float
            ),
            color=(0.25, 1.0, 0.25, 1.0),
            width=2,
            antialias=True,
            mode="lines"
        )

        self.axis_z = gl.GLLinePlotItem(
            pos=np.array(
                [
                    [0, 0, 0],
                    [0, 0, 100]
                ],
                dtype=float
            ),
            color=(0.25, 0.55, 1.0, 1.0),
            width=2,
            antialias=True,
            mode="lines"
        )

        self.plot.addItem(
            self.axis_x
        )

        self.plot.addItem(
            self.axis_y
        )

        self.plot.addItem(
            self.axis_z
        )

        # -----------------------------------------------------
        # TOOLPATH
        # -----------------------------------------------------

        self.cut_3d = gl.GLLinePlotItem(
            color=(0.0, 1.0, 1.0, 1.0),
            width=2,
            antialias=True,
            mode="lines"
        )

        self.rapid_3d = gl.GLLinePlotItem(
            color=(1.0, 0.0, 0.0, 1.0),
            width=1,
            antialias=True,
            mode="lines"
        )

        self.plot.addItem(
            self.rapid_3d
        )

        self.plot.addItem(
            self.cut_3d
        )

        # -----------------------------------------------------
        # TOOL
        # -----------------------------------------------------

        self.tool_3d = gl.GLScatterPlotItem(
            pos=np.array(
                [[0, 0, 0]],
                dtype=float
            ),
            size=12,
            color=(1.0, 0.15, 0.15, 1.0),
            pxMode=True
        )

        self.plot.addItem(
            self.tool_3d
        )

        # -----------------------------------------------------
        # VISUALISER DATA
        # -----------------------------------------------------

        self.cut_points_3d = np.empty(
            (0, 3),
            dtype=float
        )

        self.rapid_points_3d = np.empty(
            (0, 3),
            dtype=float
        )

        # -----------------------------------------------------
        # BUTTONS
        # -----------------------------------------------------

        self.fit_btn.clicked.connect(
            self.fit_visualiser
        )

        self.clear_view_btn.clicked.connect(
            self.clear_visualiser
        )

        self.view_top_btn.clicked.connect(
            self.view_top
        )

        self.view_front_btn.clicked.connect(
            self.view_front
        )

        self.view_right_btn.clicked.connect(
            self.view_right
        )

        self.view_iso_btn.clicked.connect(
            self.view_iso
        )

        tabs.addTab(
            visual_page,
            "3D TOOLPATH"
        )

        # =====================================================
        # GCODE TAB
        # =====================================================

        gcode_page = QtWidgets.QWidget()

        gp = QtWidgets.QVBoxLayout(
            gcode_page
        )

        gcode_header = QtWidgets.QHBoxLayout()

        gcode_header.addWidget(
            self.section_title(
                "G-CODE PROGRAM"
            )
        )

        gcode_header.addStretch()

        self.gcode_line_label = QtWidgets.QLabel(
            "LINE 0 / 0"
        )

        self.gcode_line_label.setObjectName(
            "Value"
        )

        gcode_header.addWidget(
            self.gcode_line_label
        )

        gp.addLayout(
            gcode_header
        )

        self.gcode_editor = GCodeEditor()

        gp.addWidget(
            self.gcode_editor,
            1
        )

        tabs.addTab(
            gcode_page,
            "G-CODE"
        )

        # =====================================================
        # CONSOLE TAB
        # =====================================================

        console_page = QtWidgets.QWidget()

        cp = QtWidgets.QVBoxLayout(
            console_page
        )

        console_header = QtWidgets.QHBoxLayout()

        console_header.addWidget(
            self.section_title(
                "GRBL CONSOLE"
            )
        )

        console_header.addStretch()

        self.clear_console_btn = QtWidgets.QPushButton(
            "CLEAR"
        )

        self.clear_console_btn.setFixedWidth(
            70
        )

        console_header.addWidget(
            self.clear_console_btn
        )

        cp.addLayout(
            console_header
        )

        self.log_box = QtWidgets.QTextEdit()

        self.log_box.setReadOnly(
            True
        )

        cp.addWidget(
            self.log_box,
            1
        )

        command_row = QtWidgets.QHBoxLayout()

        self.cmd_input = QtWidgets.QLineEdit()

        self.cmd_input.setPlaceholderText(
            "Manual GRBL command..."
        )

        self.cmd_send_btn = QtWidgets.QPushButton(
            "SEND"
        )

        command_row.addWidget(
            self.cmd_input,
            1
        )

        command_row.addWidget(
            self.cmd_send_btn
        )

        cp.addLayout(
            command_row
        )

        self.cmd_send_btn.clicked.connect(
            self.send_manual_command
        )

        self.cmd_input.returnPressed.connect(
            self.send_manual_command
        )

        self.clear_console_btn.clicked.connect(
            self.log_box.clear
        )

        tabs.addTab(
            console_page,
            "CONSOLE"
        )

        right.addWidget(
            tabs,
            1
        )

        # =====================================================
        # FOOTER
        # =====================================================

        footer = QtWidgets.QLabel(
            "MAD HAT  •  CNC CONTROL SOFTWARE  •  "
            "CNC / LASER / 3D PRINTING"
        )

        footer.setAlignment(
            QtCore.Qt.AlignCenter
        )

        footer.setStyleSheet("""
            QLabel {
                color: #555555;
                font-size: 8pt;
                padding: 3px;
            }
        """)

        main.addWidget(
            footer
        )

        self.update_button_state()

    # =========================================================
    # HELPERS
    # =========================================================

    def make_card(self):

        frame = QtWidgets.QFrame()

        frame.setObjectName(
            "Card"
        )

        return frame

    def section_title(self, text):

        label = QtWidgets.QLabel(
            text
        )

        label.setObjectName(
            "SectionTitle"
        )

        return label

    def small_label(self, text):

        label = QtWidgets.QLabel(
            text
        )

        label.setObjectName(
            "SmallLabel"
        )

        return label

    # =========================================================
    # DRO
    # =========================================================

    def make_dro(self, axis):

        layout = QtWidgets.QVBoxLayout()

        title = QtWidgets.QLabel(
            axis
        )

        title.setObjectName(
            "SmallLabel"
        )

        value = QtWidgets.QLabel(
            "0.000"
        )

        value.setObjectName(
            "BigDRO"
        )

        if axis == "X":
            self.dro_x_value = value

        elif axis == "Y":
            self.dro_y_value = value

        elif axis == "Z":
            self.dro_z_value = value

        layout.addWidget(
            title
        )

        layout.addWidget(
            value
        )

        return layout

    # =========================================================
    # JOG BUTTON
    # =========================================================

    def make_jog(self, direction):

        button = QtWidgets.QPushButton(
            direction
        )

        button.setObjectName(
            "Jog"
        )

        button.clicked.connect(
            lambda checked=False,
            d=direction:
            self.jog(d)
        )

        self.jog_buttons.append(
            button
        )

        return button

    # =========================================================
    # STYLE
    # =========================================================

    def apply_styles(self):

        self.setStyleSheet(
            APP_STYLE
        )

    # =========================================================
    # PORTS
    # =========================================================

    def refresh_ports(self):

        if not hasattr(
            self,
            "port_box"
        ):
            return

        current = self.port_box.currentText()

        self.port_box.clear()

        for port in serial.tools.list_ports.comports():

            description = port.description or ""

            text = (
                f"{port.device} - "
                f"{description}"
            )

            self.port_box.addItem(
                text,
                port.device
            )

        if current:

            for i in range(
                self.port_box.count()
            ):

                if (
                    self.port_box.itemText(i)
                    == current
                ):

                    self.port_box.setCurrentIndex(
                        i
                    )

                    break

    # =========================================================
    # SELECTED PORT
    # =========================================================

    def selected_port(self):

        data = self.port_box.currentData()

        if data:
            return data

        text = self.port_box.currentText()

        return text.split(
            " - "
        )[0]

    # =========================================================
    # CONNECT
    # =========================================================

    def connect(self):

        if self.ser:
            return

        port = self.selected_port()

        if not port:

            self.log(
                "NO SERIAL PORT SELECTED"
            )

            return

        baud = int(
            self.baud_box.currentText()
        )

        try:

            self.ser = serial.Serial(
                port=port,
                baudrate=baud,
                timeout=0.05,
                write_timeout=1
            )

            time.sleep(2)

            self.ser.reset_input_buffer()

            self.log(
                f"CONNECTED: {port} @ {baud}"
            )

            try:

                QSound.play(
                    "Assets/connected.wav"
                )

            except Exception:
                pass

            self.connect_btn.setEnabled(
                False
            )

            self.disconnect_btn.setEnabled(
                True
            )

            self.status_timer.start(
                100
            )

            self.update_button_state()

            self.request_status()

        except Exception as e:

            self.ser = None

            self.log(
                f"CONNECTION ERROR: {e}"
            )

    # =========================================================
    # DISCONNECT
    # =========================================================

    def disconnect(self):

        if (
            self.sender
            and
            self.sender.isRunning()
        ):

            self.log(
                "STOP THE CURRENT JOB FIRST"
            )

            return

        if self.ser:

            try:
                self.ser.close()

            except Exception:
                pass

            self.ser = None

        self.status_timer.stop()

        self.connect_btn.setEnabled(
            True
        )

        self.disconnect_btn.setEnabled(
            False
        )

        self.state_label.setText(
            "DISCONNECTED"
        )

        self.header_status.setText(
            "● DISCONNECTED"
        )

        self.update_button_state()

        self.log(
            "DISCONNECTED"
        )

        try:

            QSound.play(
                "Assets/disconnected.wav"
            )

        except Exception:
            pass

    # =========================================================
    # LOAD GCODE
    # =========================================================

    def load_gcode(self, path=None):

        if not path:

            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Load G-code",
                "",
                "G-code (*.nc *.gcode *.tap *.ngc *.txt)"
            )

        if not path:
            return

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                self.gcode_lines = file.readlines()

        except Exception as e:

            self.log(
                f"LOAD ERROR: {e}"
            )

            return

        self.current_file = path

        filename = os.path.basename(
            path
        )

        self.file_label.setText(
            f"{filename}\n"
            f"{len(self.gcode_lines):,} lines"
        )

        self.gcode_editor.setPlainText(
            "".join(
                self.gcode_lines
            )
        )

        self.gcode_editor.clear_highlight()

        self.gcode_line_label.setText(
            f"LINE 0 / "
            f"{len(self.gcode_lines):,}"
        )

        self.log(
            f"LOADED: {filename}"
        )

        self.plot_gcode()

        self.progress_bar.setValue(
            0
        )

        self.run_time_label.setText(
            "RUN 00:00:00"
        )

        self.eta_label.setText(
            "ETA --:--:--"
        )

        self.update_button_state()

    # =========================================================
    # DRAG DROP
    # =========================================================

    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls():

            event.acceptProposedAction()

    def dropEvent(self, event):

        for url in event.mimeData().urls():

            path = url.toLocalFile()

            if path.lower().endswith(
                (
                    ".nc",
                    ".gcode",
                    ".tap",
                    ".ngc",
                    ".txt"
                )
            ):

                self.load_gcode(
                    path
                )

                break

    # =========================================================
    # CLEAR GCODE
    # =========================================================

    def clear_gcode(self):

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        self.gcode_lines = []
        self.current_file = ""

        self.file_label.setText(
            "No file loaded"
        )

        self.gcode_editor.clear()
        self.gcode_editor.clear_highlight()

        self.gcode_line_label.setText(
            "LINE 0 / 0"
        )

        self.progress_bar.setValue(
            0
        )

        self.clear_visualiser()

        self.update_button_state()

    # =========================================================
    # PLAY
    # =========================================================

    def play(self):

        if not self.ser:

            self.log(
                "NOT CONNECTED"
            )

            return

        if not self.gcode_lines:

            self.log(
                "NO G-CODE LOADED"
            )

            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        self.is_paused = False

        self.job_start_time = time.time()

        self.progress_bar.setValue(
            0
        )

        self.gcode_editor.clear_highlight()

        self.gcode_line_label.setText(
            f"LINE 0 / "
            f"{len(self.gcode_lines):,}"
        )

        self.run_time_label.setText(
            "RUN 00:00:00"
        )

        self.eta_label.setText(
            "ETA calculating..."
        )

        self.sender = SenderThread(
            self.ser,
            self.gcode_lines
        )

        self.sender.log_signal.connect(
            self.log
        )

        self.sender.progress_signal.connect(
            self.progress_bar.setValue
        )

        self.sender.line_signal.connect(
            self.highlight_gcode_line
        )

        self.sender.feed_signal.connect(
            lambda value:
            self.feed_label.setText(
                f"F {value:.0f}"
            )
        )

        self.sender.speed_signal.connect(
            lambda value:
            self.speed_label.setText(
                f"S {value:.0f}"
            )
        )

        self.sender.status_signal.connect(
            self.update_tool_position
        )

        self.sender.machine_state_signal.connect(
            self.update_machine_state
        )

        self.sender.done_signal.connect(
            self.job_finished
        )

        self.sender.stopped_signal.connect(
            self.job_stopped
        )

        self.sender.error_signal.connect(
            self.handle_sender_error
        )

        self.sender.finished.connect(
            self.thread_finished
        )

        self.status_timer.stop()

        self.progress_timer.start(
            200
        )

        self.sender.start()

        self.update_button_state()

        self.log(
            "JOB STARTED"
        )

    # =========================================================
    # PAUSE
    # =========================================================

    def pause_job(self):

        if not self.ser:
            return

        if (
            not self.sender
            or
            not self.sender.isRunning()
        ):
            return

        try:

            self.ser.write(
                b"!"
            )

            self.is_paused = True

            self.log(
                "FEED HOLD / PAUSED"
            )

        except Exception as e:

            self.log(
                f"PAUSE ERROR: {e}"
            )

        self.update_button_state()

    # =========================================================
    # RESUME
    # =========================================================

    def resume_job(self):

        if not self.ser:
            return

        try:

            self.ser.write(
                b"~"
            )

            self.is_paused = False

            self.log(
                "CYCLE START / RESUMED"
            )

        except Exception as e:

            self.log(
                f"RESUME ERROR: {e}"
            )

        self.update_button_state()

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        if not self.ser:
            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Stop Job",
            "STOP the current CNC job?\n\n"
            "The machine will be stopped and "
            "the current job will not resume "
            "from the same line.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        try:

            self.ser.write(
                b"!"
            )

            time.sleep(
                0.05
            )

            self.ser.write(
                b"M5\n"
            )

        except Exception:
            pass

        if self.sender:
            self.sender.stop()

        self.stop_btn.setEnabled(
            False
        )

        self.log(
            "STOP REQUESTED"
        )

    # =========================================================
    # SOFT RESET
    # =========================================================

    def soft_reset(self):

        if not self.ser:
            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Soft Reset",
            "Send GRBL SOFT RESET (Ctrl-X)?\n\n"
            "The controller will reset and the "
            "current motion/job will stop.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        try:

            self.ser.write(
                b"\x18"
            )

            self.log(
                "GRBL SOFT RESET SENT"
            )

        except Exception as e:

            self.log(
                f"RESET ERROR: {e}"
            )

        if self.sender:
            self.sender.stop()

    # =========================================================
    # CHECK GCODE
    # =========================================================

    def check_gcode(self):

        if not self.gcode_lines:

            self.log(
                "NO G-CODE LOADED"
            )

            return

        errors = []

        for i, line in enumerate(
            self.gcode_lines
        ):

            clean = re.sub(
                r"\([^)]*\)",
                "",
                line
            )

            clean = clean.split(
                ";"
            )[0].strip()

            if not clean:
                continue

            if any(
                char in clean
                for char in [
                    "{",
                    "}",
                    "[",
                    "]"
                ]
            ):

                errors.append(
                    (
                        i + 1,
                        clean
                    )
                )

        if errors:

            self.log(
                f"G-CODE CHECK: "
                f"{len(errors)} suspicious lines"
            )

            for number, line in errors[:10]:

                self.log(
                    f"LINE {number}: {line}"
                )

        else:

            self.log(
                "G-CODE CHECK PASSED"
            )

            QtWidgets.QMessageBox.information(
                self,
                "G-code Check",
                "Basic G-code validation passed."
            )

    # =========================================================
    # JOB COMPLETE
    # =========================================================

    def job_finished(self):

        self.progress_bar.setValue(
            100
        )

        self.progress_timer.stop()

        self.eta_label.setText(
            "ETA 00:00:00"
        )

        self.is_paused = False

        self.stop_btn.setEnabled(
            False
        )

        self.resume_btn.setEnabled(
            False
        )

        if self.ser:
            self.status_timer.start(
                100
            )

        self.update_button_state()

        self.log(
            "JOB COMPLETE"
        )

        try:

            QSound.play(
                "Assets/job_complete.wav"
            )

        except Exception:
            pass

    # =========================================================
    # JOB STOPPED
    # =========================================================

    def job_stopped(self):

        self.progress_timer.stop()

        self.stop_btn.setEnabled(
            False
        )

        self.resume_btn.setEnabled(
            False
        )

        self.is_paused = False

        if self.ser:
            self.status_timer.start(
                100
            )

        self.update_button_state()

        self.log(
            "JOB STOPPED"
        )

    # =========================================================
    # THREAD CLEANUP
    # =========================================================

    def thread_finished(self):

        if self.sender:

            self.sender.deleteLater()

            self.sender = None

        self.update_button_state()

    # =========================================================
    # ERROR
    # =========================================================

    def handle_sender_error(self, message):

        self.log(
            message
        )

        self.update_button_state()

    # =========================================================
    # PROGRESS
    # =========================================================

    def update_progress_info(self):

        if not self.job_start_time:
            return

        elapsed = int(
            time.time()
            -
            self.job_start_time
        )

        self.run_time_label.setText(
            f"RUN {self.format_time(elapsed)}"
        )

        progress = self.progress_bar.value()

        if progress > 1:

            total = (
                elapsed
                *
                100
                /
                progress
            )

            eta = max(
                0,
                int(
                    total
                    -
                    elapsed
                )
            )

            self.eta_label.setText(
                f"ETA {self.format_time(eta)}"
            )

        else:

            self.eta_label.setText(
                "ETA calculating..."
            )

    @staticmethod
    def format_time(seconds):

        h, remainder = divmod(
            int(seconds),
            3600
        )

        m, s = divmod(
            remainder,
            60
        )

        return (
            f"{h:02}:"
            f"{m:02}:"
            f"{s:02}"
        )

    # =========================================================
    # STATUS REQUEST
    # =========================================================

    def request_status(self):

        if not self.ser:
            return

        try:

            self.ser.write(
                b"?"
            )

        except Exception:
            pass

    # =========================================================
    # STATUS POLLING
    # =========================================================

    def poll_status(self):

        if not self.ser:
            return

        if not self.ser.is_open:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        try:

            self.ser.write(
                b"?"
            )

            while self.ser.in_waiting:

                line = (
                    self.ser.readline()
                    .decode(
                        errors="ignore"
                    )
                    .strip()
                )

                if line.startswith("<"):

                    self.parse_status(
                        line
                    )

                elif line:

                    self.log(
                        f"<< {line}"
                    )

        except serial.SerialException as e:

            self.log(
                f"STATUS ERROR: {e}"
            )

    # =========================================================
    # STATUS PARSER
    # =========================================================

    def parse_status(self, status):

        state = re.match(
            r"<([^|,]+)",
            status
        )

        if state:

            self.update_machine_state(
                state.group(1)
            )

        mpos = re.search(
            r"MPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        wpos = re.search(
            r"WPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        wco = re.search(
            r"WCO:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        if wco:

            self.last_wco = list(
                map(
                    float,
                    wco.groups()
                )
            )

        x = y = z = 0.0

        if wpos:

            x, y, z = map(
                float,
                wpos.groups()
            )

        elif mpos and self.last_wco:

            mx, my, mz = map(
                float,
                mpos.groups()
            )

            x = mx - self.last_wco[0]
            y = my - self.last_wco[1]
            z = mz - self.last_wco[2]

        elif mpos:

            x, y, z = map(
                float,
                mpos.groups()
            )

        self.update_tool_position(
            x,
            y,
            z
        )

        fs = re.search(
            r"FS:([0-9.]+),([0-9.]+)",
            status
        )

        if fs:

            self.feed_label.setText(
                f"F {float(fs.group(1)):.0f}"
            )

            self.speed_label.setText(
                f"S {float(fs.group(2)):.0f}"
            )

    # =========================================================
    # MACHINE STATE
    # =========================================================

    def update_machine_state(self, state):

        state = state.upper()

        self.state_label.setText(
            state
        )

        self.header_status.setText(
            f"● {state}"
        )

        if "ALARM" in state:

            self.header_status.setStyleSheet(
                "color:#ff4444;"
                "font-size:12pt;"
                "font-weight:bold;"
            )

        elif "RUN" in state:

            self.header_status.setStyleSheet(
                "color:#55dd55;"
                "font-size:12pt;"
                "font-weight:bold;"
            )

        elif "HOLD" in state:

            self.header_status.setStyleSheet(
                "color:#f0a500;"
                "font-size:12pt;"
                "font-weight:bold;"
            )

        else:

            self.header_status.setStyleSheet(
                "color:#f0a500;"
                "font-size:12pt;"
                "font-weight:bold;"
            )

    # =========================================================
    # TOOL POSITION
    # =========================================================

    def update_tool_position(self, x, y, z):

        self.dro_x_value.setText(
            f"{x:.3f}"
        )

        self.dro_y_value.setText(
            f"{y:.3f}"
        )

        self.dro_z_value.setText(
            f"{z:.3f}"
        )

        self.tool_3d.setData(
            pos=np.array(
                [[x, y, z]],
                dtype=float
            )
        )

    # =========================================================
    # JOG
    # =========================================================

    def jog(self, direction):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        distance = float(
            self.jog_distance_box.currentText()
        )

        speed = self.jog_speed_box.value()

        axis = direction[0]

        sign = (
            "+"
            if direction[1] == "+"
            else "-"
        )

        distance_text = f"{distance:g}"

        if sign == "-":

            distance_text = "-" + distance_text

        command = (
            f"$J=G91 {axis}"
            f"{distance_text} "
            f"F{speed}\n"
        )

        try:

            self.ser.write(
                command.encode()
            )

            self.log(
                f"JOG {direction}  "
                f"{distance:g} mm  "
                f"{speed} mm/min"
            )

        except Exception as e:

            self.log(
                f"JOG ERROR: {e}"
            )

    # =========================================================
    # ZERO AXIS
    # =========================================================

    def zero_axis(self, axis):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        try:

            command = (
                f"G10 L20 P1 {axis}0\n"
            )

            self.ser.write(
                command.encode()
            )

            self.log(
                f"{axis} WORK ZERO SET"
            )

            self.request_status()

        except Exception as e:

            self.log(
                f"ZERO ERROR: {e}"
            )

    # =========================================================
    # ZERO ALL
    # =========================================================

    def zero_all(self):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        try:

            self.ser.write(
                b"G10 L20 P1 X0 Y0 Z0\n"
            )

            self.log(
                "X/Y/Z WORK ZERO SET"
            )

            self.request_status()

        except Exception as e:

            self.log(
                f"ZERO ALL ERROR: {e}"
            )

    # =========================================================
    # GO TO ZERO
    # =========================================================

    def go_zero(self):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Go To Zero",
            "Move the machine to X0 Y0 Z0?\n\n"
            "Make sure the travel path is clear.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        self.send_command(
            "G90 G0 X0 Y0 Z0"
        )

    # =========================================================
    # HOME
    # =========================================================

    def home_machine(self):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Home Machine",
            "Send $H to GRBL?\n\n"
            "Make sure the machine is clear "
            "before homing.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer == QtWidgets.QMessageBox.Yes:

            self.send_command(
                "$H"
            )

    # =========================================================
    # SPINDLE CW
    # =========================================================

    def spindle_cw(self):

        rpm = self.rpm_box.value()

        self.send_command(
            f"M3 S{rpm}"
        )

    # =========================================================
    # SPINDLE CCW
    # =========================================================

    def spindle_ccw(self):

        rpm = self.rpm_box.value()

        self.send_command(
            f"M4 S{rpm}"
        )

    # =========================================================
    # FEED OVERRIDE
    # =========================================================

    def feed_override_change(self, amount):

        if not self.ser:
            return

        new_value = max(
            10,
            min(
                200,
                self.feed_override + amount
            )
        )

        while self.feed_override < new_value:

            try:

                self.ser.write(
                    b"\x91"
                )

            except Exception:
                break

            self.feed_override += 10

        while self.feed_override > new_value:

            try:

                self.ser.write(
                    b"\x90"
                )

            except Exception:
                break

            self.feed_override -= 10

        self.feed_override_label.setText(
            f"{self.feed_override}%"
        )

    def feed_override_set(self, value):

        if not self.ser:
            return

        self.feed_override = 100

        try:

            self.ser.write(
                b"\x92"
            )

        except Exception:
            pass

        self.feed_override_label.setText(
            "100%"
        )

    # =========================================================
    # SPINDLE OVERRIDE
    # =========================================================

    def spindle_override_change(self, amount):

        if not self.ser:
            return

        new_value = max(
            10,
            min(
                200,
                self.spindle_override + amount
            )
        )

        while self.spindle_override < new_value:

            try:

                self.ser.write(
                    b"\x9A"
                )

            except Exception:
                break

            self.spindle_override += 10

        while self.spindle_override > new_value:

            try:

                self.ser.write(
                    b"\x99"
                )

            except Exception:
                break

            self.spindle_override -= 10

        self.spindle_override_label.setText(
            f"{self.spindle_override}%"
        )

    def spindle_override_set(self, value):

        if not self.ser:
            return

        try:

            self.ser.write(
                b"\x9B"
            )

        except Exception:
            pass

        self.spindle_override = 100

        self.spindle_override_label.setText(
            "100%"
        )

    # =========================================================
    # MANUAL COMMAND
    # =========================================================

    def send_manual_command(self):

        if not self.ser:

            self.log(
                "NOT CONNECTED"
            )

            return

        command = (
            self.cmd_input.text()
            .strip()
        )

        if not command:
            return

        self.send_command(
            command
        )

        self.cmd_input.clear()

    # =========================================================
    # SEND COMMAND
    # =========================================================

    def send_command(self, command):

        if not self.ser:
            return

        try:

            self.ser.write(
                (
                    command
                    +
                    "\n"
                ).encode()
            )

            self.log(
                f">> {command}"
            )

        except Exception as e:

            self.log(
                f"COMMAND ERROR: {e}"
            )

    # =========================================================
    # GCODE HIGHLIGHT
    # =========================================================

    def highlight_gcode_line(self, line_number):

        self.gcode_editor.highlight_line(
            line_number
        )

        self.gcode_line_label.setText(
            f"LINE "
            f"{line_number + 1:,}"
            f" / "
            f"{len(self.gcode_lines):,}"
        )

    # =========================================================
    # 3D GCODE VISUALISER
    # =========================================================

    def plot_gcode(self):

        # -----------------------------------------------------
        # RESET
        # -----------------------------------------------------

        self.cut_points_3d = []
        self.rapid_points_3d = []

        # -----------------------------------------------------
        # MODAL STATE
        # -----------------------------------------------------

        x = 0.0
        y = 0.0
        z = 0.0

        absolute = True

        motion = None

        spindle_on = False
        spindle_power = 0.0

        # -----------------------------------------------------
        # HELPERS
        # -----------------------------------------------------

        def number(pattern, text):

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:
                try:
                    return float(match.group(1))
                except Exception:
                    return None

            return None

        def has_code(code, text):

            return re.search(
                rf"(?<![A-Z0-9]){code}(?![A-Z0-9])",
                text,
                re.IGNORECASE
            ) is not None

        def add_segment(target, start, end):

            start = np.asarray(
                start,
                dtype=float
            )

            end = np.asarray(
                end,
                dtype=float
            )

            if np.allclose(
                start,
                end
            ):
                return

            # IMPORTANT:
            # Each move is an independent pair.
            target.append(start)
            target.append(end)

        def add_arc(
            target,
            start,
            end,
            clockwise,
            i_value,
            j_value
        ):

            # -------------------------------------------------
            # If no I/J information exists, use a straight line
            # -------------------------------------------------

            if (
                i_value is None
                and
                j_value is None
            ):

                add_segment(
                    target,
                    start,
                    end
                )

                return

            i_value = (
                i_value
                if i_value is not None
                else 0.0
            )

            j_value = (
                j_value
                if j_value is not None
                else 0.0
            )

            # -------------------------------------------------
            # GRBL G2/G3 arcs use I/J as offsets from start
            # -------------------------------------------------

            cx = start[0] + i_value
            cy = start[1] + j_value

            radius = np.hypot(
                start[0] - cx,
                start[1] - cy
            )

            if radius <= 0.000001:

                add_segment(
                    target,
                    start,
                    end
                )

                return

            start_angle = np.arctan2(
                start[1] - cy,
                start[0] - cx
            )

            end_angle = np.arctan2(
                end[1] - cy,
                end[0] - cx
            )

            # -------------------------------------------------
            # Determine sweep direction
            # -------------------------------------------------

            if clockwise:

                while end_angle >= start_angle:

                    end_angle -= 2.0 * np.pi

            else:

                while end_angle <= start_angle:

                    end_angle += 2.0 * np.pi

            sweep = (
                end_angle
                -
                start_angle
            )

            # -------------------------------------------------
            # Number of interpolation points
            # -------------------------------------------------

            segments = max(
                12,
                int(
                    abs(sweep)
                    *
                    180.0
                    /
                    np.pi
                    /
                    4.0
                )
            )

            angles = np.linspace(
                start_angle,
                end_angle,
                segments + 1
            )

            points = []

            for angle in angles:

                px = (
                    cx
                    +
                    radius
                    *
                    np.cos(angle)
                )

                py = (
                    cy
                    +
                    radius
                    *
                    np.sin(angle)
                )

                # Linear Z interpolation through arc

                if abs(
                    end[2] - start[2]
                ) > 0.000001:

                    fraction = (
                        angle
                        -
                        start_angle
                    ) / sweep

                    pz = (
                        start[2]
                        +
                        (
                            end[2]
                            -
                            start[2]
                        )
                        *
                        fraction
                    )

                else:

                    pz = start[2]

                points.append(
                    [
                        px,
                        py,
                        pz
                    ]
                )

            # -------------------------------------------------
            # Add independent line segments
            # -------------------------------------------------

            for i in range(
                len(points) - 1
            ):

                add_segment(
                    target,
                    points[i],
                    points[i + 1]
                )

        # =====================================================
        # PARSE GCODE
        # =====================================================

        for raw_line in self.gcode_lines:

            # -------------------------------------------------
            # REMOVE PARENTHESIS COMMENTS
            # -------------------------------------------------

            line = re.sub(
                r"\([^)]*\)",
                "",
                raw_line
            )

            # -------------------------------------------------
            # REMOVE SEMICOLON COMMENTS
            # -------------------------------------------------

            line = line.split(
                ";",
                1
            )[0].strip()

            if not line:
                continue

            # -------------------------------------------------
            # REMOVE LINE NUMBER
            # -------------------------------------------------

            line = re.sub(
                r"^\s*N[-+]?\d+\s*",
                "",
                line,
                flags=re.IGNORECASE
            )

            if not line:
                continue

            upper = line.upper()

            # -------------------------------------------------
            # DISTANCE MODE
            # -------------------------------------------------

            if re.search(
                r"(?<![A-Z0-9])G90(?![A-Z0-9])",
                upper
            ):

                absolute = True

            if re.search(
                r"(?<![A-Z0-9])G91(?![A-Z0-9])",
                upper
            ):

                absolute = False

            # -------------------------------------------------
            # MOTION MODE
            # -------------------------------------------------

            # G-code words may be written with or without spaces, e.g.
            # G1 X10, G1X10, G01 X10 or G01X10.
            # The previous pattern required a non-letter after the G-code,
            # so normal forms such as G1X10 were not detected and the
            # previous G0 modal state remained active. That made the whole
            # toolpath get classified as RAPID.
            motion_match = re.search(
                r"(?<![A-Z0-9])G0*([0-3])(?=$|\s|[XYZIJKF])",
                upper
            )

            if motion_match:

                motion = "G" + motion_match.group(1)

            # -------------------------------------------------
            # SPINDLE COMMANDS
            # -------------------------------------------------

            if re.search(
                r"(?<![A-Z0-9])M0*3(?![A-Z0-9])",
                upper
            ):

                spindle_on = True

            if re.search(
                r"(?<![A-Z0-9])M0*4(?![A-Z0-9])",
                upper
            ):

                spindle_on = True

            if re.search(
                r"(?<![A-Z0-9])M0*5(?![A-Z0-9])",
                upper
            ):

                spindle_on = False

                # Do NOT reset S.
                # S is modal and may be restored later.

            # -------------------------------------------------
            # SPINDLE SPEED
            # -------------------------------------------------

            s_value = number(
                r"S\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if s_value is not None:

                spindle_power = s_value

                # If S > 0 appears with the line, regard the
                # spindle as active unless M5 is also present.

                if s_value > 0:

                    spindle_on = True

            # -------------------------------------------------
            # CURRENT POSITION
            # -------------------------------------------------

            start = np.array(
                [
                    x,
                    y,
                    z
                ],
                dtype=float
            )

            tx = x
            ty = y
            tz = z

            # -------------------------------------------------
            # X
            # -------------------------------------------------

            x_value = number(
                r"X\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if x_value is not None:

                if absolute:

                    tx = x_value

                else:

                    tx += x_value

            # -------------------------------------------------
            # Y
            # -------------------------------------------------

            y_value = number(
                r"Y\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if y_value is not None:

                if absolute:

                    ty = y_value

                else:

                    ty += y_value

            # -------------------------------------------------
            # Z
            # -------------------------------------------------

            z_value = number(
                r"Z\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if z_value is not None:

                if absolute:

                    tz = z_value

                else:

                    tz += z_value

            end = np.array(
                [
                    tx,
                    ty,
                    tz
                ],
                dtype=float
            )

            # -------------------------------------------------
            # WAS THERE ACTUAL MOTION?
            # -------------------------------------------------

            moved = not np.allclose(
                start,
                end,
                atol=0.000001
            )

            if moved:

                # -------------------------------------------------
                # RAPID
                # -------------------------------------------------

                if motion == "G0":

                    add_segment(
                        self.rapid_points_3d,
                        start,
                        end
                    )

                # -------------------------------------------------
                # CUTTING LINE
                #
                # For CNC:
                # G1 is considered a cutting/work move.
                #
                # This fixes the previous problem where G1
                # disappeared when there was no S on the same
                # line.
                # -------------------------------------------------

                elif motion == "G1":

                    add_segment(
                        self.cut_points_3d,
                        start,
                        end
                    )

                # -------------------------------------------------
                # CLOCKWISE ARC
                # -------------------------------------------------

                elif motion == "G2":

                    i_value = number(
                        r"I\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                        upper
                    )

                    j_value = number(
                        r"J\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                        upper
                    )

                    add_arc(
                        self.cut_points_3d,
                        start,
                        end,
                        True,
                        i_value,
                        j_value
                    )

                # -------------------------------------------------
                # COUNTER-CLOCKWISE ARC
                # -------------------------------------------------

                elif motion == "G3":

                    i_value = number(
                        r"I\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                        upper
                    )

                    j_value = number(
                        r"J\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                        upper
                    )

                    add_arc(
                        self.cut_points_3d,
                        start,
                        end,
                        False,
                        i_value,
                        j_value
                    )

                # -------------------------------------------------
                # UNKNOWN MOTION
                #
                # If coordinates move before a G0/G1 has appeared,
                # show them as rapid/travel rather than losing them.
                # -------------------------------------------------

                else:

                    add_segment(
                        self.rapid_points_3d,
                        start,
                        end
                    )

            # -------------------------------------------------
            # UPDATE MODAL POSITION
            # -------------------------------------------------

            x = tx
            y = ty
            z = tz

        # =====================================================
        # CONVERT TO NUMPY
        # =====================================================

        if self.cut_points_3d:

            self.cut_points_3d = np.asarray(
                self.cut_points_3d,
                dtype=float
            )

        else:

            self.cut_points_3d = np.empty(
                (0, 3),
                dtype=float
            )

        if self.rapid_points_3d:

            self.rapid_points_3d = np.asarray(
                self.rapid_points_3d,
                dtype=float
            )

        else:

            self.rapid_points_3d = np.empty(
                (0, 3),
                dtype=float
            )

        # =====================================================
        # UPDATE OPENGL CUT PATH
        # =====================================================

        if len(
            self.cut_points_3d
        ) > 0:

            self.cut_3d.setData(
                pos=self.cut_points_3d,
                color=(0.0, 1.0, 1.0, 1.0),
                width=2,
                antialias=True,
                mode="lines"
            )

        else:

            self.cut_3d.setData(
                pos=np.empty(
                    (0, 3),
                    dtype=float
                ),
                color=(0.0, 1.0, 1.0, 1.0),
                width=2,
                antialias=True,
                mode="lines"
            )

        # =====================================================
        # UPDATE OPENGL RAPID PATH
        # =====================================================

        if len(
            self.rapid_points_3d
        ) > 0:

            self.rapid_3d.setData(
                pos=self.rapid_points_3d,
                color=(1.0, 0.0, 0.0, 1.0),
                width=1,
                antialias=True,
                mode="lines"
            )

        else:

            self.rapid_3d.setData(
                pos=np.empty(
                    (0, 3),
                    dtype=float
                ),
                color=(1.0, 0.0, 0.0, 1.0),
                width=1,
                antialias=True,
                mode="lines"
            )

        # =====================================================
        # RESET TOOL TO PROGRAM START
        # =====================================================

        self.tool_3d.setData(
            pos=np.array(
                [[0.0, 0.0, 0.0]],
                dtype=float
            )
        )

        # =====================================================
        # FIT
        # =====================================================

        self.fit_visualiser()

    # =========================================================
    # FIT 3D VIEW
    # =========================================================

    def fit_visualiser(self):

        points = []

        if (
            isinstance(
                self.cut_points_3d,
                np.ndarray
            )
            and
            len(self.cut_points_3d)
        ):

            points.append(
                self.cut_points_3d
            )

        if (
            isinstance(
                self.rapid_points_3d,
                np.ndarray
            )
            and
            len(self.rapid_points_3d)
        ):

            points.append(
                self.rapid_points_3d
            )

        if not points:
            return

        all_points = np.vstack(
            points
        )

        # -----------------------------------------------------
        # REMOVE INVALID VALUES
        # -----------------------------------------------------

        all_points = all_points[
            np.all(
                np.isfinite(all_points),
                axis=1
            )
        ]

        if len(all_points) == 0:
            return

        minimum = np.min(
            all_points,
            axis=0
        )

        maximum = np.max(
            all_points,
            axis=0
        )

        centre = (
            minimum
            +
            maximum
        ) / 2.0

        size = np.max(
            maximum
            -
            minimum
        )

        if size <= 0:
            size = 100.0

        self.plot.opts["center"] = pg.Vector(
            float(centre[0]),
            float(centre[1]),
            float(centre[2])
        )

        self.plot.opts["distance"] = max(
            50.0,
            float(size * 1.6)
        )

        grid_size = max(
            200.0,
            float(size * 1.5)
        )

        grid_spacing = max(
            1.0,
            float(size / 20.0)
        )

        self.grid.setSize(
            grid_size,
            grid_size
        )

        self.grid.setSpacing(
            grid_spacing,
            grid_spacing
        )

        # -----------------------------------------------------
        # KEEP AXES VISIBLE
        # -----------------------------------------------------

        axis_length = max(
            100.0,
            float(size)
        )

        self.axis_x.setData(
            pos=np.array(
                [
                    [0, 0, 0],
                    [axis_length, 0, 0]
                ],
                dtype=float
            )
        )

        self.axis_y.setData(
            pos=np.array(
                [
                    [0, 0, 0],
                    [0, axis_length, 0]
                ],
                dtype=float
            )
        )

        self.axis_z.setData(
            pos=np.array(
                [
                    [0, 0, 0],
                    [0, 0, axis_length]
                ],
                dtype=float
            )
        )

        self.plot.update()

    # =========================================================
    # TOP VIEW
    # =========================================================

    def view_top(self):

        self.plot.setCameraPosition(
            elevation=90,
            azimuth=-90
        )

    # =========================================================
    # FRONT VIEW
    # =========================================================

    def view_front(self):

        self.plot.setCameraPosition(
            elevation=0,
            azimuth=-90
        )

    # =========================================================
    # RIGHT VIEW
    # =========================================================

    def view_right(self):

        self.plot.setCameraPosition(
            elevation=0,
            azimuth=0
        )

    # =========================================================
    # ISO VIEW
    # =========================================================

    def view_iso(self):

        self.plot.setCameraPosition(
            elevation=30,
            azimuth=-45
        )

    # =========================================================
    # CLEAR VISUALISER
    # =========================================================

    def clear_visualiser(self):

        self.cut_points_3d = np.empty(
            (0, 3),
            dtype=float
        )

        self.rapid_points_3d = np.empty(
            (0, 3),
            dtype=float
        )

        self.cut_3d.setData(
            pos=np.empty(
                (0, 3),
                dtype=float
            )
        )

        self.rapid_3d.setData(
            pos=np.empty(
                (0, 3),
                dtype=float
            )
        )

        self.tool_3d.setData(
            pos=np.array(
                [[0, 0, 0]],
                dtype=float
            )
        )

    # =========================================================
    # BUTTON STATE
    # =========================================================

    def update_button_state(self):

        connected = (
            self.ser is not None
            and
            self.ser.is_open
            if self.ser
            else False
        )

        running = (
            self.sender is not None
            and
            self.sender.isRunning()
        )

        for button in self.jog_buttons:

            button.setEnabled(
                connected
                and
                not running
            )

        for button in self.zero_buttons:

            button.setEnabled(
                connected
                and
                not running
            )

        self.spindle_cw_btn.setEnabled(
            connected
            and
            not running
        )

        self.spindle_ccw_btn.setEnabled(
            connected
            and
            not running
        )

        self.spindle_off_btn.setEnabled(
            connected
        )

        self.cmd_send_btn.setEnabled(
            connected
            and
            not running
        )

        self.play_btn.setEnabled(
            connected
            and
            bool(self.gcode_lines)
            and
            not running
        )

        self.pause_btn.setEnabled(
            running
            and
            not self.is_paused
        )

        self.resume_btn.setEnabled(
            running
            and
            self.is_paused
        )

        self.stop_btn.setEnabled(
            running
        )

        self.load_btn.setEnabled(
            not running
        )

        self.clear_btn.setEnabled(
            not running
        )

        self.home_btn.setEnabled(
            connected
            and
            not running
        )

        self.unlock_btn.setEnabled(
            connected
            and
            not running
        )

        self.reset_btn.setEnabled(
            connected
        )

        self.check_btn.setEnabled(
            bool(self.gcode_lines)
            and
            not running
        )

    # =========================================================
    # LOG
    # =========================================================

    def log(self, message):

        timestamp = time.strftime(
            "%H:%M:%S"
        )

        self.log_box.append(
            f"[{timestamp}] {message}"
        )

        self.log_box.ensureCursorVisible()

    # =========================================================
    # CLOSE
    # =========================================================

    def closeEvent(self, event):

        if (
            self.sender
            and
            self.sender.isRunning()
        ):

            answer = QtWidgets.QMessageBox.warning(
                self,
                "Job Running",
                "A CNC job is currently running.\n\n"
                "Stop the machine and close?",
                QtWidgets.QMessageBox.Yes |
                QtWidgets.QMessageBox.No
            )

            if answer != QtWidgets.QMessageBox.Yes:

                event.ignore()

                return

            try:

                self.ser.write(
                    b"!"
                )

                time.sleep(
                    0.05
                )

                self.ser.write(
                    b"M5\n"
                )

            except Exception:
                pass

            self.sender.stop()

            self.sender.wait(
                2000
            )

        if self.ser:

            try:

                self.ser.write(
                    b"M5\n"
                )

            except Exception:
                pass

            try:

                self.ser.close()

            except Exception:
                pass

        event.accept()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app = QtWidgets.QApplication(
        sys.argv
    )

    app.setApplicationName(
        APP_NAME
    )

    app.setApplicationVersion(
        APP_VERSION
    )

    app.setStyle(
        "Fusion"
    )

    window = CNCSender()

    window.show()

    sys.exit(
        app.exec_()
    )