import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QStackedWidget, QListWidget, QListWidgetItem, QMenuBar, QAction, QStatusBar, QMessageBox, QToolBar,
    QListView, QAbstractItemView, QLineEdit, QButtonGroup, QRadioButton, QComboBox, QProgressDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import traceback
from pydfpro import handle_merge, handle_split, handle_reorder, handle_delete, handle_rotate, handle_extract_text, handle_extract_images, handle_pdf_to_image, handle_images_to_pdf, handle_add_watermark, handle_add_page_numbers, handle_encrypt, handle_decrypt, handle_compress

APP_NAME = "PyDF Pro GUI"
RECENT_FILES_PATH = os.path.expanduser("~/.pydfpro_recent_files.txt")

class FileManagement:
    def __init__(self):
        self.recent_files = self.load_recent_files()

    def load_recent_files(self):
        if os.path.exists(RECENT_FILES_PATH):
            with open(RECENT_FILES_PATH, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def add_recent_file(self, path):
        if path and path not in self.recent_files:
            self.recent_files.insert(0, path)
            self.recent_files = self.recent_files[:10]  # Keep only 10 recent files
            with open(RECENT_FILES_PATH, "w", encoding="utf-8") as f:
                for p in self.recent_files:
                    f.write(p + "\n")

class FeaturePanel(QWidget):
    def __init__(self, feature_name):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel(f"{feature_name} feature coming soon!")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)

class MergePDFsPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.selected_files = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # File selection
        file_select_layout = QHBoxLayout()
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        file_select_layout.addWidget(self.file_list)
        btns_layout = QVBoxLayout()
        add_btn = QPushButton("Add PDFs...")
        add_btn.clicked.connect(self.add_files)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        up_btn = QPushButton("Move Up")
        up_btn.clicked.connect(self.move_up)
        down_btn = QPushButton("Move Down")
        down_btn.clicked.connect(self.move_down)
        btns_layout.addWidget(add_btn)
        btns_layout.addWidget(remove_btn)
        btns_layout.addWidget(up_btn)
        btns_layout.addWidget(down_btn)
        btns_layout.addStretch()
        file_select_layout.addLayout(btns_layout)
        layout.addLayout(file_select_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Merge button
        self.merge_btn = QPushButton("Merge PDFs")
        self.merge_btn.clicked.connect(self.merge_pdfs)
        layout.addWidget(self.merge_btn)

        layout.addStretch()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDF files to merge", "", "PDF Files (*.pdf)")
        for f in files:
            if f not in self.selected_files:
                self.selected_files.append(f)
                self.file_list.addItem(f)
        self.status_callback(f"Added {len(files)} file(s)")

    def remove_selected(self):
        selected = self.file_list.selectedItems()
        for item in selected:
            idx = self.file_list.row(item)
            self.file_list.takeItem(idx)
            del self.selected_files[idx]
        self.status_callback(f"Removed {len(selected)} file(s)")

    def move_up(self):
        row = self.file_list.currentRow()
        if row > 0:
            self.selected_files[row-1], self.selected_files[row] = self.selected_files[row], self.selected_files[row-1]
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row-1, item)
            self.file_list.setCurrentRow(row-1)

    def move_down(self):
        row = self.file_list.currentRow()
        if row < self.file_list.count() - 1 and row != -1:
            self.selected_files[row+1], self.selected_files[row] = self.selected_files[row], self.selected_files[row+1]
            item = self.file_list.takeItem(row)
            self.file_list.insertItem(row+1, item)
            self.file_list.setCurrentRow(row+1)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def merge_pdfs(self):
        if len(self.selected_files) < 2:
            QMessageBox.warning(self, "Merge PDFs", "Please select at least two PDF files to merge.")
            return
        output_file = self.output_line.text().strip()
        if not output_file:
            QMessageBox.warning(self, "Merge PDFs", "Please specify an output file.")
            return
        # Call CLI logic
        try:
            class Args:
                input_files = self.selected_files
                output_file = output_file
            handle_merge(Args)
            self.status_callback(f"Merged {len(self.selected_files)} PDFs into '{output_file}'")
            QMessageBox.information(self, "Merge PDFs", f"Successfully merged PDFs into '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Merge PDFs", str(e), traceback.format_exc())

class SplitPDFPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Output path/pattern
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output Dir/Pattern:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse Dir...")
        out_btn.clicked.connect(self.select_output_dir)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Split mode selection
        self.mode_group = QButtonGroup(self)
        mode_layout = QHBoxLayout()
        self.ranges_radio = QRadioButton("By Ranges")
        self.n_radio = QRadioButton("Every N Pages")
        self.each_radio = QRadioButton("Each Page")
        self.ranges_radio.setChecked(True)
        self.mode_group.addButton(self.ranges_radio)
        self.mode_group.addButton(self.n_radio)
        self.mode_group.addButton(self.each_radio)
        mode_layout.addWidget(self.ranges_radio)
        mode_layout.addWidget(self.n_radio)
        mode_layout.addWidget(self.each_radio)
        layout.addLayout(mode_layout)

        # Ranges input
        self.ranges_line = QLineEdit()
        self.ranges_line.setPlaceholderText("e.g. 1-3,5,7-9")
        layout.addWidget(self.ranges_line)
        # N input
        self.n_line = QLineEdit()
        self.n_line.setPlaceholderText("Split every N pages (e.g. 2)")
        self.n_line.setEnabled(False)
        layout.addWidget(self.n_line)
        # No input for each page

        self.ranges_radio.toggled.connect(lambda checked: self.ranges_line.setEnabled(checked))
        self.n_radio.toggled.connect(lambda checked: self.n_line.setEnabled(checked))
        self.each_radio.toggled.connect(lambda checked: (self.ranges_line.setEnabled(False), self.n_line.setEnabled(False)))

        # Split button
        self.split_btn = QPushButton("Split PDF")
        self.split_btn.clicked.connect(self.split_pdf)
        layout.addWidget(self.split_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to split", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_line.setText(dir_path)

    def split_pdf(self):
        input_file = self.input_line.text().strip()
        output_path = self.output_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Split PDF", "Please select a valid input PDF file.")
            return
        if not output_path:
            QMessageBox.warning(self, "Split PDF", "Please specify an output directory or pattern.")
            return
        # Determine split mode
        ranges = self.ranges_line.text().strip() if self.ranges_radio.isChecked() else None
        every_n = int(self.n_line.text().strip()) if self.n_radio.isChecked() and self.n_line.text().strip().isdigit() else None
        each_page = self.each_radio.isChecked()
        if self.ranges_radio.isChecked() and not ranges:
            QMessageBox.warning(self, "Split PDF", "Please specify page ranges.")
            return
        if self.n_radio.isChecked() and not every_n:
            QMessageBox.warning(self, "Split PDF", "Please specify a valid N for splitting.")
            return
        # Call CLI logic
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.output_path = output_path
            Args.ranges = ranges if self.ranges_radio.isChecked() else None
            Args.every_n_pages = every_n if self.n_radio.isChecked() else None
            Args.each_page = each_page
            handle_split(Args)
            self.status_callback(f"Split '{input_file}' using mode: {'ranges' if ranges else 'every_n' if every_n else 'each_page'}")
            QMessageBox.information(self, "Split PDF", f"Successfully split '{input_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Split PDF", str(e), traceback.format_exc())

class ReorderPagesPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.page_order = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Page order list
        self.page_list = QListWidget()
        self.page_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(QLabel("Page Order (top = first page):"))
        layout.addWidget(self.page_list)

        btns_layout = QHBoxLayout()
        up_btn = QPushButton("Move Up")
        up_btn.clicked.connect(self.move_up)
        down_btn = QPushButton("Move Down")
        down_btn.clicked.connect(self.move_down)
        btns_layout.addWidget(up_btn)
        btns_layout.addWidget(down_btn)
        layout.addLayout(btns_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Load pages button
        load_btn = QPushButton("Load Pages")
        load_btn.clicked.connect(self.load_pages)
        layout.addWidget(load_btn)

        # Reorder button
        self.reorder_btn = QPushButton("Reorder Pages")
        self.reorder_btn.clicked.connect(self.reorder_pages)
        layout.addWidget(self.reorder_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to reorder", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def load_pages(self):
        input_file = self.input_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Reorder Pages", "Please select a valid input PDF file.")
            return
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(input_file)
            num_pages = len(reader.pages)
            self.page_order = list(range(1, num_pages+1))
            self.page_list.clear()
            for i in self.page_order:
                self.page_list.addItem(f"Page {i}")
            self.status_callback(f"Loaded {num_pages} pages from '{input_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Reorder Pages", str(e), traceback.format_exc())

    def move_up(self):
        row = self.page_list.currentRow()
        if row > 0:
            self.page_order[row-1], self.page_order[row] = self.page_order[row], self.page_order[row-1]
            item = self.page_list.takeItem(row)
            self.page_list.insertItem(row-1, item)
            self.page_list.setCurrentRow(row-1)

    def move_down(self):
        row = self.page_list.currentRow()
        if row < self.page_list.count() - 1 and row != -1:
            self.page_order[row+1], self.page_order[row] = self.page_order[row], self.page_order[row+1]
            item = self.page_list.takeItem(row)
            self.page_list.insertItem(row+1, item)
            self.page_list.setCurrentRow(row+1)

    def reorder_pages(self):
        input_file = self.input_line.text().strip()
        output_file = self.output_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Reorder Pages", "Please select a valid input PDF file.")
            return
        if not output_file:
            QMessageBox.warning(self, "Reorder Pages", "Please specify an output file.")
            return
        if not self.page_order or self.page_list.count() != len(self.page_order):
            QMessageBox.warning(self, "Reorder Pages", "Please load the pages first.")
            return
        # Compose page order string (1-indexed, comma-separated)
        page_order_str = ",".join(str(i) for i in self.page_order)
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.page_order = page_order_str
            Args.output_file = output_file
            handle_reorder(Args)
            self.status_callback(f"Reordered pages in '{input_file}' and saved to '{output_file}'")
            QMessageBox.information(self, "Reorder Pages", f"Successfully reordered pages and saved to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Reorder Pages", str(e), traceback.format_exc())

class DeletePagesPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Pages to delete
        pages_layout = QHBoxLayout()
        self.pages_line = QLineEdit()
        self.pages_line.setPlaceholderText("Pages to delete (e.g. 1,3-5,7)")
        pages_layout.addWidget(QLabel("Pages to Delete:"))
        pages_layout.addWidget(self.pages_line)
        layout.addLayout(pages_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Delete button
        self.delete_btn = QPushButton("Delete Pages")
        self.delete_btn.clicked.connect(self.delete_pages)
        layout.addWidget(self.delete_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to delete pages from", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def delete_pages(self):
        input_file = self.input_line.text().strip()
        pages_to_delete = self.pages_line.text().strip()
        output_file = self.output_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Delete Pages", "Please select a valid input PDF file.")
            return
        if not pages_to_delete:
            QMessageBox.warning(self, "Delete Pages", "Please specify pages to delete.")
            return
        if not output_file:
            QMessageBox.warning(self, "Delete Pages", "Please specify an output file.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.pages_to_delete = pages_to_delete
            Args.output_file = output_file
            handle_delete(Args)
            self.status_callback(f"Deleted pages {pages_to_delete} from '{input_file}' and saved to '{output_file}'")
            QMessageBox.information(self, "Delete Pages", f"Successfully deleted pages and saved to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Delete Pages", str(e), traceback.format_exc())

class RotatePagesPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Pages to rotate
        pages_layout = QHBoxLayout()
        self.pages_line = QLineEdit()
        self.pages_line.setPlaceholderText("Pages to rotate (e.g. 1,3-5,7) or leave blank for all")
        pages_layout.addWidget(QLabel("Pages to Rotate:"))
        pages_layout.addWidget(self.pages_line)
        layout.addLayout(pages_layout)

        # Rotation angle
        angle_layout = QHBoxLayout()
        self.angle_combo = QComboBox()
        self.angle_combo.addItems(["90", "180", "270"])
        angle_layout.addWidget(QLabel("Rotation Angle:"))
        angle_layout.addWidget(self.angle_combo)
        layout.addLayout(angle_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Rotate button
        self.rotate_btn = QPushButton("Rotate Pages")
        self.rotate_btn.clicked.connect(self.rotate_pages)
        layout.addWidget(self.rotate_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to rotate pages", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def rotate_pages(self):
        input_file = self.input_line.text().strip()
        pages = self.pages_line.text().strip()
        angle = int(self.angle_combo.currentText())
        output_file = self.output_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Rotate Pages", "Please select a valid input PDF file.")
            return
        if not output_file:
            QMessageBox.warning(self, "Rotate Pages", "Please specify an output file.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.pages = pages if pages else None
            Args.angle = angle
            Args.output_file = output_file
            handle_rotate(Args)
            self.status_callback(f"Rotated pages in '{input_file}' by {angle} degrees and saved to '{output_file}'")
            QMessageBox.information(self, "Rotate Pages", f"Successfully rotated pages and saved to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Rotate Pages", str(e), traceback.format_exc())

class ExtractTextPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Output TXT file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output Text File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Extract button
        self.extract_btn = QPushButton("Extract Text")
        self.extract_btn.clicked.connect(self.extract_text)
        layout.addWidget(self.extract_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to extract text from", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output Text File", "", "Text Files (*.txt)")
        if file_path:
            self.output_line.setText(file_path)

    def extract_text(self):
        input_file = self.input_line.text().strip()
        output_file = self.output_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Extract Text", "Please select a valid input PDF file.")
            return
        if not output_file:
            QMessageBox.warning(self, "Extract Text", "Please specify an output text file.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.output_file = output_file
            handle_extract_text(Args)
            self.status_callback(f"Extracted text from '{input_file}' to '{output_file}'")
            QMessageBox.information(self, "Extract Text", f"Successfully extracted text to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Extract Text", str(e), traceback.format_exc())

class ExtractImagesPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Output directory
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output Directory:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_dir)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Image quality/resolution (optional)
        quality_layout = QHBoxLayout()
        self.quality_line = QLineEdit()
        self.quality_line.setPlaceholderText("Image quality/resolution (optional, e.g. 90 or 300dpi)")
        quality_layout.addWidget(QLabel("Quality/Resolution:"))
        quality_layout.addWidget(self.quality_line)
        layout.addLayout(quality_layout)

        # Extract button
        self.extract_btn = QPushButton("Extract Images")
        self.extract_btn.clicked.connect(self.extract_images)
        layout.addWidget(self.extract_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to extract images from", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_line.setText(dir_path)

    def extract_images(self):
        input_file = self.input_line.text().strip()
        output_dir = self.output_line.text().strip()
        quality = self.quality_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Extract Images", "Please select a valid input PDF file.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Extract Images", "Please specify a valid output directory.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.output_dir = output_dir
            Args.quality = quality if quality else None
            handle_extract_images(Args)
            self.status_callback(f"Extracted images from '{input_file}' to '{output_dir}'")
            QMessageBox.information(self, "Extract Images", f"Successfully extracted images to '{output_dir}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Extract Images", str(e), traceback.format_exc())

class PDFToImagePanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Output directory
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output Directory:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_dir)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Page selection
        pages_layout = QHBoxLayout()
        self.pages_line = QLineEdit()
        self.pages_line.setPlaceholderText("Pages to export (e.g. 1,3-5,7) or leave blank for all")
        pages_layout.addWidget(QLabel("Pages:"))
        pages_layout.addWidget(self.pages_line)
        layout.addLayout(pages_layout)

        # Output image format
        format_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPG"])
        format_layout.addWidget(QLabel("Image Format:"))
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # DPI/Quality
        dpi_layout = QHBoxLayout()
        self.dpi_line = QLineEdit()
        self.dpi_line.setPlaceholderText("DPI/Quality (e.g. 150 or 90, optional)")
        dpi_layout.addWidget(QLabel("DPI/Quality:"))
        dpi_layout.addWidget(self.dpi_line)
        layout.addLayout(dpi_layout)

        # Convert button
        self.convert_btn = QPushButton("Convert PDF to Images")
        self.convert_btn.clicked.connect(self.convert_pdf_to_images)
        layout.addWidget(self.convert_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to convert to images", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_line.setText(dir_path)

    def convert_pdf_to_images(self):
        input_file = self.input_line.text().strip()
        output_dir = self.output_line.text().strip()
        pages = self.pages_line.text().strip()
        img_format = self.format_combo.currentText().lower()
        dpi = self.dpi_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "PDF to Image", "Please select a valid input PDF file.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "PDF to Image", "Please specify a valid output directory.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.output_dir = output_dir
            Args.pages = pages if pages else None
            Args.format = img_format
            Args.dpi = dpi if dpi else None
            handle_pdf_to_image(Args)
            self.status_callback(f"Converted '{input_file}' to images in '{output_dir}'")
            QMessageBox.information(self, "PDF to Image", f"Successfully converted PDF to images in '{output_dir}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "PDF to Image", str(e), traceback.format_exc())

class ImagesToPDFPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.selected_images = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Image selection
        img_select_layout = QHBoxLayout()
        self.img_list = QListWidget()
        self.img_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        img_select_layout.addWidget(self.img_list)
        btns_layout = QVBoxLayout()
        add_btn = QPushButton("Add Images...")
        add_btn.clicked.connect(self.add_images)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected)
        up_btn = QPushButton("Move Up")
        up_btn.clicked.connect(self.move_up)
        down_btn = QPushButton("Move Down")
        down_btn.clicked.connect(self.move_down)
        btns_layout.addWidget(add_btn)
        btns_layout.addWidget(remove_btn)
        btns_layout.addWidget(up_btn)
        btns_layout.addWidget(down_btn)
        btns_layout.addStretch()
        img_select_layout.addLayout(btns_layout)
        layout.addLayout(img_select_layout)

        # Images per page (optional)
        ipp_layout = QHBoxLayout()
        self.ipp_line = QLineEdit()
        self.ipp_line.setPlaceholderText("Images per page (optional, e.g. 1)")
        ipp_layout.addWidget(QLabel("Images per Page:"))
        ipp_layout.addWidget(self.ipp_line)
        layout.addLayout(ipp_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output PDF File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Convert button
        self.convert_btn = QPushButton("Convert Images to PDF")
        self.convert_btn.clicked.connect(self.convert_images_to_pdf)
        layout.addWidget(self.convert_btn)
        layout.addStretch()

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images to convert to PDF", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)")
        for f in files:
            if f not in self.selected_images:
                self.selected_images.append(f)
                self.img_list.addItem(f)
        self.status_callback(f"Added {len(files)} image(s)")

    def remove_selected(self):
        selected = self.img_list.selectedItems()
        for item in selected:
            idx = self.img_list.row(item)
            self.img_list.takeItem(idx)
            del self.selected_images[idx]
        self.status_callback(f"Removed {len(selected)} image(s)")

    def move_up(self):
        row = self.img_list.currentRow()
        if row > 0:
            self.selected_images[row-1], self.selected_images[row] = self.selected_images[row], self.selected_images[row-1]
            item = self.img_list.takeItem(row)
            self.img_list.insertItem(row-1, item)
            self.img_list.setCurrentRow(row-1)

    def move_down(self):
        row = self.img_list.currentRow()
        if row < self.img_list.count() - 1 and row != -1:
            self.selected_images[row+1], self.selected_images[row] = self.selected_images[row], self.selected_images[row+1]
            item = self.img_list.takeItem(row)
            self.img_list.insertItem(row+1, item)
            self.img_list.setCurrentRow(row+1)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def convert_images_to_pdf(self):
        if len(self.selected_images) < 1:
            QMessageBox.warning(self, "Images to PDF", "Please select at least one image file.")
            return
        output_file = self.output_line.text().strip()
        if not output_file:
            QMessageBox.warning(self, "Images to PDF", "Please specify an output PDF file.")
            return
        images_per_page = self.ipp_line.text().strip()
        try:
            class Args:
                pass
            Args.input_files = self.selected_images
            Args.output_file = output_file
            Args.images_per_page = int(images_per_page) if images_per_page.isdigit() else None
            handle_images_to_pdf(Args)
            self.status_callback(f"Converted {len(self.selected_images)} images to '{output_file}'")
            QMessageBox.information(self, "Images to PDF", f"Successfully converted images to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Images to PDF", str(e), traceback.format_exc())

class AddPageNumbersPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Position selection
        pos_layout = QHBoxLayout()
        self.header_footer_combo = QComboBox()
        self.header_footer_combo.addItems(["Header", "Footer"])
        self.lr_combo = QComboBox()
        self.lr_combo.addItems(["Left", "Center", "Right"])
        pos_layout.addWidget(QLabel("Position:"))
        pos_layout.addWidget(self.header_footer_combo)
        pos_layout.addWidget(self.lr_combo)
        layout.addLayout(pos_layout)

        # Starting number
        start_layout = QHBoxLayout()
        self.start_line = QLineEdit()
        self.start_line.setPlaceholderText("Starting number (e.g. 1)")
        start_layout.addWidget(QLabel("Start Number:"))
        start_layout.addWidget(self.start_line)
        layout.addLayout(start_layout)

        # Font style/size
        font_layout = QHBoxLayout()
        self.font_line = QLineEdit()
        self.font_line.setPlaceholderText("Font (e.g. Arial)")
        font_layout.addWidget(QLabel("Font:"))
        font_layout.addWidget(self.font_line)
        self.size_line = QLineEdit()
        self.size_line.setPlaceholderText("Size (e.g. 12)")
        font_layout.addWidget(QLabel("Size:"))
        font_layout.addWidget(self.size_line)
        layout.addLayout(font_layout)

        # Page range
        range_layout = QHBoxLayout()
        self.range_line = QLineEdit()
        self.range_line.setPlaceholderText("Page range (e.g. 1-3,5) or leave blank for all")
        range_layout.addWidget(QLabel("Page Range:"))
        range_layout.addWidget(self.range_line)
        layout.addLayout(range_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output PDF File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Add Page Numbers button
        self.add_btn = QPushButton("Add Page Numbers")
        self.add_btn.clicked.connect(self.add_page_numbers)
        layout.addWidget(self.add_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to add page numbers", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def add_page_numbers(self):
        input_file = self.input_line.text().strip()
        output_file = self.output_line.text().strip()
        page_range = self.range_line.text().strip()
        start_number = self.start_line.text().strip()
        font = self.font_line.text().strip()
        size = self.size_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Add Page Numbers", "Please select a valid input PDF file.")
            return
        if not output_file:
            QMessageBox.warning(self, "Add Page Numbers", "Please specify an output PDF file.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.output_file = output_file
            Args.page_range = page_range if page_range else None
            Args.position = f"{self.header_footer_combo.currentText().lower()}_{self.lr_combo.currentText().lower()}"
            Args.start_number = int(start_number) if start_number.isdigit() else 1
            Args.font = font or None
            Args.size = int(size) if size.isdigit() else None
            handle_add_page_numbers(Args)
            self.status_callback(f"Added page numbers to '{input_file}' and saved to '{output_file}'")
            QMessageBox.information(self, "Add Page Numbers", f"Successfully added page numbers to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Add Page Numbers", str(e), traceback.format_exc())

class EncryptPDFPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Owner/User passwords
        owner_layout = QHBoxLayout()
        self.owner_line = QLineEdit()
        self.owner_line.setPlaceholderText("Owner password (optional)")
        owner_layout.addWidget(QLabel("Owner Password:"))
        owner_layout.addWidget(self.owner_line)
        layout.addLayout(owner_layout)
        user_layout = QHBoxLayout()
        self.user_line = QLineEdit()
        self.user_line.setPlaceholderText("User password (to open PDF)")
        user_layout.addWidget(QLabel("User Password:"))
        user_layout.addWidget(self.user_line)
        layout.addLayout(user_layout)

        # Permissions
        perm_layout = QHBoxLayout()
        self.printing_cb = QPushButton("Allow Printing")
        self.printing_cb.setCheckable(True)
        self.printing_cb.setChecked(True)
        self.copying_cb = QPushButton("Allow Copying")
        self.copying_cb.setCheckable(True)
        self.copying_cb.setChecked(True)
        self.modifying_cb = QPushButton("Allow Modifying")
        self.modifying_cb.setCheckable(True)
        self.modifying_cb.setChecked(True)
        perm_layout.addWidget(self.printing_cb)
        perm_layout.addWidget(self.copying_cb)
        perm_layout.addWidget(self.modifying_cb)
        layout.addLayout(perm_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output PDF File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Encrypt button
        self.encrypt_btn = QPushButton("Encrypt PDF")
        self.encrypt_btn.clicked.connect(self.encrypt_pdf)
        layout.addWidget(self.encrypt_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to encrypt", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def encrypt_pdf(self):
        input_file = self.input_line.text().strip()
        output_file = self.output_line.text().strip()
        owner_pw = self.owner_line.text().strip()
        user_pw = self.user_line.text().strip()
        allow_printing = self.printing_cb.isChecked()
        allow_copying = self.copying_cb.isChecked()
        allow_modifying = self.modifying_cb.isChecked()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Encrypt PDF", "Please select a valid input PDF file.")
            return
        if not output_file:
            QMessageBox.warning(self, "Encrypt PDF", "Please specify an output PDF file.")
            return
        if not user_pw:
            QMessageBox.warning(self, "Encrypt PDF", "Please specify a user password.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.output_file = output_file
            Args.owner_password = owner_pw or None
            Args.user_password = user_pw
            Args.allow_printing = allow_printing
            Args.allow_copying = allow_copying
            Args.allow_modifying = allow_modifying
            handle_encrypt(Args)
            self.status_callback(f"Encrypted '{input_file}' and saved to '{output_file}'")
            QMessageBox.information(self, "Encrypt PDF", f"Successfully encrypted PDF to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Encrypt PDF", str(e), traceback.format_exc())

class DecryptPDFPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Password
        pw_layout = QHBoxLayout()
        self.pw_line = QLineEdit()
        self.pw_line.setPlaceholderText("Password")
        self.pw_line.setEchoMode(QLineEdit.Password)
        pw_layout.addWidget(QLabel("Password:"))
        pw_layout.addWidget(self.pw_line)
        layout.addLayout(pw_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output PDF File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Decrypt button
        self.decrypt_btn = QPushButton("Decrypt PDF")
        self.decrypt_btn.clicked.connect(self.decrypt_pdf)
        layout.addWidget(self.decrypt_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to decrypt", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def decrypt_pdf(self):
        input_file = self.input_line.text().strip()
        output_file = self.output_line.text().strip()
        password = self.pw_line.text().strip()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Decrypt PDF", "Please select a valid input PDF file.")
            return
        if not output_file:
            QMessageBox.warning(self, "Decrypt PDF", "Please specify an output PDF file.")
            return
        if not password:
            QMessageBox.warning(self, "Decrypt PDF", "Please enter the password.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.output_file = output_file
            Args.password = password
            handle_decrypt(Args)
            self.status_callback(f"Decrypted '{input_file}' and saved to '{output_file}'")
            QMessageBox.information(self, "Decrypt PDF", f"Successfully decrypted PDF to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Decrypt PDF", str(e), traceback.format_exc())

class CompressPDFPanel(QWidget):
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Input PDF selection
        in_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        in_layout.addWidget(QLabel("Input PDF:"))
        in_layout.addWidget(self.input_line)
        in_btn = QPushButton("Browse...")
        in_btn.clicked.connect(self.select_input_file)
        in_layout.addWidget(in_btn)
        layout.addLayout(in_layout)

        # Compression level
        level_layout = QHBoxLayout()
        self.level_combo = QComboBox()
        self.level_combo.addItems(["Basic", "Strong"])
        level_layout.addWidget(QLabel("Compression Level:"))
        level_layout.addWidget(self.level_combo)
        layout.addLayout(level_layout)

        # Output file
        out_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        out_layout.addWidget(QLabel("Output PDF File:"))
        out_layout.addWidget(self.output_line)
        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self.select_output_file)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Compress button
        self.compress_btn = QPushButton("Compress PDF")
        self.compress_btn.clicked.connect(self.compress_pdf)
        layout.addWidget(self.compress_btn)
        layout.addStretch()

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to compress", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_line.setText(file_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.output_line.setText(file_path)

    def compress_pdf(self):
        input_file = self.input_line.text().strip()
        output_file = self.output_line.text().strip()
        level = self.level_combo.currentText().lower()
        if not input_file or not os.path.exists(input_file):
            QMessageBox.warning(self, "Compress PDF", "Please select a valid input PDF file.")
            return
        if not output_file:
            QMessageBox.warning(self, "Compress PDF", "Please specify an output PDF file.")
            return
        try:
            class Args:
                pass
            Args.input_file = input_file
            Args.output_file = output_file
            Args.level = level
            handle_compress(Args)
            self.status_callback(f"Compressed '{input_file}' to '{output_file}' (level: {level})")
            QMessageBox.information(self, "Compress PDF", f"Successfully compressed PDF to '{output_file}'")
        except Exception as e:
            self.status_callback(f"Error: {e}")
            show_error_dialog(self, "Compress PDF", str(e), traceback.format_exc())

class ProgressDialog(QProgressDialog):
    def __init__(self, label, parent=None):
        super().__init__(label, None, 0, 0, parent)
        self.setWindowTitle("Processing...")
        self.setWindowModality(Qt.WindowModal)
        self.setCancelButton(None)
        self.setMinimumDuration(0)

def show_error_dialog(parent, title, message, details=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    if details:
        msg.setDetailedText(details)
    msg.exec_()

class HelpDialog(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyDF Pro Help")
        self.setIcon(QMessageBox.Information)
        self.setText("<b>PyDF Pro - Help & Usage Tips</b>")
        self.setDetailedText(
            """
<b>Feature Overview:</b>
- Merge PDFs: Combine multiple PDFs into one.
- Split PDF: Split a PDF by ranges, every N pages, or each page.
- Reorder Pages: Change the order of pages in a PDF.
- Delete Pages: Remove specific pages from a PDF.
- Rotate Pages: Rotate selected or all pages.
- Extract Text/Images: Save text or images from a PDF.
- PDF to Image: Export PDF pages as images.
- Images to PDF: Combine images into a PDF.
- Add Watermark: Add text or image watermarks.
- Add Page Numbers: Insert page numbers with style options.
- Encrypt/Decrypt: Add or remove PDF passwords.
- Compress: Reduce PDF file size.

<b>Usage Tips:</b>
- Use the sidebar to select features.
- Drag and drop PDF files into the app to add to recent files.
- Use the status bar for progress and error messages.
- Right-click on file lists for more options (where available).
- For detailed errors, click 'Show Details' in error dialogs.

<b>Documentation & Support:</b>
- See the README for full documentation.
- For help, visit: https://github.com/yourrepo/pydfpro
- Contact: support@pydfpro.com
"""
        )
        self.setStandardButtons(QMessageBox.Ok)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1000, 700)
        self.file_mgmt = FileManagement()
        self._init_ui()

    def _init_ui(self):
        # Menu Bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        open_action = QAction("Open PDF...", self)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        save_action = QAction("Save As...", self)
        save_action.triggered.connect(self.save_file_dialog)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        recent_menu = file_menu.addMenu("Recent Files")
        self.recent_menu = recent_menu
        self.update_recent_files_menu()
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        help_action = QAction("Help", self)
        help_action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(help_action)

        # Toolbar
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)

        # Main Layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Feature Navigation
        self.feature_list = QListWidget()
        self.feature_list.setFixedWidth(200)
        features = [
            "Merge PDFs", "Split PDF", "Reorder Pages", "Delete Pages", "Rotate Pages",
            "Extract Text", "Extract Images", "PDF to Image", "Images to PDF",
            "Add Watermark", "Add Page Numbers", "Encrypt PDF", "Decrypt PDF", "Compress PDF"
        ]
        for feat in features:
            QListWidgetItem(feat, self.feature_list)
        self.feature_list.currentRowChanged.connect(self.switch_feature_panel)
        main_layout.addWidget(self.feature_list)

        # Feature Panels
        self.feature_panels = QStackedWidget()
        self.feature_panels.addWidget(MergePDFsPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(SplitPDFPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(ReorderPagesPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(DeletePagesPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(RotatePagesPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(ExtractTextPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(ExtractImagesPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(PDFToImagePanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(ImagesToPDFPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(AddPageNumbersPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(EncryptPDFPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(DecryptPDFPanel(self.status_bar.showMessage))
        self.feature_panels.addWidget(CompressPDFPanel(self.status_bar.showMessage))
        for feat in features[14:]:
            self.feature_panels.addWidget(FeaturePanel(feat))
        main_layout.addWidget(self.feature_panels)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Drag and Drop
        self.setAcceptDrops(True)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf);;All Files (*)")
        if file_path:
            self.file_mgmt.add_recent_file(file_path)
            self.status_bar.showMessage(f"Opened: {file_path}", 5000)
            self.update_recent_files_menu()

    def save_file_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save As", "", "PDF Files (*.pdf);;All Files (*)")
        if file_path:
            self.status_bar.showMessage(f"Save As: {file_path}", 5000)

    def update_recent_files_menu(self):
        self.recent_menu.clear()
        for path in self.file_mgmt.recent_files:
            act = QAction(path, self)
            act.triggered.connect(lambda checked, p=path: self.open_recent_file(p))
            self.recent_menu.addAction(act)

    def open_recent_file(self, path):
        if os.path.exists(path):
            self.status_bar.showMessage(f"Opened: {path}", 5000)
        else:
            QMessageBox.warning(self, "File Not Found", f"The file '{path}' does not exist.")
            self.file_mgmt.recent_files.remove(path)
            self.update_recent_files_menu()

    def show_about_dialog(self):
        QMessageBox.information(
            self,
            "About PyDF Pro GUI",
            f"<b>PyDF Pro</b><br>A Python-powered PDF utility with GUI.<br><br>Version 1.0<br>© 2025 PyDF Pro Team<br><br>For help, see the Help menu or visit <a href='https://github.com/yourrepo/pydfpro'>GitHub</a>."
        )

    def show_help_dialog(self):
        dlg = HelpDialog(self)
        dlg.exec_()

    def switch_feature_panel(self, index):
        self.feature_panels.setCurrentIndex(index)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.pdf'):
                self.file_mgmt.add_recent_file(path)
                self.status_bar.showMessage(f"Dropped: {path}", 5000)
                self.update_recent_files_menu()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 