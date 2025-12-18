import sys
import os
import shutil
import hashlib
import tarfile
import zipfile
import gzip
import bz2
import lzma
import subprocess

try:
    import pyzipper
    HAS_PYZIPPER = True
except ImportError:
    HAS_PYZIPPER = False

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTabWidget, 
                             QFileDialog, QComboBox, QCheckBox, QLineEdit, 
                             QListWidget, QMessageBox, QHeaderView,
                             QTableWidget, QTableWidgetItem, QAbstractItemView, 
                             QGroupBox, QStyle, QListWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont

# --- THEME: WARM MODERN (BROWN & ORANGE) ---
COLORS = {
    "bg": "#FFF8F0",          
    "text": "#4E342E",        
    "accent": "#E65100",      
    "accent_hover": "#FF6D00",
    "secondary_bg": "#FFFFFF",
    "border": "#D7CCC8",
    "highlight": "#FFCCBC",   
    "danger": "#D32F2F"       
}

STYLESHEET = f"""
    /* --- GLOBAL WINDOW SETTINGS --- */
    /* Force background on Main Window, Dialogs, and Message Boxes */
    QMainWindow, QDialog, QMessageBox {{ 
        background-color: {COLORS["bg"]}; 
        color: {COLORS["text"]};
    }}

    /* Force generic text color on all labels and checkboxes */
    QLabel, QCheckBox, QRadioButton {{ 
        color: {COLORS["text"]}; 
        background-color: transparent;
    }}

    /* --- MESSAGE BOX SPECIFICS --- */
    QMessageBox {{
        background-color: {COLORS["bg"]};
    }}
    QMessageBox QLabel {{
        color: {COLORS["text"]}; 
    }}
    
    /* --- BUTTONS --- */
    QPushButton {{
        background-color: {COLORS["accent"]}; 
        color: white; 
        border-radius: 8px; 
        padding: 10px 20px; 
        font-weight: 600;
        font-size: 13px;
        border: none;
    }}
    QPushButton:hover {{ 
        background-color: {COLORS["accent_hover"]}; 
        margin-top: -1px; 
    }}
    QPushButton:pressed {{ margin-top: 1px; }}
    QPushButton:disabled {{ background-color: {COLORS['border']}; color: #8D6E63; }}
    QPushButton#danger {{ background-color: {COLORS['danger']}; }}
    
    /* --- INPUTS --- */
    QLineEdit, QComboBox {{
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        background-color: white;
        color: {COLORS["text"]};
        font-size: 13px;
        selection-background-color: {COLORS["accent"]};
        selection-color: white;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 2px solid {COLORS["accent"]}; 
    }}
    
    /* --- TABS --- */
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{
        background: {COLORS["border"]};
        color: {COLORS["text"]};
        padding: 8px 24px;
        margin-right: 8px;
        border-radius: 16px; 
        font-weight: bold;
    }}
    QTabBar::tab:selected {{ 
        background: {COLORS["accent"]}; 
        color: white; 
    }}
    
    /* --- LISTS & TABLES --- */
    QListWidget, QTableWidget {{ 
        border: 1px solid {COLORS['border']}; 
        border-radius: 8px;
        background-color: white;
        color: {COLORS["text"]};
        padding: 5px;
        outline: 0; /* Removes dotted line on selection */
    }}
    QHeaderView::section {{ 
        background-color: {COLORS["bg"]}; 
        padding: 8px; 
        border: none; 
        font-weight: bold;
        color: {COLORS["text"]}; 
    }}
    /* Force item text color to ensure visibility */
    QTableWidget::item, QListWidget::item {{
        color: {COLORS["text"]};
    }}
    QTableWidget::item:selected, QListWidget::item:selected {{
        background-color: {COLORS["highlight"]};
        color: {COLORS["text"]}; /* Keep text dark on highlight */
        border-radius: 4px;
    }}

    /* --- GROUP BOX --- */
    QGroupBox {{ 
        border: 1px solid {COLORS["border"]}; 
        border-radius: 8px; 
        margin-top: 24px; 
        font-weight: bold;
        color: {COLORS["accent"]};
        background-color: {COLORS["bg"]};
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
"""

FORMAT_CONFIG = {
    "Tar":   {"ext": ".tar", "type": "archive", "multi": True},
    "Zip":   {"ext": ".zip", "type": "compressed_archive", "multi": True},
    "Gzip":  {"ext": ".gz",  "type": "compress_only", "multi": False},
    "Bzip2": {"ext": ".bz2", "type": "compress_only", "multi": False},
    "Xz":    {"ext": ".xz",  "type": "compress_only", "multi": False},
    "7z":    {"ext": ".7z",  "type": "compressed_archive", "multi": True},
    "Rar":   {"ext": ".rar", "type": "compressed_archive", "multi": True},
}

# --- CUSTOM WIDGETS ---

class DragDropListWidget(QListWidget): # for the create archive tabb
    """A ListWidget that accepts file drags and supports deletion."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) # this allows multi-select or multi-deletion ng files

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            self.add_file_item(f)
            
    def add_file_item(self, path):

        items = [self.item(i).text() for i in range(self.count())]
        if path not in items:
            item = QListWidgetItem(path)

            icon_provider = QApplication.style()
            if os.path.isdir(path):
                icon = icon_provider.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            else:
                icon = icon_provider.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
            item.setIcon(icon)
            self.addItem(item)

    # --- handle Delete Key ---
    # selecting a file and pressing delete will remove it from the list
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.remove_selected()
        else:
            super().keyPressEvent(event)

    # --- helper to remove items ---
    def remove_selected(self):
        for item in self.selectedItems():
            self.takeItem(self.row(item))

# --- WORKERS ---

class ChecksumWorker(QThread):
    result = pyqtSignal(str)
    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
    def run(self):
        try:
            sha256_hash = hashlib.sha256()
            with open(self.filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            self.result.emit(f"SHA-256: {sha256_hash.hexdigest()}")
        except Exception as e:
            self.result.emit(f"Error: {str(e)}")

# --- MAIN APP ---

class IArchiveApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iArchive")
        self.resize(950, 750)
        self.setStyleSheet(STYLESHEET)
        
        self.worker = None
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # --- TABS ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_archive_tab(), "Create Archive")
        self.tabs.addTab(self.create_extract_tab(), "Extract / Unzip")
        self.tabs.addTab(self.create_manage_tab(), "Manage Files")
        layout.addWidget(self.tabs)
        
        # --- STATUS BAR ---
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #777; font-size: 11px;")
        self.statusBar().addWidget(self.status_label)

    # ---------------- TAB 1: CREATE ----------------
    def create_archive_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)
        layout.setContentsMargins(10, 20, 10, 10)

        # 1. input Selection
        src_group = QGroupBox("1. Drag Files Here")
        src_layout = QVBoxLayout()
        
        self.file_list = DragDropListWidget()
        self.file_list.setFixedHeight(120)
        self.file_list.setToolTip("Drag and drop files from Finder here")
        
        btn_row = QHBoxLayout()
        
        # 1. browse btn
        self.btn_add_files = QPushButton("Browse Files")
        self.btn_add_files.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.btn_add_files.clicked.connect(self.add_files_action)
        
        # 2. remove selected btn
        self.btn_remove_file = QPushButton("Remove Selected")

        self.btn_remove_file.setStyleSheet(f"background-color: {COLORS['border']}; color: {COLORS['text']};")
        self.btn_remove_file.clicked.connect(self.file_list.remove_selected)
        
        # 3. clear button
        self.btn_clear_files = QPushButton("Clear All")
        self.btn_clear_files.setStyleSheet(f"background-color: {COLORS['border']}; color: {COLORS['text']};")
        self.btn_clear_files.clicked.connect(self.file_list.clear)
        
        btn_row.addWidget(self.btn_add_files)
        btn_row.addWidget(self.btn_remove_file)
        btn_row.addWidget(self.btn_clear_files)
        btn_row.addStretch()
        
        src_layout.addWidget(self.file_list)
        src_layout.addLayout(btn_row) 
        src_group.setLayout(src_layout)
        
        # 2. settings
        settings_group = QGroupBox("2. Preferences")
        set_layout = QVBoxLayout()
        set_layout.setSpacing(10)
        
        # grid for inputs
        grid_row = QHBoxLayout()
        
        # format
        fmt_layout = QVBoxLayout()
        fmt_layout.addWidget(QLabel("Format:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(FORMAT_CONFIG.keys())
        self.combo_format.currentTextChanged.connect(self.on_format_changed)
        fmt_layout.addWidget(self.combo_format)
        grid_row.addLayout(fmt_layout)
        
        # password
        pwd_layout = QVBoxLayout()
        pwd_layout.addWidget(QLabel("Password (Zip only):"))
        self.line_password = QLineEdit()
        self.line_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_password.setPlaceholderText("Optional")
        pwd_layout.addWidget(self.line_password)
        grid_row.addLayout(pwd_layout)
        
        # exclusion
        exc_layout = QVBoxLayout()
        exc_layout.addWidget(QLabel("Exclude Extension:"))
        self.line_exclude = QLineEdit()
        self.line_exclude.setPlaceholderText("e.g. .tmp")
        exc_layout.addWidget(self.line_exclude)
        grid_row.addLayout(exc_layout)
        
        set_layout.addLayout(grid_row)
        
        # checkbox
        self.check_recursive = QCheckBox("Recursively archive sub-folders")
        self.check_recursive.setChecked(True)
        set_layout.addWidget(self.check_recursive)
        
        settings_group.setLayout(set_layout)

        # 3. output
        act_layout = QHBoxLayout()
        self.lbl_dest_path = QLabel("Output: (None selected)")
        self.lbl_dest_path.setStyleSheet("color: #666; font-style: italic;")
        
        btn_dest = QPushButton("Set Destination")
        btn_dest.clicked.connect(self.set_destination_action)
        
        self.btn_process = QPushButton("Create Archive")
        self.btn_process.setMinimumHeight(45) 
        self.btn_process.clicked.connect(self.process_archive_action)
        
        act_layout.addWidget(btn_dest)
        act_layout.addWidget(self.lbl_dest_path)
        act_layout.addStretch()
        act_layout.addWidget(self.btn_process)

        layout.addWidget(src_group)
        layout.addWidget(settings_group)
        layout.addLayout(act_layout)
        layout.addStretch()
        
        self.destination_path = ""
        return tab

    # ---------------- TAB 2: EXTRACT ----------------
    def create_extract_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(20)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(15)

        # input
        form_layout.addWidget(QLabel("Archive Source:"))
        inp_row = QHBoxLayout()
        self.line_extract_src = QLineEdit()
        self.line_extract_src.setPlaceholderText("Select .zip, .tar, .gz...")
        btn_browse_ext = QPushButton("Browse")
        btn_browse_ext.clicked.connect(self.browse_extract_source)
        inp_row.addWidget(self.line_extract_src)
        inp_row.addWidget(btn_browse_ext)
        form_layout.addLayout(inp_row)

        # dest
        form_layout.addWidget(QLabel("Extract To:"))
        out_row = QHBoxLayout()
        self.line_extract_dest = QLineEdit()
        self.line_extract_dest.setPlaceholderText("Select output folder")
        btn_browse_dest = QPushButton("Browse")
        btn_browse_dest.clicked.connect(self.browse_extract_dest)
        out_row.addWidget(self.line_extract_dest)
        out_row.addWidget(btn_browse_dest)
        form_layout.addLayout(out_row)
        
        # options
        form_layout.addWidget(QLabel("Exclude Files (comma separated):"))
        self.line_extract_exclude = QLineEdit()
        self.line_extract_exclude.setPlaceholderText("e.g. .DS_Store, .tmp")
        form_layout.addWidget(self.line_extract_exclude)

        layout.addWidget(form_container)

        self.btn_extract = QPushButton("Start Extraction")
        self.btn_extract.setMinimumHeight(45)
        self.btn_extract.clicked.connect(self.run_extraction)
        layout.addWidget(self.btn_extract)
        layout.addStretch()
        return tab

    # ---------------- TAB 3: MANAGE ----------------
    def create_manage_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 20, 10, 10)

        top_layout = QHBoxLayout()
        self.line_manage_path = QLineEdit()
        self.line_manage_path.setReadOnly(True)
        self.line_manage_path.setPlaceholderText("No archive loaded")
        btn_load = QPushButton("Load Archive")
        btn_load.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        btn_load.clicked.connect(self.load_archive_for_management)
        top_layout.addWidget(self.line_manage_path)
        top_layout.addWidget(btn_load)
        layout.addLayout(top_layout)

        self.table_files = QTableWidget()
        self.table_files.setColumnCount(3)
        self.table_files.setHorizontalHeaderLabels(["Filename", "Size", "Type"])
        self.table_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_files.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_files.setAlternatingRowColors(True)
        self.table_files.verticalHeader().setVisible(False)
        self.table_files.setShowGrid(False) 
        layout.addWidget(self.table_files)

        self.lbl_checksum = QLabel("Checksum: N/A")
        self.lbl_checksum.setStyleSheet("font-family: monospace; background: #EEE; padding: 5px; border-radius: 4px;")
        self.lbl_checksum.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.lbl_checksum)

        btn_layout = QHBoxLayout()
        self.btn_append = QPushButton("Append File")
        self.btn_append.clicked.connect(self.append_to_archive)
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.clicked.connect(self.delete_from_archive)
        
        btn_layout.addWidget(self.btn_append)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)
        return tab

    # --- LOGIC: CREATE ---
    def on_format_changed(self, text):
        cfg = FORMAT_CONFIG[text]
        if not cfg["multi"] and self.file_list.count() > 1:
            QMessageBox.warning(self, "Restriction", f"{text} only supports single file compression.")
            self.file_list.clear()

    def add_files_action(self):
        fmt = self.combo_format.currentText()
        allow_multi = FORMAT_CONFIG[fmt]["multi"]
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files")
        if files:
            if not allow_multi and (self.file_list.count() > 0 or len(files) > 1):
                QMessageBox.critical(self, "Error", f"{fmt} allows only ONE input file.")
                return
            for f in files:
                self.file_list.add_file_item(f)

    def set_destination_action(self):
        fmt = self.combo_format.currentText()
        ext = FORMAT_CONFIG[fmt]["ext"]
        path, _ = QFileDialog.getSaveFileName(self, "Save Archive", f"archive{ext}", f"*{ext}")
        if path:
            self.destination_path = path
            self.lbl_dest_path.setText(os.path.basename(path))

    def process_archive_action(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Error", "Please drag files into the list or click Add Files.")
            return
        if not self.destination_path:
            QMessageBox.warning(self, "Error", "Please set a destination path.")
            return
            
        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        fmt = self.combo_format.currentText()
        pwd = self.line_password.text()
        recursive = self.check_recursive.isChecked()
        exclude_ext = self.line_exclude.text().strip()
        
        self.status_label.setText("Processing...")
        QApplication.processEvents()
        
        try:
            if fmt == "Zip":
                self.create_zip(files, self.destination_path, pwd, recursive, exclude_ext)
            elif fmt == "Tar":
                self.create_tar(files, self.destination_path, "w", recursive, exclude_ext)
            elif fmt == "Gzip":
                self.create_single_compress(files[0], self.destination_path, gzip.open)
            elif fmt == "Bzip2":
                self.create_single_compress(files[0], self.destination_path, bz2.open)
            elif fmt == "Xz":
                self.create_single_compress(files[0], self.destination_path, lzma.open)
            else:
                QMessageBox.information(self, "Info", f"{fmt} creation requires external binaries.")
                self.status_label.setText("Ready")
                return

            QMessageBox.information(self, "Success", "Archive created successfully.")
            self.file_list.clear()
            self.lbl_dest_path.setText("Output: (None selected)")
            self.destination_path = ""
            self.line_password.clear()
            self.status_label.setText("Ready")
            
        except Exception as e:
            self.status_label.setText("Error")
            QMessageBox.critical(self, "Error", str(e))

    def _should_exclude(self, filename, exclude_ext):
        if not exclude_ext: return False
        return filename.endswith(exclude_ext)

    def create_zip(self, files, dest, pwd, recursive, exclude):
        # STRATEGY 1: use pyzipper
        if HAS_PYZIPPER and pwd:
            try:
                with pyzipper.AESZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
                    zf.setpassword(pwd.encode('utf-8'))
                    self._write_to_zip(zf, files, recursive, exclude)
                return
            except Exception as e:
                raise Exception(f"pyzipper error: {str(e)}")

        # STRATEGY 2: fallbak to System Command 
        if pwd:
            try:
                # check if zip is installed
                subprocess.run(["zip", "-h"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                
                # construct command
                # -P: password
                # -r: recursive (essential for folders)
                cmd = ["zip", "-P", pwd, "-r", dest] + files
                
                if not recursive:
                    cmd = ["zip", "-P", pwd, "-j", dest] + files

                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return 
            except FileNotFoundError:
                raise Exception("System 'zip' command not found. Please install 'pyzipper' via pip for password support.")
            except subprocess.CalledProcessError as e:
                raise Exception(f"System zip command failed. Ensure you have permissions.")

        # STRATEGY 3: standard Python Zipfile
        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zf:
            self._write_to_zip(zf, files, recursive, exclude)

    def _write_to_zip(self, zf, files, recursive, exclude):
        """Helper to write files to a zip object (works for both zipfile and pyzipper)"""
        for f in files:
            if os.path.isfile(f):
                if not self._should_exclude(f, exclude):
                    zf.write(f, os.path.basename(f))
            elif os.path.isdir(f):
                if recursive:
                    for root, dirs, filenames in os.walk(f):
                        for filename in filenames:
                            if not self._should_exclude(filename, exclude):
                                filepath = os.path.join(root, filename)
                                # create relative path inside archive
                                arcname = os.path.relpath(filepath, os.path.dirname(f))
                                zf.write(filepath, arcname)
                else:
                    # if hindi recursive, just add the folder entry empty
                    zf.write(f, os.path.basename(f))

    def create_tar(self, files, dest, mode, recursive, exclude):
        with tarfile.open(dest, mode) as tf:
            for f in files:
                if self._should_exclude(f, exclude): continue
                def tar_filter(tarinfo):
                    if not recursive and tarinfo.isdir() and tarinfo.name != os.path.basename(f):
                        return None 
                    if self._should_exclude(tarinfo.name, exclude):
                        return None
                    return tarinfo
                tf.add(f, arcname=os.path.basename(f), filter=tar_filter)

    def create_single_compress(self, input_file, dest, open_func):
        with open(input_file, 'rb') as f_in:
            with open_func(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    # --- LOGIC: EXTRACT ---
    def browse_extract_source(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Archive")
        if f: self.line_extract_src.setText(f)

    def browse_extract_dest(self):
        d = QFileDialog.getExistingDirectory(self, "Select Destination")
        if d: self.line_extract_dest.setText(d)

    def run_extraction(self):
        src = self.line_extract_src.text()
        dest = self.line_extract_dest.text()
        exclude = self.line_extract_exclude.text().strip()

        if not os.path.exists(src) or not dest:
            QMessageBox.warning(self, "Missing Info", "Please select source file and destination folder.")
            return
        
        try:
            if src.endswith('.zip'):
                try:
                    with zipfile.ZipFile(src, 'r') as zf:
                        members = [m for m in zf.namelist() if not self._should_exclude(m, exclude)]
                        zf.extractall(dest, members=members)
                except RuntimeError as e:
                    if "encrypted" in str(e) or "Bad password" in str(e):
                         QMessageBox.warning(self, "Encrypted Zip", "This file is encrypted. Please use macOS Finder to extract it.")
                    else:
                        raise e
            
            elif src.endswith('.tar'):
                with tarfile.open(src, 'r:') as tf:
                    members = [m for m in tf.getmembers() if not self._should_exclude(m.name, exclude)]
                    tf.extractall(dest, members=members)

            elif src.endswith(('.tar.gz', '.tgz')):
                with tarfile.open(src, 'r:gz') as tf:
                    members = [m for m in tf.getmembers() if not self._should_exclude(m.name, exclude)]
                    tf.extractall(dest, members=members)
            
            elif src.endswith('.gz'):
                out_name = os.path.join(dest, os.path.basename(src).replace('.gz', ''))
                with gzip.open(src, 'rb') as f_in, open(out_name, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            QMessageBox.information(self, "Success", "Extraction complete.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # --- LOGIC: MANAGE ---
    def load_archive_for_management(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open Archive")
        if not f: return
        
        if self.worker is not None and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        self.line_manage_path.clear()
        self.table_files.setRowCount(0)
        self.lbl_checksum.setText("Checksum: Calculating...")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setText("Delete Selected")

        self.line_manage_path.setText(f)
        
        self.worker = ChecksumWorker(f)
        self.worker.result.connect(self.lbl_checksum.setText)
        self.worker.start()

        is_pure_archive = f.endswith('.tar')
        if is_pure_archive:
            self.btn_delete.setEnabled(True)
            self.btn_delete.setText("Delete Selected")
        else:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setText("Delete Disabled (Compressed)")

        try:
            if zipfile.is_zipfile(f):
                with zipfile.ZipFile(f, 'r') as zf:
                    for info in zf.infolist():
                        self._add_table_row(info.filename, info.file_size, "Zip Entry")
            elif tarfile.is_tarfile(f):
                mode = 'r:' if f.endswith('.tar') else 'r:gz'
                with tarfile.open(f, mode) as tf:
                    for member in tf.getmembers():
                        self._add_table_row(member.name, member.size, "Tar Entry")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read archive: {e}")

    def _add_table_row(self, name, size, ftype):
        row = self.table_files.rowCount()
        self.table_files.insertRow(row)
        self.table_files.setItem(row, 0, QTableWidgetItem(name))
        self.table_files.setItem(row, 1, QTableWidgetItem(f"{size:,} bytes"))
        self.table_files.setItem(row, 2, QTableWidgetItem(ftype))

    def append_to_archive(self):
        arc_path = self.line_manage_path.text()
        if not arc_path: return
        f_to_add, _ = QFileDialog.getOpenFileName(self, "Select File to Append")
        if not f_to_add: return

        try:
            if arc_path.endswith('.tar'):
                with tarfile.open(arc_path, 'a') as tf:
                    tf.add(f_to_add, arcname=os.path.basename(f_to_add))
            elif arc_path.endswith('.zip'):
                with zipfile.ZipFile(arc_path, 'a') as zf:
                    zf.write(f_to_add, os.path.basename(f_to_add))
            else:
                QMessageBox.warning(self, "Error", "Appending is only supported for .tar and .zip.")
                return
            QMessageBox.information(self, "Success", "File Appended.")
            self.load_archive_for_management()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_from_archive(self):
        arc_path = self.line_manage_path.text()
        row = self.table_files.currentRow()
        if row < 0: return
        filename_to_del = self.table_files.item(row, 0).text()
        
        reply = QMessageBox.question(self, "Confirm", f"Delete {filename_to_del}? This will repack the archive.", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                temp_path = arc_path + ".tmp"
                with tarfile.open(arc_path, 'r:') as tf_in:
                    with tarfile.open(temp_path, 'w') as tf_out:
                        for member in tf_in.getmembers():
                            if member.name != filename_to_del:
                                tf_out.addfile(member, tf_in.extractfile(member))
                shutil.move(temp_path, arc_path)
                QMessageBox.information(self, "Success", "File Deleted.")
                self.load_archive_for_management()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to repack: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = IArchiveApp()
    window.show()
    sys.exit(app.exec())