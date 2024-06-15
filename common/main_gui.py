from PySide6.QtCore import QObject, Signal, Slot, QTimer, Qt
from PySide6.QtWidgets import (QApplication, QLabel,
                               QVBoxLayout, QWidget,
                               QMainWindow, QStackedLayout,
                               QPushButton, QLineEdit, QListWidget,
                               QFrame, QHBoxLayout, QMessageBox, QTextEdit)
from aplustools.io.gui import QNoSpacingHBoxLayout, QNoSpacingVBoxLayout, QCenteredLayout
import json
import sys
import os
import io


from .db import CHANGES_LOG_FILE as _CHANGES_LOG_FILE


class DataNotifier(QObject):
    dataChanged = Signal()

    def __init__(self, db_access):
        super().__init__()
        self.db_access = db_access
        self.last_position = 0

    def poll_for_changes(self):
        if os.path.exists(_CHANGES_LOG_FILE):
            with open(_CHANGES_LOG_FILE, 'r') as log_file:
                log_file.seek(0, io.SEEK_END)  # log_file.seek(self.last_position)
                changes = self.last_position != log_file.tell()  # changes = log_file.readlines()
                self.last_position = log_file.tell()
            if changes:  # Close the file as soon as possible
                self.dataChanged.emit()


class ClientLawyerGUIOld(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.label = QLabel(self)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.update_data()

    @Slot()
    def update_data(self):
        data = f"{self.client.first_name} {self.client.last_name}"
        self.label.setText(data)


class ClientLawyerGUI(QWidget):
    def __init__(self, window_title: str):
        super().__init__()
        self.setWindowTitle(window_title)
        self.setGeometry(100, 100, 1200, 800)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.stack_layout = QStackedLayout()
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(self.width() // 3)  # 300

        self.sidebar_layout = QVBoxLayout()
        self.new_case_button = QPushButton("New Case")
        self.new_case_button.clicked.connect(self.create_new_case)

        self.search_input = SmartTextEdit()
        self.search_input.setPlaceholderText("Search for People, Cases, or Documents")
        self.search_input.textChanged.connect(self.search_data)

        self.search_results = QListWidget()
        self.search_results.itemClicked.connect(self.display_info)

        self.sidebar_layout.addWidget(self.search_input)
        self.sidebar_layout.addWidget(self.new_case_button)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.sidebar_layout.addWidget(line)
        self.sidebar_layout.addWidget(self.search_results)

        self.sidebar.setLayout(self.sidebar_layout)

        self.main_frame = QFrame()
        self.main_layout = QNoSpacingVBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setEnabled(False)
        back_layout = QNoSpacingHBoxLayout()
        back_layout.addWidget(self.back_button)
        back_layout.addStretch()
        self.back_frame = QFrame()
        self.back_frame.setLayout(back_layout)
        self.info_display = QLabel("Select an item to see details here")
        self.info_display.setWordWrap(True)
        self.main_layout.addWidget(self.info_display)
        self.main_frame.setLayout(self.main_layout)

        self.stack_layout.addWidget(self.main_frame)

        self.split_layout = QHBoxLayout()
        self.split_layout.addWidget(self.sidebar)
        self.split_layout.addLayout(self.stack_layout)

        self.main_container = QWidget()
        self.main_container_layout = QVBoxLayout()
        self.main_container_layout.addLayout(self.split_layout)
        self.main_container.setLayout(self.main_container_layout)

        self.layout.addWidget(self.main_container)

        self.history = []

        self.search_data()

        self.new_case_frame = QFrame()
        self.new_case_layout = QVBoxLayout()
        # self.new_case_layout.addWidget(self.back_frame)
        self.new_case_layout.addWidget(QLabel("Enter new case details:"))

        id_input = QLineEdit()
        id_input.setPlaceholderText("Case ID")
        name_input = QLineEdit()
        name_input.setPlaceholderText("Case Name")
        details_input = QLineEdit()
        details_input.setPlaceholderText("Details")

        self.new_case_layout.addWidget(id_input)
        self.new_case_layout.addWidget(name_input)
        self.new_case_layout.addWidget(details_input)

        save_button = QPushButton("Save Case")
        save_button.clicked.connect(lambda: self.save_case(id_input.text(), name_input.text(), details_input.text()))
        self.new_case_layout.addWidget(save_button)

        self.new_case_frame.setLayout(self.new_case_layout)
        self.stack_layout.addWidget(self.new_case_frame)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sidebar.setFixedWidth(self.width() // 3)

    def search_data(self):
        query = self.search_input.text()
        self.search_results.clear()

        # For demonstration purposes, we add mock search results
        mock_results = ["Person: John Doe", "Case: Case A", "Document: Document 1"]
        for result in mock_results:
            self.search_results.addItem(result)

    def display_info(self, item):
        selected_text = item.text()

        if selected_text.startswith("Person:"):
            details = f"{selected_text}\nRole: Lawyer\nCases: Case A, Case B"
            related_cases = ["Case A", "Case B"]
        elif selected_text.startswith("Case:"):
            details = f"{selected_text}\nParticipants: John Doe, Jane Smith\nDocuments: Document 1, Document 2"
            related_cases = ["John Doe", "Jane Smith"]
        elif selected_text.startswith("Document:"):
            details = f"{selected_text}\nAssociated Case: Case A\nParticipants: John Doe, Jane Smith"
            related_cases = ["John Doe", "Case A"]
        else:
            details = "No details available."
            related_cases = []

        info_frame = QFrame()
        info_layout = QVBoxLayout()
        info_layout.addWidget(self.back_frame)
        info_label = QLabel(details)
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)

        related_list = QListWidget()
        for related in related_cases:
            related_list.addItem(related)
        related_list.itemClicked.connect(self.display_related_info)
        info_layout.addWidget(QLabel("Related:"))
        info_layout.addWidget(related_list)

        info_frame.setLayout(info_layout)
        self.stack_layout.addWidget(info_frame)
        self.stack_layout.setCurrentWidget(info_frame)

        self.history = [self.main_frame, info_frame]
        self.back_button.setEnabled(True)

    def display_related_info(self, item):
        selected_text = item.text()

        if selected_text.startswith("Case"):
            details = f"Details about {selected_text}"
        else:
            details = f"Details about participant {selected_text}"

        related_frame = QFrame()
        related_layout = QVBoxLayout()
        related_label = QLabel(details)
        related_label.setWordWrap(True)
        related_layout.addWidget(related_label)
        related_frame.setLayout(related_layout)

        self.stack_layout.addWidget(related_frame)
        self.stack_layout.setCurrentWidget(related_frame)

        self.history.append(related_frame)

    def create_new_case(self):
        self.search_results.clearSelection()
        self.stack_layout.setCurrentWidget(self.new_case_frame)
        self.history = [self.main_frame, self.new_case_frame]
        self.back_button.setEnabled(True)

    def save_case(self, case_id, case_name, details):
        # For demonstration, we simply show a message box
        QMessageBox.information(self, "Save Case", f"Case ID: {case_id}\nCase Name: {case_name}\nDetails: {details}")

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            self.stack_layout.setCurrentWidget(self.history[-1])
            if len(self.history) == 1:
                self.search_results.clearSelection()
                self.back_button.setEnabled(False)
        else:
            self.back_button.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClientLawyerGUI("Law Firm Data Management")
    window.show()
    sys.exit(app.exec())
