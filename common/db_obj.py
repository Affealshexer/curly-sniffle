import time

from aplustools.io.environment import auto_repr as _auto_repr
from .db import DatabaseAccess as _DatabaseAccess


@_auto_repr
class Document:
    def __init__(self, document_nb: int, _main_contact: _DatabaseAccess):
        self.document_nb = document_nb
        self._main_contact = _main_contact
        self.snap_shot = {
            "document_name": "",
            "document_description": "",
            "document_notes": [""],
            # "document_path": "",
            "cases": []
        }
        self.edit_mode_engaged = False
        self.cb = False
        self.update()

    @property
    def document_name(self):
        return

    @document_name.setter
    def document_name(self, value: str):
        if not self.edit_mode_engaged:
            raise ValueError("Please engage edit mode first before trying to change any values.")

        pass  # Change value
        self.snap_shot["document_name"] = value

    @property
    def cases(self):
        return self._main_contact.get_documents(self.document_nb, "cases")[0]

    def update(self):
        pass  # Refresh snapshot
        self.snap_shot = {k: v for k, (v,) in zip(self.snap_shot.keys(), self._main_contact.get_documents(self.document_nb, *self.snap_shot.keys()))}

    def _callback(self):
        self.cb = True

    def edit(self):
        self.edit_mode_engaged = True
        self._main_contact.edit_lock_manager.stage_changes(self.document_nb, "Documents", self._callback)
        while not self.cb:
            time.sleep(0.1)

    def finalize_edit(self):
        self.edit_mode_engaged = False
        self._main_contact.edit_lock_manager.release_edit_lock(self.document_nb, "Documents")
        snap_copy = self.snap_shot.copy()
        del snap_copy["cases"]
        snap_copy["document_notes"] = '\n'.join(snap_copy["document_notes"])
        print(snap_copy)
        self._main_contact.update_documents(self.document_nb, **snap_copy)
        self.cb = False


@_auto_repr
class Case:
    def __init__(self, case_nb: int, _main_contact: _DatabaseAccess):
        self.case_nb = case_nb
        self._main_contact = _main_contact

    @property
    def case_name(self):
        return self._main_contact.get_cases(self.case_nb, "case_name")[0][0]

    @property
    def persons(self):
        person_nbs = self._main_contact.get_cases(self.case_nb, "persons")[0]
        return [Person(person_nb, self._main_contact) for person_nb in person_nbs]

    @property
    def documents(self):
        document_nbs = self._main_contact.get_cases(self.case_nb, "documents")[0]
        return [Document(document_nb, self._main_contact) for document_nb in document_nbs]


@_auto_repr
class Person:
    def __init__(self, person_nb: int, _main_contact: _DatabaseAccess):
        self.person_nb = person_nb
        self._main_contact = _main_contact

    @property
    def first_name(self):
        return self._main_contact.get_persons(self.person_nb, "first_name")[0][0]

    @property
    def last_name(self):
        return self._main_contact.get_persons(self.person_nb, "last_name")[0][0]

    @property
    def address(self):
        return self._main_contact.get_persons(self.person_nb, "address")[0][0]

    @property
    def birth_date(self):
        return self._main_contact.get_persons(self.person_nb, "birth_date")[0][0]

    @property
    def contact_info(self):
        return self._main_contact.get_persons(self.person_nb, "contact_info")[0][0]

    @property
    def can_be_lawyer(self):
        return self._main_contact.get_persons(self.person_nb, "can_be_lawyer")[0][0] == 1

    @property
    def cases(self):
        case_nbs = self._main_contact.get_persons(self.person_nb, "cases")[0]
        return [Case(case_nb, self._main_contact) for case_nb in case_nbs]


if __name__ == "__main__":
    from db import DB_PATH
    db = _DatabaseAccess(DB_PATH)
    print(Document(1, db))
    input()

    person = Person(22, db)
    print(person.first_name)
    print(person.can_be_lawyer)
    cases = person.cases
    print(cases)
    print(cases[0].documents[0].cases[0].persons)
