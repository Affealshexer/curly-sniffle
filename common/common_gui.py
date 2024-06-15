from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QLabel,
                               QApplication, QHBoxLayout, QFrame, QScrollArea)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from aplustools.io.environment import System, SystemTheme
import itertools
import sys
import os


class BaseDocumentViewerControls(QWidget):
    FIT_CHANGED = Signal(str)
    POP_CHANGED = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Document Viewer')

        self.mode_iterator = itertools.cycle(("./assets/fit_both.svg", "./assets/no_limit.svg", "./assets/fit_width.svg", "./assets/fit_height.svg"))
        self.popout_iterator = itertools.cycle(("./assets/pop_out.svg", "./assets/pop_in.svg"))

        self.main_layout = QHBoxLayout(self)
        self.controls_layout = QVBoxLayout(self)

        self.pop_button = QPushButton()
        self.pop_button.setIcon(QPixmap(next(self.popout_iterator)))
        self.pop_button.clicked.connect(self.change_pop)
        self.pop_button.setFixedSize(40, 40)
        self.controls_layout.addWidget(self.pop_button)

        self.fit_button = QPushButton()
        self.fit_button.setIcon(QPixmap(next(self.mode_iterator)))
        self.fit_button.clicked.connect(self.change_fit)
        self.fit_button.setFixedSize(40, 40)
        self.controls_layout.addWidget(self.fit_button)

        self.fit_window_button = QPushButton()
        self.fit_window_button.setIcon(QPixmap("assets/fit_window.svg"))
        self.FIT_WINDOW = self.fit_window_button.clicked
        self.fit_window_button.setFixedSize(40, 40)
        self.controls_layout.addWidget(self.fit_window_button)

        self.controls_frame = QFrame()
        self.controls_frame.setMaximumWidth(60)
        self.controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.controls_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.controls_frame.setLayout(self.controls_layout)

        self.setMinimumSize(300, 200)

        self.main_layout.addWidget(self.controls_frame, alignment=Qt.AlignmentFlag.AlignLeft)

        self.setLayout(self.main_layout)

        self.fit_emit = "fit_both"
        self.pop_emit = "pop_out"

    def change_fit(self):
        fit = next(self.mode_iterator)
        self.fit_button.setIcon(QPixmap(fit))
        self.fit_emit = os.path.basename(fit).split(".")[0]
        self.FIT_CHANGED.emit(self.fit_emit)

    def change_pop(self):
        pop = next(self.popout_iterator)
        self.pop_button.setIcon(QPixmap(pop))
        self.pop_emit = os.path.basename(pop).split(".")[0]
        self.POP_CHANGED.emit(self.pop_emit)


class DocumentViewer(BaseDocumentViewerControls):
    def __init__(self, parent=None, allow_multiple_popouts: bool = False):
        super().__init__(parent)
        self.system = System.system()
        self.theme = self.system.get_system_theme()
        self.scroll_area = QScrollArea()  # Scroll area for the content
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setFrameShape(QFrame.Shape.StyledPanel)
        self.scroll_area.setFrameShadow(QFrame.Shadow.Raised)
        self.scroll_area.setStyleSheet(f"""
                    QScrollArea {{
                        border-radius: 5px;
                        background-color: #{"2d2d2d" if self.theme == SystemTheme.DARK else "fbfbfb"};
                        margin: 1px;
                    }}
                    QScrollArea > QWidget > QWidget {{
                        border: none;
                        border-radius: 15px;
                        background-color: transparent;
                    }}
                    QScrollBar:vertical {{
                        border: none;
                        background: #{'3c3c3c' if self.theme == SystemTheme.DARK else 'f0f0f0'};
                        width: 15px;
                        margin: 15px 0 15px 0;
                        border-radius: 7px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: #{'888888' if self.theme == SystemTheme.DARK else 'cccccc'};
                        min-height: 20px;
                        border-radius: 7px;
                    }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                        border: none;
                        background: none;
                    }}
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                        background: none;
                    }}
                    QScrollBar:horizontal {{
                        border: none;
                        background: #{'3c3c3c' if self.theme == SystemTheme.DARK else 'f0f0f0'};
                        height: 15px;
                        margin: 0 15px 0 15px;
                        border-radius: 7px;
                    }}
                    QScrollBar::handle:horizontal {{
                        background: #{'888888' if self.theme == SystemTheme.DARK else 'cccccc'};
                        min-width: 20px;
                        border-radius: 7px;
                    }}
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                        border: none;
                        background: none;
                    }}
                    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                        background: none;
                    }}
                """)

        self.general_preview_widget = QLabel()
        self.general_preview_widget.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.general_preview_widget.setWordWrap(True)

        self.video_widget = QVideoWidget()
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)

        self.pdf_view = QPdfView()
        self.pdf_document = QPdfDocument(self)
        self.pdf_view.setDocument(self.pdf_document)

        self.scroll_layout.addWidget(self.general_preview_widget)
        self.scroll_layout.addWidget(self.video_widget)
        self.scroll_layout.addWidget(self.pdf_view)
        self.general_preview_widget.hide()
        self.video_widget.hide()
        self.pdf_view.hide()

        self.main_layout.addWidget(self.scroll_area)
        self.is_popped_out = False
        self.current_file_path = ""
        self.POP_CHANGED.connect(self.pop_out_in)
        self.wins = []
        self.allow_multiple_popouts = allow_multiple_popouts
        self.FIT_CHANGED.connect(self.fit_content)
        self.FIT_WINDOW.connect(self.fit_window)
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.timer_tick)
        self.timer.start()

    def fit_content(self):
        if self.fit_emit == "fit_width":
            if self.pdf_view.isVisible():
                self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            elif self.video_widget.isVisible():
                self.video_widget.setFixedSize(self.scroll_area.width(), self.video_widget.height())
            elif self.general_preview_widget.isVisible():
                if self.general_preview_widget.pixmap().isNull():
                    self.general_preview_widget.setWordWrap(False)
                else:
                    pixmap = QPixmap(self.current_file_path)
                    self.general_preview_widget.setPixmap(pixmap.scaled(self.scroll_area.width(), pixmap.height(),
                                                                        Qt.AspectRatioMode.KeepAspectRatio))
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        elif self.fit_emit == "fit_height":
            if self.pdf_view.isVisible():
                self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
                self.pdf_view.setZoomFactor(0.0)
                self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
                self.pdf_view.setZoomFactor((self.scroll_area.height() / self.pdf_document.pagePointSize(0).height()) / 1.4)
            elif self.video_widget.isVisible():
                self.video_widget.setFixedSize(self.video_widget.width(), self.scroll_area.height())
            if self.general_preview_widget.isVisible():
                if self.general_preview_widget.pixmap().isNull():
                    self.general_preview_widget.setWordWrap(True)
                else:
                    pixmap = QPixmap(self.current_file_path)
                    self.general_preview_widget.setPixmap(pixmap.scaled(pixmap.width(), self.scroll_area.height(),
                                                                        Qt.AspectRatioMode.KeepAspectRatio))
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        elif self.fit_emit == "fit_both":
            if self.pdf_view.isVisible():
                self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
            elif self.video_widget.isVisible():
                self.video_widget.setFixedSize(self.scroll_area.size())
            elif self.general_preview_widget.isVisible():
                if self.general_preview_widget.pixmap().isNull():
                    self.general_preview_widget.setWordWrap(True)
                else:
                    pixmap = QPixmap(self.current_file_path)
                    self.general_preview_widget.setPixmap(pixmap.scaled(self.scroll_area.size()))
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        elif self.fit_emit == "no_limit":  # fit_none
            if self.pdf_view.isVisible():
                self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
                self.pdf_view.setZoomFactor(1.0)
            elif self.video_widget.isVisible():
                self.video_widget.setFixedSize(600, 400)
            if self.general_preview_widget.isVisible():
                if self.general_preview_widget.pixmap().isNull():
                    self.general_preview_widget.setWordWrap(True)
                else:
                    pixmap = QPixmap(self.current_file_path)
                    self.general_preview_widget.setPixmap(pixmap)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def pop_out_in(self):
        if self.is_popped_out:
            self.close()
        else:
            if not self.allow_multiple_popouts and len(self.wins) > 0:
                self.wins[0].close()
                del self.wins[0]
            win = DocumentViewer()
            win.preview_document(self.current_file_path)
            win.pop_button.setIcon(QPixmap(next(win.popout_iterator)))
            win.is_popped_out = True
            win.show()
            win.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().value())
            win.scroll_area.horizontalScrollBar().setValue(self.scroll_area.horizontalScrollBar().value())
            win.fit_in(self.fit_emit, itertools.tee(self.mode_iterator)[0])
            win.fit_content()
            self.wins.append(win)

    def fit_in(self, current_fit, iterator):
        self.mode_iterator = iterator
        self.fit_button.setIcon(QPixmap(f"./assets/{current_fit}.svg"))
        self.fit_emit = current_fit

    def change_pop(self):
        pop = next(self.popout_iterator)
        self.pop_emit = os.path.basename(pop).split(".")[0]
        self.POP_CHANGED.emit(self.pop_emit)

    def preview_document(self, file_path: str):
        self.current_file_path = file_path

        self.general_preview_widget.hide()
        self.video_widget.hide()
        self.pdf_view.hide()

        if not file_path:
            return

        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
            self.general_preview_widget.show()
            self.general_preview_widget.setPixmap(QPixmap(file_path))
        elif file_path.lower().endswith('.pdf'):
            self.pdf_view.show()
            self.pdf_document.load(file_path)
        elif file_path.lower().endswith(('.mp4', '.mov')):
            self.video_widget.show()
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.play()
        else:
            self.general_preview_widget.show()
            try:
                with open(file_path, 'r') as f:
                    contents = f.read()
                self.general_preview_widget.setText(contents)
            except Exception:
                self.general_preview_widget.setText(f"Unsupported file format: {file_path}")

        self.fit_content()

    def fit_window(self, arg):
        if self.is_popped_out:
            # Adjust the scroll area to its contents
            self.scroll_area.adjustSize()

            # Calculate the new size based on the content
            content_size = self.scroll_content.sizeHint()

            # Set the scroll area size to match the content size
            self.setMinimumSize(content_size)
            self.setMaximumSize(content_size)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_content()

    def reapply_theme(self):
        self.scroll_area.setStyleSheet(f"""
                    QScrollArea {{
                        border-radius: 5px;
                        background-color: #{"2d2d2d" if self.theme == SystemTheme.DARK else "fbfbfb"};
                        margin: 1px;
                    }}
                    QScrollArea > QWidget > QWidget {{
                        border: none;
                        border-radius: 15px;
                        background-color: transparent;
                    }}
                    QScrollBar:vertical {{
                        border: none;
                        background: #{'3c3c3c' if self.theme == SystemTheme.DARK else 'f0f0f0'};
                        width: 15px;
                        margin: 15px 0 15px 0;
                        border-radius: 7px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: #{'888888' if self.theme == SystemTheme.DARK else 'cccccc'};
                        min-height: 20px;
                        border-radius: 7px;
                    }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                        border: none;
                        background: none;
                    }}
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                        background: none;
                    }}
                    QScrollBar:horizontal {{
                        border: none;
                        background: #{'3c3c3c' if self.theme == SystemTheme.DARK else 'f0f0f0'};
                        height: 15px;
                        margin: 0 15px 0 15px;
                        border-radius: 7px;
                    }}
                    QScrollBar::handle:horizontal {{
                        background: #{'888888' if self.theme == SystemTheme.DARK else 'cccccc'};
                        min-width: 20px;
                        border-radius: 7px;
                    }}
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                        border: none;
                        background: none;
                    }}
                    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                        background: none;
                    }}
                """)

    def timer_tick(self):
        current_theme = self.system.get_system_theme()
        if current_theme != self.theme:
            self.theme = current_theme
            self.reapply_theme()


if __name__ == "___main__":
    app = QApplication(sys.argv)
    window = DocumentViewer()
    window.preview_document(r"C:\Users\till_\OneDrive\Desktop\8.jpg")
    window.show()
    sys.exit(app.exec())


from PySide6.QtWidgets import (QLineEdit, QTextEdit, QGroupBox, QListWidget,
                               QFileDialog, QDialog, QFormLayout, QComboBox,
                               QMessageBox, QDateEdit)
from PySide6.QtCore import QDate
from aplustools.io.gui import QNoSpacingHBoxLayout, QNoSpacingVBoxLayout, QBulletPointTextEdit


class QPersonWidget(QFrame):
    clicked = Signal()
    selected = Signal()

    def __init__(self, name, representation, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QPersonWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 5px;
            }""")
        self.setSelectable(False)

        layout = QNoSpacingHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(9)

        self.name_label = QLabel(name)
        self.representation_label = QLabel(representation)

        self.remove_button = QPushButton('Remove')
        self.remove_button.setFixedSize(60, 25)
        self.remove_button.clicked.connect(self.remove_person)

        layout.addWidget(self.name_label)
        layout.addWidget(self.representation_label)
        layout.addWidget(self.remove_button)
        self.setFocusPolicy(Qt.StrongFocus)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.isSelected:
                self.selected.emit()
                self.setSelectable(True)
                self.updateSelectionStyle()
            else:
                self.clicked.emit()

    def focusInEvent(self, event):
        self.setSelectable(True)
        self.updateSelectionStyle()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setSelectable(False)
        self.updateSelectionStyle()
        super().focusOutEvent(event)

    def setSelectable(self, selectable):
        self.isSelected = selectable

    def updateSelectionStyle(self):
        if self.isSelected:
            self.setStyleSheet("""
                QPersonWidget {
                    background-color: #e6f7ff;
                    border: 1px solid #007bff;
                    border-radius: 5px;
                }
                QPushButton {
                    border: 1px solid #007bff;
                    border-radius: 5px;
                }""")
        else:
            self.setStyleSheet("""
                QPersonWidget {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
                QPushButton {
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }""")

    def remove_person(self):
        self.setParent(None)

    def deselect(self):
        self.setSelectable(False)
        self.updateSelectionStyle()


class QPersonListWidget(QWidget):
    personActivated = Signal(QPersonWidget)

    def __init__(self, parent=None):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.selected_widget = None

    def add_person(self, name, representation):
        person_widget = QPersonWidget(name, representation)
        person_widget.clicked.connect(lambda: self.on_person_clicked(person_widget))
        person_widget.selected.connect(lambda: self.on_person_selected(person_widget))
        self.layout.addWidget(person_widget)

    def on_person_selected(self, person_widget):
        if self.selected_widget and self.selected_widget != person_widget:
            self.selected_widget.deselect()
        self.selected_widget = person_widget

    def on_person_clicked(self, person_widget):
        self.personActivated.emit(person_widget)


class NewCaseFrame(QFrame):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()

        # Title input
        self.title_layout = QNoSpacingHBoxLayout()
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText('Title')
        self.title_input.setStyleSheet("font-size: 24px; height: 40px;")
        self.save_case_button = QPushButton("Create Case")
        self.title_layout.addWidget(self.title_input)
        self.title_layout.addWidget(self.save_case_button)
        main_layout.addLayout(self.title_layout)

        # Description
        extra_info_layout = QNoSpacingHBoxLayout()
        extra_info_layout.setSpacing(9)
        self.description_groupbox = QGroupBox('Description')
        self.description_text = QTextEdit()
        self.description_text.setStyleSheet("border-radius:10px; background-color: palette(base); ")
        description_layout = QVBoxLayout()
        description_layout.addWidget(self.description_text)
        self.description_groupbox.setLayout(description_layout)
        extra_info_layout.addWidget(self.description_groupbox)
        # Notes
        self.notes_groupbox = QGroupBox('Notes')
        self.notes_text = QBulletPointTextEdit()
        self.notes_text.setStyleSheet("border-radius:10px; background-color: palette(base); ")
        notes_layout = QVBoxLayout()
        notes_layout.addWidget(self.notes_text)
        self.notes_groupbox.setLayout(notes_layout)
        extra_info_layout.addWidget(self.notes_groupbox)
        main_layout.addLayout(extra_info_layout)

        # Documents GroupBox
        self.documents_layout = QHBoxLayout()
        self.documents_groupbox = QGroupBox('Documents')
        documents_layout = QVBoxLayout()
        self.documents_list = QListWidget()
        self.documents_list.setStyleSheet("border-radius:10px; background-color: palette(base); ")
        self.theme = System().system().get_system_theme()
        self.documents_list.setStyleSheet(f"""
                    QScrollBar:vertical {{
                        border: none;
                        background: #{'3c3c3c' if self.theme == SystemTheme.DARK else 'f0f0f0'};
                        width: 15px;
                        margin: 15px 0 15px 0;
                        border-radius: 7px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: #{'888888' if self.theme == SystemTheme.DARK else 'cccccc'};
                        min-height: 20px;
                        border-radius: 7px;
                    }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                        border: none;
                        background: none;
                    }}
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                        background: none;
                    }}
                    QScrollBar:horizontal {{
                        border: none;
                        background: #{'3c3c3c' if self.theme == SystemTheme.DARK else 'f0f0f0'};
                        height: 15px;
                        margin: 0 15px 0 15px;
                        border-radius: 7px;
                    }}
                    QScrollBar::handle:horizontal {{
                        background: #{'888888' if self.theme == SystemTheme.DARK else 'cccccc'};
                        min-width: 20px;
                        border-radius: 7px;
                    }}
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                        border: none;
                        background: none;
                    }}
                    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                        background: none;
                    }}
        """)
        self.documents_list.currentItemChanged.connect(self.preview_document)
        box_layout = QNoSpacingHBoxLayout()
        self.remove_document_button = QPushButton('- Remove Document')
        self.remove_document_button.clicked.connect(self.remove_document)
        box_layout.addWidget(self.remove_document_button)
        self.add_document_button = QPushButton('+ Add Document')
        self.add_document_button.clicked.connect(self.add_document)
        box_layout.addWidget(self.add_document_button)
        documents_layout.addWidget(self.documents_list)
        documents_layout.addLayout(box_layout)
        self.documents_layout.addLayout(documents_layout)
        # Preview
        self.preview = DocumentViewer(allow_multiple_popouts=True)
        self.documents_layout.addWidget(self.preview)
        self.documents_groupbox.setLayout(self.documents_layout)
        main_layout.addWidget(self.documents_groupbox)

        # People GroupBox
        self.people_groupbox = QGroupBox('People')
        self.people_layout = QHBoxLayout()

        self.for_it_list = QPersonListWidget()
        self.against_it_list = QPersonListWidget()

        self.add_for_it_button = QPushButton('+ Add Person (For it)')
        self.add_for_it_button.clicked.connect(lambda: self.search_person(self.for_it_list))

        self.add_against_it_button = QPushButton('+ Add Person (Against it)')
        self.add_against_it_button.clicked.connect(lambda: self.search_person(self.against_it_list))

        self.for_it_layout = QVBoxLayout()
        self.for_it_layout.addWidget(QLabel('For it'))
        self.for_it_layout.addWidget(self.for_it_list)
        self.for_it_layout.addWidget(self.add_for_it_button)

        self.against_it_layout = QVBoxLayout()
        self.against_it_layout.addWidget(QLabel('Against it'))
        self.against_it_layout.addWidget(self.against_it_list)
        self.against_it_layout.addWidget(self.add_against_it_button)

        self.people_layout.addLayout(self.for_it_layout)
        self.people_layout.addLayout(self.against_it_layout)

        self.people_groupbox.setLayout(self.people_layout)
        main_layout.addWidget(self.people_groupbox)

        self.setLayout(main_layout)

    def add_document(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Add Document", "",
                                                   "PDF Files (*.pdf);;Images (*.png *.jpg *.jpeg);;Videos (*.mp4);;Text Files (*.txt)",
                                                   options=options)
        if file_name:
            self.documents_list.addItem(file_name)
            self.documents_list.setCurrentRow(self.documents_list.count() - 1)
            #QMessageBox.information(self, 'File Types Supported',
            #                        'This application supports the following file types for preview:\nPDF, Images, Videos, ASCII Text Files')

    def remove_document(self):
        current_item = self.documents_list.currentItem()
        if current_item:
            self.documents_list.takeItem(self.documents_list.row(current_item))

    def preview_document(self, current, previous):
        self.preview.preview_document(current.text() if current else "")

    def search_person(self, list_widget):
        dialog = QDialog(self)
        dialog.setWindowTitle('Search Person')

        dialog_layout = QVBoxLayout(dialog)

        search_input = QLineEdit(dialog)
        search_input.setPlaceholderText('Search for a person...')
        dialog_layout.addWidget(search_input)

        search_results = QListWidget(dialog)
        dialog_layout.addWidget(search_results)

        # Populate with existing people for demonstration (in practice, fetch from a database or other source)
        for i in range(10):
            search_results.addItem(f'Person {i + 1}')

        def add_selected_person():
            selected_items = search_results.selectedItems()
            if selected_items:
                for item in selected_items:
                    list_widget.add_person(item.text(), 'Representation')
                dialog.accept()

        select_button = QPushButton('Select', dialog)
        select_button.clicked.connect(add_selected_person)
        dialog_layout.addWidget(select_button)

        create_new_person_button = QPushButton('Create New Person', dialog)
        create_new_person_button.clicked.connect(lambda: self.create_new_person(list_widget))
        dialog_layout.addWidget(create_new_person_button)

        dialog.exec_()

    def create_new_person(self, list_widget):
        dialog = QDialog(self)
        dialog.setWindowTitle('Create New Person')

        scroll_area = QScrollArea(dialog)
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget(scroll_area)
        scroll_layout = QVBoxLayout(scroll_content)

        form_layout = QFormLayout()

        name_input = QLineEdit()
        address_input = QLineEdit()
        gender_combo = QComboBox()
        gender_combo.addItems(['Male', 'Female', 'Other'])
        birthdate_input = QDateEdit()
        birthdate_input.setCalendarPopup(True)
        birthdate_input.setDate(QDate.currentDate())
        contact_input = QLineEdit()
        picture_input = QPushButton('Upload Picture')

        # Placeholder for picture path
        self.picture_path = ""

        picture_input.clicked.connect(lambda: self.upload_picture(dialog))

        form_layout.addRow('Name:', name_input)
        form_layout.addRow('Address:', address_input)
        form_layout.addRow('Gender:', gender_combo)
        form_layout.addRow('Birthdate:', birthdate_input)
        form_layout.addRow('Contact:', contact_input)
        form_layout.addRow('Picture:', picture_input)

        scroll_layout.addLayout(form_layout)
        scroll_area.setWidget(scroll_content)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton('OK', dialog)
        cancel_button = QPushButton('Cancel', dialog)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)

        ok_button.clicked.connect(
            lambda: self.on_create_person_ok(dialog, name_input, address_input, gender_combo, birthdate_input,
                                             contact_input, list_widget))
        cancel_button.clicked.connect(dialog.reject)

        main_layout = QVBoxLayout(dialog)
        main_layout.addWidget(scroll_area)
        main_layout.addLayout(buttons_layout)

        dialog.exec_()

    def upload_picture(self, dialog):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(dialog, "Upload Picture", "", "Image Files (*.png *.jpg *.jpeg)",
                                                   options=options)
        if file_name:
            self.picture_path = file_name

    def on_create_person_ok(self, dialog, name_input, address_input, gender_combo, birthdate_input, contact_input,
                            list_widget):
        name = name_input.text()
        address = address_input.text()
        gender = gender_combo.currentText()
        birthdate = birthdate_input.date().toString(Qt.ISODate)
        contact = contact_input.text()
        picture = self.picture_path

        if name and address:
            # Here you can save the new person details to a database or a data structure
            list_widget.add_person(name, 'Representation')
            dialog.accept()
        else:
            QMessageBox.warning(self, 'Error', 'Name and address are required.')

    def validate_address(self, address):
        # Placeholder for address validation logic
        # This should be replaced with actual API call to validate address
        return True


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = NewCaseFrame()
#     window.show()
#     app.exec()
#     print(window.notes_text.get_bullet_points())
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize


class QEditableGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setLayout(QVBoxLayout())
        self.is_editing = False

        # Create the edit button
        self.edit_button = QPushButton(self)
        self.edit_button.setIcon(QPixmap("assets/edit.svg"))
        self.edit_button.setIconSize(QSize(16, 16))
        self.edit_button.setFixedSize(20, 20)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
            }
        """)

    def toggle_edit_mode(self):
        self.is_editing = not self.is_editing
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QLineEdit, QTextEdit)):
                widget.setReadOnly(not self.is_editing)
        self.edit_button.setIcon(QPixmap("assets/save.svg") if self.is_editing else QPixmap("assets/edit.svg"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.edit_button.move(self.width() - self.edit_button.width() - 5, 0)


class EditCaseFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.max_editors = 3
        self.current_editors = 0
        main_layout = QVBoxLayout()

        # Title
        self.title_label = QLabel('Title')
        self.title_label.setStyleSheet("font-size: 24px; height: 40px;")
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText('Title')
        self.title_input.setStyleSheet("font-size: 24px; height: 40px;")
        self.title_input.hide()

        self.title_edit_button = QPushButton('Edit')
        self.title_edit_button.clicked.connect(self.toggle_edit_title)

        title_layout = QHBoxLayout()
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.title_input)
        title_layout.addWidget(self.title_edit_button)
        main_layout.addLayout(title_layout)

        # Description GroupBox
        self.description_groupbox = QEditableGroupBox('Description')
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_groupbox.layout().addWidget(self.description_text)
        main_layout.addWidget(self.description_groupbox)

        # Notes GroupBox
        self.notes_groupbox = QEditableGroupBox('Notes')
        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_groupbox.layout().addWidget(self.notes_text)
        main_layout.addWidget(self.notes_groupbox)

        # Documents GroupBox
        self.documents_groupbox = QEditableGroupBox('Documents')
        self.documents_layout = QVBoxLayout()
        self.documents_list = QListWidget()
        self.documents_list.currentItemChanged.connect(self.preview_document)
        self.add_document_button = QPushButton('+ Add Document')
        self.add_document_button.clicked.connect(self.add_document)
        self.documents_layout.addWidget(self.documents_list)
        self.documents_layout.addWidget(self.add_document_button)
        self.documents_groupbox.layout().addLayout(self.documents_layout)
        main_layout.addWidget(self.documents_groupbox)

        # People GroupBox
        self.people_groupbox = QEditableGroupBox('People')
        self.people_layout = QVBoxLayout()
        self.add_person_button = QPushButton('+ Add Person')
        self.add_person_button.clicked.connect(self.add_person)
        self.people_layout.addWidget(self.add_person_button)
        self.people_groupbox.layout().addLayout(self.people_layout)
        main_layout.addWidget(self.people_groupbox)

        self.setLayout(main_layout)

    def toggle_edit_title(self):
        if self.title_input.isVisible():
            self.title_label.setText(self.title_input.text())
            self.title_input.hide()
            self.title_label.show()
            self.current_editors -= 1
        else:
            if self.current_editors < self.max_editors:
                self.title_input.setText(self.title_label.text())
                self.title_label.hide()
                self.title_input.show()
                self.current_editors += 1

    def add_document(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Add Document", "",
                                                   "PDF Files (*.pdf);;Images (*.png *.jpg *.jpeg);;Videos (*.mp4);;Text Files (*.txt)",
                                                   options=options)
        if file_name:
            self.documents_list.addItem(file_name)
            self.documents_list.setCurrentRow(self.documents_list.count() - 1)

    def preview_document(self, current, previous):
        if current:
            self.preview.preview_document(current.text())

    def add_person(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Add Person')

        dialog_layout = QFormLayout(dialog)

        name_input = QLineEdit(dialog)
        address_input = QLineEdit(dialog)
        representation_combo = QComboBox(dialog)
        representation_combo.addItems(['Self-represented', 'External'])

        dialog_layout.addRow('Name:', name_input)
        dialog_layout.addRow('Address:', address_input)
        dialog_layout.addRow('Representation:', representation_combo)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton('OK', dialog)
        cancel_button = QPushButton('Cancel', dialog)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)

        dialog_layout.addRow(buttons_layout)

        ok_button.clicked.connect(
            lambda: self.on_add_person_ok(dialog, name_input, address_input, representation_combo))
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec_()

    def on_add_person_ok(self, dialog, name_input, address_input, representation_combo):
        name = name_input.text()
        address = address_input.text()
        representation = representation_combo.currentText()

        if name and self.validate_address(address):
            person_widget = QWidget()
            person_layout = QHBoxLayout()

            name_label = QLabel(name)
            address_label = QLabel(address)
            representation_label = QLabel(representation)

            remove_button = QPushButton('Remove')
            remove_button.clicked.connect(lambda: self.remove_person(person_widget))

            person_layout.addWidget(name_label)
            person_layout.addWidget(address_label)
            person_layout.addWidget(representation_label)
            person_layout.addWidget(remove_button)
            person_widget.setLayout(person_layout)

            self.people_layout.addWidget(person_widget)
            dialog.accept()
        else:
            QMessageBox.warning(self, 'Error', 'Invalid name or address')

    def validate_address(self, address):
        return True

    def remove_person(self, widget):
        widget.setParent(None)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EditCaseFrame()
    window.show()
    app.exec()
