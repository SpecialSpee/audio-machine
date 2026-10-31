import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLineEdit, QLabel, 
                             QComboBox, QTextEdit, QFileDialog, QTabWidget,
                             QGridLayout, QFrame, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

import soundfile as sf
from pydub import AudioSegment


# ═══════════════════════════════════════════════════════════════
# ПОТОК КОНВЕРТАЦИИ (чтобы GUI не зависал)
# ═══════════════════════════════════════════════════════════════
class ConvertThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, mode, input_dir, output_dir, setting):
        super().__init__()
        self.mode = mode
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.setting = setting

    def run(self):
        in_path = Path(self.input_dir)
        out_path = Path(self.output_dir) if self.output_dir else in_path
        out_path.mkdir(parents=True, exist_ok=True)

        if self.mode == 'flac2wav':
            files = [f for f in in_path.iterdir() if f.is_file() and f.suffix.lower() == '.flac']
            ext_out = '.wav'
            self.log_signal.emit(f"🔍 НАЙДЕНО FLAC: {len(files)}")
        else:
            files = [f for f in in_path.iterdir() if f.is_file() and f.suffix.lower() == '.wav']
            ext_out = '.mp3'
            self.log_signal.emit(f"🔍 НАЙДЕНО WAV: {len(files)}")

        if not files:
            self.log_signal.emit("❌ ФАЙЛЫ НЕ НАЙДЕНЫ")
            self.finished_signal.emit(False)
            return

        success_count = 0
        for f in files:
            out_file = out_path / f"{f.stem}{ext_out}"
            try:
                if self.mode == 'flac2wav':
                    data, sr = sf.read(f)
                    sf.write(out_file, data, sr, subtype=self.setting)
                else:
                    audio = AudioSegment.from_wav(f)
                    audio.export(out_file, format="mp3", bitrate=self.setting)
                
                self.log_signal.emit(f"✅ {f.name} → {out_file.name}")
                success_count += 1
            except Exception as e:
                self.log_signal.emit(f"⚠️  ОШИБКА [{f.name}]: {e}")

        self.log_signal.emit(f"\n🎉 ГОТОВО! Обработано: {success_count}/{len(files)}")
        self.finished_signal.emit(True)


# ═══════════════════════════════════════════════════════════════
# ГЛАВНОЕ ОКНО
# ═══════════════════════════════════════════════════════════════
class AudioMachineWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("АУДИО-МАШИНА // КОНВЕРТЕР v1.0")
        self.resize(1000, 720)
        self.thread = None
        self.setup_ui()
        self.apply_style()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── ШАПКА (черная плашка с красным акцентом) ──
        header = QFrame()
        header.setProperty("class", "header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)

        title = QLabel("█ АУДИО-МАШИНА")
        title.setProperty("class", "title")
        subtitle = QLabel("// КОНВЕРТЕР ФОРМАТОВ // 2026")
        subtitle.setProperty("class", "subtitle")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addStretch()
        main_layout.addWidget(header)

        # ── ОСНОВНАЯ ОБЛАСТЬ ──
        body = QWidget()
        body.setProperty("class", "body")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(20)

        # Левая колонка — вкладки с настройками
        left_col = QVBoxLayout()
        left_col.setSpacing(15)

        # Заголовок секции
        section_label = QLabel("▌ ЗАДАНИЕ")
        section_label.setProperty("class", "section-title")
        left_col.addWidget(section_label)

        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setProperty("class", "tabs")
        self.tabs.addTab(self.create_flac_tab(), "FLAC → WAV")
        self.tabs.addTab(self.create_mp3_tab(), "WAV → MP3")
        left_col.addWidget(self.tabs)

        # Кнопка ПУСК
        self.btn_start = QPushButton("▶  ПУСК  КОНВЕРТАЦИЮ")
        self.btn_start.setProperty("class", "btn-start")
        self.btn_start.clicked.connect(self.start_conversion)
        left_col.addWidget(self.btn_start)

        # Кнопка очистки лога
        self.btn_clear = QPushButton("✕  ОЧИСТИТЬ ЛОГ")
        self.btn_clear.setProperty("class", "btn-secondary")
        self.btn_clear.clicked.connect(self.clear_log)
        left_col.addWidget(self.btn_clear)

        left_col.addStretch()

        # Правая колонка — лог
        right_col = QVBoxLayout()
        right_col.setSpacing(15)

        log_label = QLabel("▌ ПРОТОКОЛ РАБОТЫ")
        log_label.setProperty("class", "section-title")
        right_col.addWidget(log_label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setProperty("class", "log")
        self.log.setPlaceholderText("// ОЖИДАНИЕ КОМАНДЫ...")
        right_col.addWidget(self.log)

        body_layout.addLayout(left_col, 4)
        body_layout.addLayout(right_col, 6)
        main_layout.addWidget(body, 1)

        # ── ПОДВАЛ ──
        footer = QFrame()
        footer.setProperty("class", "footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 8, 20, 8)
        status = QLabel("СТАТУС: // ГОТОВ К РАБОТЕ")
        status.setProperty("class", "status")
        self.status_label = status
        footer_layout.addWidget(status)
        footer_layout.addStretch()
        version = QLabel("CONSTRUCTIVIST EDITION")
        version.setProperty("class", "version")
        footer_layout.addWidget(version)
        main_layout.addWidget(footer)

    # ── Вкладка FLAC → WAV ──
    def create_flac_tab(self):
        tab = QWidget()
        grid = QGridLayout(tab)
        grid.setSpacing(12)
        grid.setContentsMargins(15, 15, 15, 15)

        grid.addWidget(QLabel("ВХОД (FLAC):"), 0, 0)
        self.flac_in = QLineEdit()
        self.flac_in.setPlaceholderText("путь к папке...")
        grid.addWidget(self.flac_in, 0, 1)
        btn1 = QPushButton("ОБЗОР")
        btn1.setProperty("class", "btn-browse")
        btn1.clicked.connect(lambda: self.browse_folder(self.flac_in))
        grid.addWidget(btn1, 0, 2)

        grid.addWidget(QLabel("ВЫХОД (WAV):"), 1, 0)
        self.flac_out = QLineEdit()
        self.flac_out.setPlaceholderText("оставь пустым = та же папка")
        grid.addWidget(self.flac_out, 1, 1)
        btn2 = QPushButton("ОБЗОР")
        btn2.setProperty("class", "btn-browse")
        btn2.clicked.connect(lambda: self.browse_folder(self.flac_out))
        grid.addWidget(btn2, 1, 2)

        grid.addWidget(QLabel("SUBTYPE:"), 2, 0)
        self.subtype_combo = QComboBox()
        self.subtype_combo.addItems([
            "PCM_16  // CD-качество, компакт",
            "PCM_24  // студия, максимум",
            "FLOAT   // для монтажа в DAW"
        ])
        grid.addWidget(self.subtype_combo, 2, 1, 1, 2)

        grid.setColumnStretch(1, 1)
        return tab

    # ── Вкладка WAV → MP3 ──
    def create_mp3_tab(self):
        tab = QWidget()
        grid = QGridLayout(tab)
        grid.setSpacing(12)
        grid.setContentsMargins(15, 15, 15, 15)

        grid.addWidget(QLabel("ВХОД (WAV):"), 0, 0)
        self.wav_in = QLineEdit()
        self.wav_in.setPlaceholderText("путь к папке...")
        grid.addWidget(self.wav_in, 0, 1)
        btn1 = QPushButton("ОБЗОР")
        btn1.setProperty("class", "btn-browse")
        btn1.clicked.connect(lambda: self.browse_folder(self.wav_in))
        grid.addWidget(btn1, 0, 2)

        grid.addWidget(QLabel("ВЫХОД (MP3):"), 1, 0)
        self.wav_out = QLineEdit()
        self.wav_out.setPlaceholderText("оставь пустым = та же папка")
        grid.addWidget(self.wav_out, 1, 1)
        btn2 = QPushButton("ОБЗОР")
        btn2.setProperty("class", "btn-browse")
        btn2.clicked.connect(lambda: self.browse_folder(self.wav_out))
        grid.addWidget(btn2, 1, 2)

        grid.addWidget(QLabel("BITRATE:"), 2, 0)
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems([
            "128k  // голос, подкасты",
            "192k  // стандарт",
            "256k  // высокое качество",
            "320k  // максимум для музыки"
        ])
        grid.addWidget(self.bitrate_combo, 2, 1, 1, 2)

        grid.setColumnStretch(1, 1)
        return tab

    # ── СТИЛИ В ДУХЕ КОНСТРУКТИВИЗМА ──
    def apply_style(self):
        style = """
        /* ═══ БАЗА ═══ */
        QMainWindow { background-color: #EDEDED; }
        QWidget { 
            font-family: 'Arial Black', 'Impact', 'Helvetica', sans-serif;
            color: #0A0A0A;
        }
        QLabel { font-size: 12px; font-weight: 900; letter-spacing: 1px; }

        /* ═══ ШАПКА ═══ */
        QFrame[class="header"] {
            background-color: #0A0A0A;
            border-bottom: 6px solid #D32F2F;
        }
        QLabel[class="title"] {
            color: #FFFFFF;
            font-size: 26px;
            font-weight: 900;
            letter-spacing: 3px;
        }
        QLabel[class="subtitle"] {
            color: #D32F2F;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 2px;
        }

        /* ═══ ТЕЛО ═══ */
        QWidget[class="body"] {
            background-color: #EDEDED;
        }

        /* ═══ ЗАГОЛОВКИ СЕКЦИЙ ═══ */
        QLabel[class="section-title"] {
            background-color: #0A0A0A;
            color: #FFFFFF;
            padding: 8px 14px;
            font-size: 14px;
            font-weight: 900;
            letter-spacing: 3px;
        }

        /* ═══ ВКЛАДКИ ═══ */
        QTabWidget::pane {
            border: 3px solid #0A0A0A;
            background-color: #FFFFFF;
        }
        QTabBar::tab {
            background-color: #FFFFFF;
            color: #0A0A0A;
            border: 3px solid #0A0A0A;
            border-bottom: none;
            padding: 10px 24px;
            font-size: 13px;
            font-weight: 900;
            letter-spacing: 2px;
            margin-right: 4px;
        }
        QTabBar::tab:selected {
            background-color: #D32F2F;
            color: #FFFFFF;
        }
        QTabBar::tab:hover:!selected {
            background-color: #0A0A0A;
            color: #FFFFFF;
        }

        /* ═══ ПОЛЯ ВВОДА ═══ */
        QLineEdit {
            border: 3px solid #0A0A0A;
            padding: 10px;
            background-color: #FFFFFF;
            font-size: 12px;
            font-weight: 700;
            font-family: 'Consolas', 'Courier New', monospace;
        }
        QLineEdit:focus {
            border-color: #D32F2F;
        }

        /* ═══ ВЫПАДАЮЩИЕ СПИСКИ ═══ */
        QComboBox {
            border: 3px solid #0A0A0A;
            padding: 8px 12px;
            background-color: #FFFFFF;
            font-size: 12px;
            font-weight: 900;
            font-family: 'Consolas', monospace;
        }
        QComboBox::drop-down {
            border-left: 3px solid #0A0A0A;
            background-color: #D32F2F;
            width: 30px;
        }
        QComboBox QAbstractItemView {
            border: 3px solid #0A0A0A;
            background-color: #FFFFFF;
            selection-background-color: #D32F2F;
            selection-color: #FFFFFF;
            font-weight: 700;
        }

        /* ═══ КНОПКИ ОБЗОРА ═══ */
        QPushButton[class="btn-browse"] {
            background-color: #FFFFFF;
            color: #0A0A0A;
            border: 3px solid #0A0A0A;
            padding: 8px 16px;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 2px;
        }
        QPushButton[class="btn-browse"]:hover {
            background-color: #0A0A0A;
            color: #FFFFFF;
        }

        /* ═══ ГЛАВНАЯ КНОПКА ПУСК ═══ */
        QPushButton[class="btn-start"] {
            background-color: #D32F2F;
            color: #FFFFFF;
            border: 4px solid #0A0A0A;
            padding: 20px;
            font-size: 18px;
            font-weight: 900;
            letter-spacing: 4px;
            min-height: 40px;
        }
        QPushButton[class="btn-start"]:hover {
            background-color: #B71C1C;
        }
        QPushButton[class="btn-start"]:pressed {
            background-color: #0A0A0A;
            color: #D32F2F;
        }
        QPushButton[class="btn-start"]:disabled {
            background-color: #888888;
            color: #CCCCCC;
        }

        /* ═══ ВТОРИЧНАЯ КНОПКА ═══ */
        QPushButton[class="btn-secondary"] {
            background-color: #FFFFFF;
            color: #0A0A0A;
            border: 3px solid #0A0A0A;
            padding: 12px;
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 2px;
        }
        QPushButton[class="btn-secondary"]:hover {
            background-color: #0A0A0A;
            color: #FFFFFF;
        }

        /* ═══ ЛОГ (телетайп) ═══ */
        QTextEdit[class="log"] {
            background-color: #0A0A0A;
            color: #E0E0E0;
            border: 3px solid #0A0A0A;
            padding: 15px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            font-weight: 700;
            selection-background-color: #D32F2F;
            selection-color: #FFFFFF;
        }

        /* ═══ ПОДВАЛ ═══ */
        QFrame[class="footer"] {
            background-color: #0A0A0A;
            border-top: 3px solid #D32F2F;
        }
        QLabel[class="status"] {
            color: #D32F2F;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 2px;
        }
        QLabel[class="version"] {
            color: #666666;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
        }
        """
        self.setStyleSheet(style)

    # ── ЛОГИКА ──
    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "ВЫБОР ПАПКИ")
        if folder:
            line_edit.setText(folder)

    def clear_log(self):
        self.log.clear()

    def append_log(self, text):
        self.log.append(text)
        # Прокрутка вниз
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_conversion(self):
        idx = self.tabs.currentIndex()

        if idx == 0:  # FLAC → WAV
            in_path = self.flac_in.text().strip()
            out_path = self.flac_out.text().strip()
            setting = self.subtype_combo.currentText().split()[0]  # PCM_16 / PCM_24 / FLOAT
            mode = 'flac2wav'
        else:  # WAV → MP3
            in_path = self.wav_in.text().strip()
            out_path = self.wav_out.text().strip()
            setting = self.bitrate_combo.currentText().split()[0]  # 128k / 192k / ...
            mode = 'wav2mp3'

        if not in_path or not Path(in_path).exists():
            self.append_log("❌ ОШИБКА: укажи корректную входную папку!")
            return

        self.append_log(f"\n{'═'*50}")
        self.append_log(f"▶ СТАРТ: {mode.upper()}")
        self.append_log(f"  ВХОД:  {in_path}")
        self.append_log(f"  ВЫХОД: {out_path or '(та же папка)'}")
        self.append_log(f"  ПАРАМ: {setting}")
        self.append_log(f"{'═'*50}")

        self.btn_start.setEnabled(False)
        self.btn_start.setText("⏳  РАБОТАЮ...")
        self.status_label.setText("СТАТУС: // В ПРОЦЕССЕ...")

        self.thread = ConvertThread(mode, in_path, out_path, setting)
        self.thread.log_signal.connect(self.append_log)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def on_finished(self, success):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("▶  ПУСК  КОНВЕРТАЦИЮ")
        self.status_label.setText("СТАТУС: // ГОТОВ К РАБОТЕ")


# ═══════════════════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Попытка установить крупный рубленый шрифт системы
    font = QFont("Arial Black", 10)
    font.setBold(True)
    app.setFont(font)

    window = AudioMachineWindow()
    window.show()
    sys.exit(app.exec())