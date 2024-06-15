from typing import Literal, List, Tuple, Optional
import re


class SearchEngine:
    _table_pattern = r"(?:([a-zA-Z_]+)(?:\[(\w*)])?(?:\{(\w+)})?([:=])\s?)?('[^']*'|(?:\w+\s?)+)((?:\s?[|&]\s?{\w*}[:=]\s?(?:'[^']*'|(?:\w+\s?)+)|\s?[|&]\s?)*)"
    _search_term_pattern = r"([&|])\s?\{(\w*)}([:=])\s?((?:\w+\s?)*)|([|])\s?"

    def __init__(self):
        self._table_rejects = re.compile(self._table_pattern)
        self._search_term_rejects = re.compile(self._search_term_pattern)

    def _check_consumed_string(self, input_string: str, rejects) -> Tuple[List[str], bool]:
        matches = list(rejects.finditer(input_string))
        all_matches = [match.group() for match in matches]

        if not matches:
            return [], False

        # Check if the entire string is consumed
        last_end = 0
        for match in matches:
            if match.start() != last_end:
                return all_matches, False
            last_end = match.end()

        entire_string_consumed = last_end == len(input_string)
        return all_matches, entire_string_consumed

    def _check_consumed_substring(self, input_string: str, rejects) -> Tuple[List[Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]], bool]:
        matches = list(rejects.finditer(input_string))
        all_matches = [match.groups() for match in matches]

        if not matches and input_string == "":
            return [], True
        elif not matches:
            return [], False

        # Check if the entire string is consumed
        last_end = 0
        for match in matches:
            if match.start() != last_end:
                return all_matches, False
            last_end = match.end()

        entire_string_consumed = last_end == len(input_string)
        return all_matches, entire_string_consumed

    def _parse_user_input(self, user_input: str) -> Optional[List[Tuple[Tuple, List[Tuple]]]]:
        main_matches, entire_string_consumed = self._check_consumed_string(user_input, self._table_rejects)

        if not entire_string_consumed:
            return None

        parsed_results = []
        for main_match in main_matches:
            match = self._table_rejects.match(main_match)
            if not match:
                continue

            groups = match.groups()
            sub_string = groups[-1]

            search_terms, sub_string_consumed = self._check_consumed_substring(sub_string, self._search_term_rejects)

            if not sub_string_consumed:
                return None

            parsed_results.append((groups[:-1], search_terms))

        return parsed_results

    def _generate_query(self, input_tuple, search_terms):
        table_name = input_tuple[0]
        initial_column = input_tuple[2]
        initial_bool = input_tuple[3]
        initial_value = input_tuple[4]

        query = f"SELECT * FROM {table_name} WHERE "

        conditions = []
        params = []

        # Handle the initial search term
        if initial_bool == ":":
            if initial_column:
                conditions.append(f"{initial_column} REGEXP ?")
                params.append(initial_value)
            else:
                conditions.append("(name REGEXP ? OR email REGEXP ?)")
                params.extend([initial_value, initial_value])
        else:
            if initial_column:
                conditions.append(f"{initial_column} = ?")
                params.append(initial_value)
            else:
                conditions.append("(name = ? OR email = ?)")
                params.extend([initial_value, initial_value])

        # Handle additional search terms
        for term in search_terms:
            combinator = term[0]
            column = term[1]
            search_bool = term[2]
            search_value = term[3]

            if search_bool == ":":
                condition = f"{column} REGEXP ?"
            else:
                condition = f"{column} = ?"

            if combinator == "&":
                conditions.append(f"AND {condition}")
            elif combinator == "|":
                conditions.append(f"OR {condition}")
            else:
                conditions.append(condition)

            params.append(search_value)

        # Build the final query
        query += " ".join(conditions)

        return query, params

    def get_sql_query_from_user_input(self, user_input) -> list:
        parsed_input = self._parse_user_input(user_input)

        for main, search_terms in parsed_input:
            main = {"user": "Persons", "case": "Cases", "docu": "Documents"}[main]
            print(self._generate_query(main, search_terms))

        return ["SELECT * FROM Persons", "SELECT * FROM Cases", "SELECT * FROM Documents"]

    def get_sql_query_from_user_input_restricted(self, user_input, type_: Literal["user", "case", "docu"]) -> str:
        table = {"user": "Persons", "case": "Cases", "docu": "Documents"}[type_]
        return f"SELECT * FROM {table}"


ins = SearchEngine()
ins.get_sql_query_from_user_input("name: value Tim & {word1}: value1 | {word2}= value2 | {word3}: value3 | cases[non]: cat")
