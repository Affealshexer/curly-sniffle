import os.path
from contextlib import contextmanager as _contextmanager
from datetime import datetime as _datetime, date as _date
from typing import Literal as _Literal
import sqlite3 as _sqlite3
import random as _random
import json as _json
import time as _time
import os as _os
from .search_engine import SearchEngine
import sqlparse as _sqlparse
import bcrypt
from typing import Literal, List
from threading import Thread, Event


from faker import Faker as _Faker


CWD = os.path.abspath('./data')
LOCK_FILE = _os.path.join(CWD, './.lock')
CHANGES_LOG_FILE = _os.path.join(CWD, './changes_log.json')
DB_PATH = _os.path.join(CWD, './primary.db')


@_contextmanager
def acquire_lock():
    while _os.path.exists(LOCK_FILE):
        _time.sleep(0.1)  # Wait for the lock to be released
    open(LOCK_FILE, 'w').close()  # Create the lock file
    try:
        yield
    finally:
        _os.remove(LOCK_FILE)  # Release the lock file


class EditLockManager:
    """Ensures no two clients are editing the same row in one table"""
    def __init__(self, lock_dir='edit_locks'):
        self.lock_dir = lock_dir
        self.cancel_event = Event()

    def stage_changes(self, where: int, table: Literal["Cases", "CasePeople", "CaseDocuments", "Persons", "Documents"], callback):
        # Write to edit lock file which rows are affected (don't allow one row to be edited by two people at once, wait till it isn't being edited anymore, check every second.)
        # the changes.log file is for the current changes. We also have a lock file for that called
        # changes.lock that means someone is writing if it exists.
        self.cancel_event = Event()
        lock_file_path = os.path.join("./edit_locks", f'edit_lock_{table}_{where}.lock')

        # Reset the cancel event
        self.cancel_event.clear()

        # Thread target function
        def lock_row():
            try:
                # Check if the row is already being edited
                while os.path.exists(lock_file_path):
                    if self.cancel_event.is_set():
                        print("Edit operation canceled.")
                        return
                    print(f"Row {where} is currently being edited. Waiting...")
                    _time.sleep(1)  # Wait for 1 second before checking again

                # Create a lock file to indicate this row is being edited
                with open(lock_file_path, 'w') as lock_file:
                    lock_file.write(f'Editing {table} where ID is {where}\n')

                print(f"Row {where} is now locked for editing.")
                callback()

            finally:
                if self.cancel_event.is_set() and os.path.exists(lock_file_path):
                    os.remove(lock_file_path)
                    print(f"Released lock for row {where} due to cancellation.")

        # Start the thread
        self.lock_thread = Thread(target=lock_row)
        self.lock_thread.start()

    def release_edit_lock(self, where: int, table: Literal["Cases", "CasePeople", "CaseDocuments", "Persons", "Documents"]):
        lock_file_path = os.path.join(self.lock_dir, f'edit_lock_{table}_{where}.lock')
        if os.path.exists(lock_file_path):
            os.remove(lock_file_path)
            print(f"Released lock for row {where} on {table}.")
        else:
            print(f"No lock found for row {where} on {table}.")

    def cancel_edit(self):
        self.cancel_event.set()
        if self.lock_thread.is_alive():
            self.lock_thread.join()
            print("Edit operation canceled and thread joined.")


class DatabaseAccess:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = _sqlite3.connect(self.db_path, check_same_thread=False)
        self.search_engine = SearchEngine()
        self.edit_lock_manager = EditLockManager()

        if (not _os.path.exists(db_path)) or _os.path.getsize(db_path) == 0:
            self.setup_database()

    def _query(self, sql, params=()):
        with acquire_lock():  # Don't want to read incomplete data.
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()

    def _execute(self, sql, params=()):
        with acquire_lock():
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            self._log_changes(sql, params)

    def _execute_many(self, sql, params=((),)):
        with acquire_lock():
            cursor = self.conn.cursor()
            for param in params:
                cursor.execute(sql, param)
                self._log_changes(sql, param)
            self.conn.commit()

    @staticmethod
    def _get_affected_tables(query):
        parsed = _sqlparse.parse(query)[0]
        statement_type = parsed.get_type()
        tables = []

        if statement_type in ['UPDATE', 'DELETE']:
            for token in parsed.tokens:
                if token.ttype is None and token.is_group:
                    tables.append(token.get_real_name())
                    break
        return tables

    @classmethod
    def _log_changes(cls, sql, params):
        try:
            tables = set(cls._get_affected_tables(sql))
            with open(CHANGES_LOG_FILE, 'a') as log_file:
                # Tabs: Cases; People: NewLine; Document: Space
                for entry, table in zip(("\t", "\n", " "), (("Cases", "CasePeople", "CaseDocuments"),
                                                            ("Persons",), ("Documents",))):
                    if tables.intersection(set(table)):
                        log_file.write(entry)
        except PermissionError as e:
            print(f"PermissionError: {e}")
            cls._log_changes(sql, params)

    def register_user(self, username: str, password: str, role: Literal["Admin", "Manager", "Viewer"]):
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            self._execute('''
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?);
            ''', (username, password_hash, role))
            print(f"User {username} registered successfully as {role}.")
        except _sqlite3.IntegrityError:
            print("Error: Username already exists.")

    def authenticate_user(self, username: str, password: str):
        result = self._query('''
        SELECT password_hash, role FROM users WHERE username = ?;
        ''', (username,))[0]
        if result:
            password_hash, role = result
            if bcrypt.checkpw(password.encode('utf-8'), password_hash):
                print(f"Authentication successful. Role: {role}")
                return role
            else:
                print("Authentication failed. Incorrect password.")
                return None
        else:
            print("Authentication failed. User not found.")
            return None

    def setup_database(self):
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS Users (
                nb INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT CHECK(role IN ('Admin', 'Manager', 'Viewer')) NOT NULL
            );""",
            """
            CREATE TABLE IF NOT EXISTS Persons (
                person_nb INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                last_name STRING NOT NULL,
                first_name STRING NOT NULL,
                address STRING NOT NULL,
                birth_date STRING NOT NULL,
                contact_info STRING NOT NULL,
                gender STRING CHECK(gender IN ("Male", "Female", "Other")) NOT NULL,
                description TEXT NOT NULL,
                notes TEXT NOT NULL,
                can_be_lawyer INTEGER NOT NULL
            );""",
            """
            CREATE TABLE IF NOT EXISTS Cases (
                case_nb INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                case_description TEXT NOT NULL,
                case_notes TEXT NOT NULL,
                case_name STRING NOT NULL UNIQUE
            );""",
            """
            CREATE TABLE IF NOT EXISTS CasePeople (
                case_nb INTEGER NOT NULL,
                person_nb INTEGER NOT NULL,
                side INTEGER CHECK(side IN (0, 1)) NOT NULL,
                has_external_lawyer INTEGER NOT NULL DEFAULT 0,
                self_represented INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (case_nb) REFERENCES Cases(case_nb),
                FOREIGN KEY (person_nb) REFERENCES Persons(person_nb),
                PRIMARY KEY (case_nb, person_nb)
            );""",
            """
            CREATE TABLE IF NOT EXISTS Representations (
                case_nb INTEGER,
                person_nb INTEGER,
                lawyer_nb INTEGER,
                side INTEGER CHECK(side IN (0, 1)) NOT NULL,
                FOREIGN KEY (case_nb) REFERENCES Cases(case_nb),
                FOREIGN KEY (person_nb) REFERENCES Persons(person_nb),
                FOREIGN KEY (lawyer_nb) REFERENCES Persons(person_nb),
                PRIMARY KEY (case_nb, person_nb, lawyer_nb)
            );""",
            """
            CREATE TABLE IF NOT EXISTS Documents (
                document_nb INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                document_path STRING NOT NULL,
                document_name STRING NOT NULL,
                document_description TEXT NOT NULL,
                document_notes TEXT NOT NULL,
                archived INTEGER NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS CaseDocuments (
                case_nb INTEGER NOT NULL,
                document_nb INTEGER NOT NULL,
                FOREIGN KEY (case_nb) REFERENCES Cases(case_nb),
                FOREIGN KEY (document_nb) REFERENCES Documents(document_nb),
                PRIMARY KEY (case_nb, document_nb)
            );"""]

        for statement in sql_statements:
            self._execute(statement)
        self.insert_test_data()

    def insert_test_data(self):
        fake = _Faker("de_DE")

        lawyers, persons = [], []
        for nb in range(1, 101):
            is_lawyer = _random.choice([0, 0, 0, 0, 0, 1])
            persons.append((fake.last_name(), fake.name(), fake.address(), fake.date_of_birth(), fake.email(),
                            _random.choice(["Male", "Female", "Other"]), fake.text(), '.\n'.join(fake.texts()), is_lawyer))
            if is_lawyer:
                lawyers.append(nb)
        self._execute_many('INSERT INTO Persons (last_name, first_name, address, birth_date, contact_info, gender, description, notes, can_be_lawyer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', persons)

        for case_nb in range(1, 21):
            case_name = f"Case {case_nb}"
            self._execute("INSERT INTO Cases (case_name, case_description, case_notes) VALUES (?, ?, ?)", (case_name, fake.text(), '\n'.join(fake.texts())))
            person_nbs = _random.sample(range(1, 101), _random.choice([2] * 10 + [3] * 8 + [4] * 4 + [5, 6]))

            a_side_num = _random.randint(1, len(person_nbs) - 1)
            a_side, b_side = person_nbs[:a_side_num], person_nbs[a_side_num:]

            document_nb = case_nb
            self._execute("INSERT INTO Documents (document_nb, document_path, document_name, document_description, document_notes, archived) VALUES (?, ?, ?, ?, ?, ?)",
                                (document_nb, f"./documents/case_{case_nb}.pdf", f"Document {document_nb}", fake.text(), '\n'.join(fake.texts()), 1))
            self._execute("INSERT INTO CaseDocuments (case_nb, document_nb) VALUES (?, ?)",
                                (case_nb, document_nb))

            for aff, side in enumerate((a_side, b_side)):
                without_lawyer = []
                for person_nb in side:
                    self_represented = 0
                    if _random.choice([0, 1]):
                        lawyer_nb = _random.choice(lawyers)
                        if lawyer_nb != person_nb:
                            self._execute(
                                "INSERT INTO Representations (case_nb, person_nb, lawyer_nb, side) VALUES (?, ?, ?, ?)",
                                (case_nb, person_nb, lawyer_nb, aff))
                        else:
                            self_represented = 1
                    elif _random.choice([0, 0, 0, 0, 1]):  # Pretty foolish to self represent if you
                        self_represented = 1  # aren't a lawyer
                    else:
                        without_lawyer.append(person_nb)
                    self._execute("INSERT INTO CasePeople (case_nb, person_nb, side, has_external_lawyer, self_represented) VALUES (?, ?, ?, ?, ?)",
                                        (case_nb, person_nb, aff, 0, self_represented))

                shared_lawyer_nb = _random.choice(lawyers)
                for person in without_lawyer:
                    self._execute(
                        "INSERT INTO Representations (case_nb, person_nb, lawyer_nb, side) VALUES (?, ?, ?, ?)",
                        (case_nb, person, shared_lawyer_nb, aff))

    def get_persons(self, number: int, *_: _Literal["last_name", "first_name", "address", "birth_date", "contact_info",
                                                    "gender", "description", "notes", "can_be_lawyer", "cases"]):
        _, index = list(_), None

        if "cases" in _:
            index = _.index("cases")
            del _[index]

        if _:
            query = f"SELECT {', '.join(['p.' + attr for attr in _])} FROM Persons p WHERE p.person_nb = {number}"
            print(query)
            returns = [(x,) for x in self._query(query)[0]]
        else:
            returns = []

        if index is not None:
            cases_query = f"SELECT cp.case_nb FROM CasePeople cp WHERE cp.person_nb = {number}"
            returns.insert(index, tuple(x[0] for x in self._query(cases_query)))

        return returns

    def update_persons(self, number: int, **kwargs):
        allowed_columns = {"last_name", "first_name", "address", "birth_date", "contact_info", "gender", "description",
                           "notes", "can_be_lawyer"}
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in allowed_columns:
                updates.append(f"{key} = ?")
                params.append(value)
            elif key == "cases":
                # Remove existing cases
                self._execute("DELETE FROM CasePeople WHERE person_nb = ?", (number,))
                # Add new cases
                for case_nb in value:
                    self._execute("INSERT INTO CasePeople (case_nb, person_nb) VALUES (?, ?)", (case_nb, number))
            else:
                raise ValueError(f"Attribute {key} is not allowed")

        if updates:
            query = f"UPDATE Persons SET {', '.join(updates)} WHERE person_nb = ?"
            params.append(number)
            self._execute(query, params)

    def get_cases(self, number: int, *_: _Literal["case_name", "case_description", "case_notes", "persons", "documents"]):
        returns = []
        for attr in _:
            if attr in ("case_name", "case_description", "case_notes"):
                query = f"SELECT c.{attr} FROM Cases c WHERE c.case_nb = {number}"
                returns.append(self._query(query)[0])
            elif attr == "persons":
                query = f"SELECT cp.person_nb FROM CasePeople cp WHERE cp.case_nb = {number}"
                returns.append(tuple(x[0] for x in self._query(query)))
            elif attr == "documents":
                query = f"SELECT cd.document_nb FROM CaseDocuments cd WHERE cd.case_nb = {number}"
                returns.append(tuple(x[0] for x in self._query(query)))
            else:
                raise ValueError(f"Attribute {attr} is not allowed")
        return returns

    def update_cases(self, number: int, **kwargs):
        allowed_columns = {"case_name", "case_description", "case_notes"}
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in allowed_columns:
                updates.append(f"{key} = ?")
                params.append(value)
            elif key == "persons":
                # Remove existing persons
                self._execute("DELETE FROM CasePeople WHERE case_nb = ?", (number,))
                # Add new persons
                for person_nb in value:
                    self._execute("INSERT INTO CasePeople (case_nb, person_nb) VALUES (?, ?)", (number, person_nb))
            elif key == "documents":
                # Remove existing documents
                self._execute("DELETE FROM CaseDocuments WHERE case_nb = ?", (number,))
                # Add new documents
                for document_nb in value:
                    self._execute("INSERT INTO CaseDocuments (case_nb, document_nb) VALUES (?, ?)", (number, document_nb))
            else:
                raise ValueError(f"Attribute {key} is not allowed")

        if updates:
            query = f"UPDATE Cases SET {', '.join(updates)} WHERE case_nb = ?"
            params.append(number)
            self._execute(query, params)

    def get_documents(self, number: int, *_: _Literal["document_name", "document_description", "document_notes", "cases"]):
        returns = []
        for attr in _:
            if attr in ("document_name", "document_description", "document_notes"):
                query = f"SELECT d.{attr} FROM Documents d WHERE d.document_nb = {number}"
                returns.append(self._query(query)[0])
            elif attr == "cases":
                query = f"SELECT cd.case_nb FROM CaseDocuments cd WHERE cd.document_nb = {number}"
                returns.append(tuple(x[0] for x in self._query(query)))
            else:
                raise ValueError(f"Attribute {attr} is not allowed")
        return returns

    def update_documents(self, number: int, **kwargs):
        allowed_columns = {"document_name", "document_description", "document_notes"}
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in allowed_columns:
                updates.append(f"{key} = ?")
                params.append(value)
            elif key == "cases":
                # Remove existing cases
                self._execute("DELETE FROM CaseDocuments WHERE document_nb = ?", (number,))
                # Add new cases
                for case_nb in value:
                    self._execute("INSERT INTO CaseDocuments (case_nb, document_nb) VALUES (?, ?)", (case_nb, number))
            else:
                raise ValueError(f"Attribute {key} is not allowed")

        if updates:
            query = f"UPDATE Documents SET {', '.join(updates)} WHERE document_nb = ?"
            params.append(number)
            self._execute(query, params)

    def search(self, query) -> list:
        returns = []
        for sql in self.search_engine.get_sql_query_from_user_input(query):
            returns.extend(self._query(sql))
        return returns

    def restricted_search(self, query, where) -> list:
        return self._query(self.search_engine.get_sql_query_from_user_input_restricted(query, where))
