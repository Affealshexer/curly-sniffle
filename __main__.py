from common.db import DatabaseAccess, DB_PATH
from common.db_obj import Person
from datetime import datetime
from PySide6.QtWidgets import QApplication
import sys
from common.main_gui import DataNotifier, ClientLawyerGUIOld
from PySide6.QtCore import QTimer


if __name__ == "__main__":
    from common.db import DB_PATH, DatabaseAccess as _DatabaseAccess
    from common.db_obj import Document
    db = _DatabaseAccess(DB_PATH)
    print(Document(1, db))

app = QApplication(sys.argv)

db_access = DatabaseAccess(DB_PATH)
client = Person(22, db_access)
notifier = DataNotifier(db_access)

gui = ClientLawyerGUIOld(client)

notifier.dataChanged.connect(gui.update_data)

timer = QTimer()
timer.timeout.connect(notifier.poll_for_changes)
timer.start(1000)  # Poll every second

gui.show()
app.exec()


if __name__ == "__main__":
    db = DatabaseAccess(DB_PATH)
    print(db.get_persons(22, "last_name", "first_name", "birth_date", "cases", "can_be_lawyer", "notes"))
    print(db.get_cases(1, "case_name", "persons", "documents"))
    print(db.get_documents(1, "cases", "document_name", "document_description"))
    db.update_documents(1, cases=[1,])
    db.update_documents(2, cases=[2])
    print(db.get_documents(1, "cases"))
    from common.db_obj import Document
    docu = Document(1, db)
    print(docu)
    docu.edit()
    docu.document_name = "MYYY CASEEEEyy"
    docu.finalize_edit()
    print(docu)


from common.def_gui import NewCaseFrame
if __name__ == "__main__":  # How to represent the database in the gui
    # For updates, ... we have a dictionary with the numbers as keys
    window = NewCaseFrame(db)
    window.show()
    app.exec()
    print(window.notes_text.get_bullet_points())
