from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QLabel, QLineEdit,
                               QHBoxLayout, QFrame, QScrollArea, QTextEdit, QGroupBox,
                               QListWidget, QFileDialog, QDialog, QDialogButtonBox,
                               QDateEdit, QCheckBox, QMessageBox, QComboBox)
from PySide6.QtGui import QPixmap, QRegularExpressionValidator
from PySide6.QtCore import Qt, Signal, QUrl, QObject, QRegularExpression, QDate, QSize
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from aplustools.io.environment import System, SystemTheme
from aplustools.package.timid import TimidTimer
from typing import Literal
import itertools
import sys
import os
from aplustools.io.gui import QNoSpacingHBoxLayout, QQuickHBoxLayout, QBulletPointTextEdit, QNoSpacingVBoxLayout


class QThemeSensor(QObject):
    themeChanged = Signal()

    def __init__(self):
        super().__init__()
        self.timer = TimidTimer(start_now=False)

        self.system = System.system()
        self.theme = self.system.get_system_theme()

        self.timer.fire(1, self.check_theme)

    def check_theme(self):
        current_theme = self.system.get_system_theme()
        if current_theme != self.theme:
            self.theme = current_theme
            self.themeChanged.emit()


global_theme_sensor = QThemeSensor()


class SmartTextEdit(QTextEdit):
    def __init__(self, max_height=100, parent=None):
        super().__init__(parent)
        self.max_height = max_height
        self.textChanged.connect(self.adjustHeight)

    def adjustHeight(self):
        doc_height = self.document().size().height()
        if doc_height > self.max_height:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setFixedHeight(self.max_height)
        else:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setFixedHeight(int(doc_height))

    def showEvent(self, event):
        super().showEvent(event)
        self.adjustHeight()

    def text(self) -> str:
        return self.toPlainText()


class QBaseDocumentViewerControls(QWidget):
    fit_changed = Signal(str)
    pop_changed = Signal(str)

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
        self.fit_changed.emit(self.fit_emit)

    def change_pop(self):
        pop = next(self.popout_iterator)
        self.pop_button.setIcon(QPixmap(pop))
        self.pop_emit = os.path.basename(pop).split(".")[0]
        self.pop_changed.emit(self.pop_emit)


class QDocumentViewer(QBaseDocumentViewerControls):
    def __init__(self, parent=None, allow_multiple_popouts: bool = False):
        super().__init__(parent)
        self.theme = global_theme_sensor.theme
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
        self.pop_changed.connect(self.pop_out_in)
        self.wins = []
        self.allow_multiple_popouts = allow_multiple_popouts
        self.fit_changed.connect(self.fit_content)
        self.FIT_WINDOW.connect(self.fit_window)
        global_theme_sensor.themeChanged.connect(self.reapply_theme)

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
            win = QDocumentViewer()
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
        self.pop_changed.emit(self.pop_emit)

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
        self.theme = global_theme_sensor.theme
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


class QPersonWidget(QFrame):
    clicked = Signal()
    selected = Signal()

    def __init__(self, name: str, representative: str,
                 representation_type: Literal["self_represented", "extern", "homegrown"], parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.theme = global_theme_sensor.theme
        self.setStyleSheet(f"""
            QPersonWidget {{
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }}
            QPushButton {{
                border: 1px solid #ccc;
                border-radius: 5px;
            }}""")
        self.isSelected = False

        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(9)

        self.name_label = QLabel(name)
        self.representation_label = QLabel(representative if representative else representation_type.replace("_", " ").title())

        remove_button = QPushButton('Remove')
        remove_button.setFixedSize(60, 25)
        remove_button.clicked.connect(self.remove_person)

        layout.addWidget(self.name_label)
        layout.addWidget(self.representation_label)
        layout.addWidget(remove_button)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.setLayout(layout)
        global_theme_sensor.themeChanged.connect(self.reapply_theme)

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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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

    def reapply_theme(self):
        self.theme = global_theme_sensor.theme
        pass  # Reapply themes


class QPersonListWidget(QWidget):
    personActivated = Signal(QPersonWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.selected_widget = None

    def add_person(self,  name: str, representative: str,
                   representation_type: Literal["self_represented", "extern", "homegrown"]):
        person_widget = QPersonWidget(name, representative, representation_type)
        person_widget.clicked.connect(lambda: self.on_person_clicked(person_widget))
        person_widget.selected.connect(lambda: self.on_person_selected(person_widget))
        self.layout.addWidget(person_widget)

    def on_person_selected(self, person_widget: QPersonWidget):
        if self.selected_widget and self.selected_widget != person_widget:
            self.selected_widget.deselect()
        self.selected_widget = person_widget

    def on_person_clicked(self, person_widget: QPersonWidget):
        self.personActivated.emit(person_widget)


class AddPersonDialog(QDialog):  # Quick and dirty
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Person")
        self.resize(1000, 600)

        main_layout = QVBoxLayout()
        self.setStyleSheet("background: white;")

        # Top space
        top_space_layout = QQuickHBoxLayout(9, (0, 0, 0, 0))
        image_label = QLabel()
        image_label.setPixmap(QPixmap("assets/unknown_person.jpg").scaled(200, int(200 * 1.1)))
        image_label.setFixedSize(200, int(200 * 1.1))
        image_label.setStyleSheet("""
            QLabel {
                border-radius: 10px;  /* Slightly rounded corners */
            }
        """)
        top_space_layout.addWidget(image_label)

        main_info_layout = QNoSpacingVBoxLayout()
        name_info_layout = QQuickHBoxLayout(0, (0, 0, 0, 0))
        self.first_name_edit = QLineEdit()
        self.first_name_edit.setPlaceholderText("First Name")
        self.first_name_edit.setStyleSheet("font-size: 24px; height: 40px; background-color: palette(base);")
        self.last_name_edit = QLineEdit()
        self.last_name_edit.setPlaceholderText("Last Name")
        self.last_name_edit.setStyleSheet("font-size: 24px; height: 40px; background-color: palette(base);")
        name_info_layout.addWidget(self.first_name_edit)
        name_info_layout.addWidget(self.last_name_edit)
        main_info_layout.addLayout(name_info_layout)

        small_info_layout = QQuickHBoxLayout(0, (0, 0, 0, 0))
        self.birthday_edit = QDateEdit()
        self.birthday_edit.setCalendarPopup(True)
        self.birthday_edit.setDate(QDate.currentDate())
        small_info_layout.addWidget(self.birthday_edit)
        self.lawyer_checkbox = QCheckBox("Can be a lawyer")
        small_info_layout.addWidget(self.lawyer_checkbox)
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(['Male', 'Female', 'Other'])
        small_info_layout.addWidget(self.gender_combo)

        small_info_layout_2 = QQuickHBoxLayout(0, (0, 0, 0, 0))
        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("Address")
        small_info_layout_2.addWidget(self.address_edit)
        self.contact_method_edit = QLineEdit()
        self.contact_method_edit.setPlaceholderText("Enter a valid email")
        self.contact_method_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"[^@]+@[^@]+\.[^@]+")))
        small_info_layout_2.addWidget(self.contact_method_edit)
        main_info_layout.addLayout(small_info_layout)
        main_info_layout.addLayout(small_info_layout_2)
        top_space_layout.addLayout(main_info_layout)
        main_layout.addLayout(top_space_layout)

        extra_info_layout = QHBoxLayout()
        self.description_edit = QTextEdit("Description")
        self.notes_edit = QBulletPointTextEdit()
        extra_info_layout.addWidget(self.description_edit)
        extra_info_layout.addWidget(self.notes_edit)
        main_layout.addLayout(extra_info_layout)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)


class NewCaseFrame(QFrame):
    saveClicked = Signal()

    def __init__(self, _db_access, parent=None):
        ########## TEMP ##########
        self._db_access = _db_access
        ########## TEMP ##########
        super().__init__(parent)
        main_layout = QVBoxLayout()
        self.theme = global_theme_sensor.theme

        # Title input
        title_layout = QNoSpacingHBoxLayout()
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText("Title")
        self.title_input.setStyleSheet("font-size: 24px; height: 40px; background-color: palette(base);")
        save_case_button = QPushButton("Create Case")
        save_case_button.clicked.connect(self.saveClicked.emit)
        title_layout.addWidget(self.title_input)
        title_layout.addWidget(save_case_button)
        main_layout.addLayout(title_layout)

        # [Description] & Notes
        extra_info_layout = QQuickHBoxLayout(9, (0, 0, 0, 0))
        description_groupbox = QGroupBox("Description")
        self.description_text = QTextEdit()
        self.description_text.setStyleSheet("border-radius: 10px; background-color: palette(base);")
        description_layout = QVBoxLayout()
        description_layout.addWidget(self.description_text)
        description_groupbox.setLayout(description_layout)
        extra_info_layout.addWidget(description_groupbox)
        # Description & [Notes]
        notes_groupbox = QGroupBox("Notes")
        self.notes_text = QBulletPointTextEdit()
        self.notes_text.setStyleSheet("border-radius: 10px; background-color: palette(base);")
        notes_layout = QVBoxLayout()
        notes_layout.addWidget(self.notes_text)
        notes_groupbox.setLayout(notes_layout)
        extra_info_layout.addWidget(notes_groupbox)
        main_layout.addLayout(extra_info_layout)

        # Documents
        document_layout = QHBoxLayout()
        document_groupbox = QGroupBox("Documents")
        document_selection_layout = QVBoxLayout()
        self.documents_list = QListWidget()
        self.documents_list.setStyleSheet(f"""
            QListWidget {{
                border-radius: 10px;
                background-color: palette(base);
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
        self.documents_list.currentItemChanged.connect(self.preview_document)

        box_layout = QNoSpacingHBoxLayout()
        remove_document_button = QPushButton("- Remove Document")
        remove_document_button.clicked.connect(self.remove_document)
        box_layout.addWidget(remove_document_button)
        add_document_button = QPushButton("+ Add Document")
        add_document_button.clicked.connect(self.add_document)
        box_layout.addWidget(add_document_button)
        document_selection_layout.addWidget(self.documents_list)
        document_selection_layout.addLayout(box_layout)
        document_layout.addLayout(document_selection_layout)
        # Preview
        self.preview = QDocumentViewer(allow_multiple_popouts=True)
        document_layout.addWidget(self.preview)
        document_groupbox.setLayout(document_layout)
        main_layout.addWidget(document_groupbox)

        # People selection
        people_groupbox = QGroupBox("People")
        people_layout = QHBoxLayout()

        self.for_it_list = QPersonListWidget()
        self.against_it_list = QPersonListWidget()

        add_for_it_button = QPushButton("+ Add Person (For it)")
        add_for_it_button.clicked.connect(lambda: self.search_person(self.for_it_list))

        add_against_it_button = QPushButton("+ Add Person (Against it)")
        add_against_it_button.clicked.connect(lambda: self.search_person(self.against_it_list))

        for_it_layout = QVBoxLayout()
        for_it_layout.addWidget(QLabel("For it"))
        for_it_layout.addWidget(self.for_it_list)
        for_it_layout.addWidget(add_for_it_button)

        against_it_layout = QVBoxLayout()
        against_it_layout.addWidget(QLabel("Against it"))
        against_it_layout.addWidget(self.against_it_list)
        against_it_layout.addWidget(add_against_it_button)

        people_layout.addLayout(for_it_layout)
        people_layout.addLayout(against_it_layout)

        people_groupbox.setLayout(people_layout)
        main_layout.addWidget(people_groupbox)

        self.setLayout(main_layout)
        global_theme_sensor.themeChanged.connect(self.reapply_theme)

    def add_document(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "Add Document(s)", "",
                                                    "PDF Files (*.pdf);;"
                                                    "Images (*.png *.jpg *.jpeg);;"
                                                    "Videos (*.mp4 *.mov);;"
                                                    "All Files (*.*)")

        if file_names:
            for file_name in file_names:
                self.documents_list.addItem(file_name)
            self.documents_list.setCurrentRow(self.documents_list.count() - 1)

    def remove_document(self):
        current_item = self.documents_list.currentItem()
        if current_item:
            self.documents_list.takeItem(self.documents_list.row(current_item))

    def preview_document(self, current, _):
        self.preview.preview_document(current.text() if current is not None else "")

    def _refresh_search_results(self, search, list_widget):
        list_widget.clear()
        # Populate with existing people for demonstration (in practice, fetch from a database or other source)
        for i in self._db_access.restricted_search(search.text(), "user"):
            (first_name,), (last_name,) = self._db_access.get_persons(i[0], "first_name", "last_name")
            list_widget.addItem(f"{first_name} {last_name}")

    def search_person(self, list_widget: QPersonListWidget):
        dialog = QDialog(self)
        dialog.setWindowTitle('Search Person')

        dialog_layout = QVBoxLayout(dialog)


        search_results = QListWidget(dialog)
        dialog_layout.addWidget(search_results)

        # Populate with existing people for demonstration (in practice, fetch from a database or other source)
        for i in self._db_access.restricted_search("", "user"):
            (first_name,), (last_name,) = self._db_access.get_persons(i[0], "first_name", "last_name")
            search_results.addItem(f"{first_name} {last_name}")

        search_input = QLineEdit(dialog)
        search_input.setPlaceholderText('Search for a person...')
        search_input.textChanged.connect(lambda: self._refresh_search_results(search_input, search_results))
        dialog_layout.addWidget(search_input)

        def add_selected_person():
            selected_items = search_results.selectedItems()
            if selected_items:
                for item in selected_items:
                    list_widget.add_person(item.text(), 'Mike Meyers', "homegrown")
                dialog.accept()

        select_button = QPushButton('Select', dialog)
        select_button.clicked.connect(add_selected_person)
        dialog_layout.addWidget(select_button)

        create_new_person_button = QPushButton('Create New Person', dialog)
        create_new_person_button.clicked.connect(lambda: self.create_new_person(list_widget))
        dialog_layout.addWidget(create_new_person_button)

        dialog.exec_()

    def create_new_person(self, list_widget):
        dialog = AddPersonDialog(self)

        dialog.button_box.accepted.connect(
            lambda: self.on_create_person_ok(dialog, dialog.first_name_edit, dialog.last_name_edit,
                                             dialog.address_edit, dialog.gender_combo,
                                             dialog.birthday_edit, dialog.contact_method_edit)
        )
        dialog.exec()

    def on_create_person_ok(self, dialog, first_name_input, last_name_input, address_input, gender_combo, birthdate_input, contact_input):
        first_name = first_name_input.text()
        last_name = last_name_input.text()
        address = address_input.text()
        gender = gender_combo.currentText()
        birthdate = birthdate_input.date().toString(Qt.ISODate)
        contact = contact_input.text()

        if first_name and address:
            # Here you can save the new person details to a database or a data structure
            dialog.accept()
        else:
            QMessageBox.warning(self, 'Error', 'Name and address are required.')

    def reapply_theme(self):
        self.theme = global_theme_sensor.theme
        self.title_input.setStyleSheet("font-size: 24px; height: 40px; background-color: palette(base);")
        self.description_text.setStyleSheet("border-radius: 10px; background-color: palette(base);")
        self.notes_text.setStyleSheet("border-radius: 10px; background-color: palette(base);")
        self.documents_list.setStyleSheet(f"""
                    QListWidget {{
                        border-radius: 10px;
                        background-color: palette(base);
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
    pass


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = NewCaseFrame()
    window.show()
    app.exec()
    print(window.notes_text.get_bullet_points())
