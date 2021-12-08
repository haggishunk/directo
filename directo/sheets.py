"""sheets module"""
from googleapiclient.discovery import build
from directo.auth import get_creds, SCOPES_RW
from jinja2 import Template
import logging


# const

GRADE_REPR = {
    "0": "K",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
}


# api interaction
def read_sheet_range(sheet_id, sheet_range):
    service = build("sheets", "v4", credentials=get_creds(SCOPES_RW))
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=sheet_range)
        .execute()
    )
    return result


# sheets types
def construct_sheet_range(
    tab_name="Sheet1", col_start="A", col_end="Z", row_start="1", row_end=""
):
    return f"{tab_name}!{col_start}{row_start}:{col_end}{row_end}"


# formatting funcs
def format_name(item):
    return f"{item['name_last']}, {item['name_first']}"


def format_addresses(parents_info):
    result = "\n\n".join([format_address(p) for p in parents_info])
    if result == "":
        result = "\n"  # docs api requires non-empty string for text inserts
    return result


def format_address(parent_data):
    template = Template(
        """
{{name_first}} {{name_last}}
{% if address is defined -%}
{{address}}
{% endif %}
{%- if city is defined -%}
{{city}} {{state}} {{zip}}
{% endif %}
{%- if email is defined -%}
{{email}}
{% endif %}
{%- if phone is defined -%}
{{phone}}
{% endif %}
"""
    )
    return template.render(parent_data).strip()


# data parsing
def parse_parents_from_item(item):
    parent_a_attributes = [
        "name_last_parent_guardian_a",
        "name_first_parent_guardian_a",
        "email_parent_guardian_a",
        "phone_parent_guardian_a",
        "address_parent_guardian_a",
        "city_parent_guardian_a",
        "state_parent_guardian_a",
        "zip_parent_guardian_a",
    ]
    parent_a = dict(
        [
            (k.replace("_parent_guardian_a", ""), v)
            for k, v in item.items()
            if k in parent_a_attributes and v != ""
        ]
    )
    parent_b_attributes = [
        "name_last_parent_guardian_b",
        "name_first_parent_guardian_b",
        "email_parent_guardian_b",
        "phone_parent_guardian_b",
        "address_parent_guardian_b",
        "city_parent_guardian_b",
        "state_parent_guardian_b",
        "zip_parent_guardian_b",
    ]
    parent_b = dict(
        [
            (k.replace("_parent_guardian_b", ""), v)
            for k, v in item.items()
            if k in parent_b_attributes and v != ""
        ]
    )
    result = {}
    result[format_name(parent_a)] = parent_a
    if "name_last" in parent_b:
        result[format_name(parent_b)] = parent_b
    return result


def parse_children_from_item(item):
    child_a_attributes = [
        "name_last_child_a",
        "name_first_child_a",
        # "grade_child_a",
        # "program_child_a",
        # "teacher_hr_child_a",
    ]
    child_a = dict(
        [
            (k.replace("_child_a", ""), v)
            for k, v in item.items()
            if k in child_a_attributes
        ]
    )
    child_b_attributes = [
        "name_last_child_b",
        "name_first_child_b",
        # "grade_child_b",
        # "program_child_b",
        # "teacher_hr_child_b",
    ]
    child_b = dict(
        [
            (k.replace("_child_b", ""), v)
            for k, v in item.items()
            if k in child_b_attributes
        ]
    )
    result = {}
    result[format_name(child_a)] = child_a
    if "name_last" in child_b:
        result[format_name(child_b)] = child_b
    return result


def parse_family_from_item(item):
    parents = parse_parents_from_item(item)
    children = parse_children_from_item(item)
    for child_name, child_data in children.items():
        child_data["parents"] = list(set(parents.keys()))
    return {
        "children": children,
        "parents": parents,
    }


def parse_child_from_item(item):
    child_attributes = [
        "name_last",
        "name_first",
        "grade",
        "teacher_hr",
        "language",
    ]
    child = dict([(k, v) for k, v in item.items() if k in child_attributes])
    result = {}
    result[format_name(child)] = child
    return result


class SheetData(object):
    def __init__(self, sheet_id, header_range, data_range):
        self.sheet_id = sheet_id
        self.header_range = header_range
        self.data_range = data_range
        self.read_sheet_headers()
        self.read_sheet_data()
        self.structure_data()

    def read_sheet_headers(self):
        self.headers = read_sheet_range(self.sheet_id, self.header_range)["values"][0]

    def read_sheet_data(self):
        self.data = read_sheet_range(self.sheet_id, self.data_range)["values"]

    def structure_data(self):
        self.data_structured = list(
            map(lambda d: dict(zip(self.headers, d)), self.data)
        )


class RosterSheetData(SheetData):
    def __init__(self, sheet_id, header_range, data_range):
        super().__init__(sheet_id, header_range, data_range)
        self.children = {}
        self.read()

    def read(self):
        """make a list of children with their data and their parent/guardian info"""
        for item in self.data_structured:
            child = parse_child_from_item(item)
            self.children.update(child)

    def enrich_roster_with_normalized_directory(self, directory_data):
        self.children_enriched = self.children.copy()
        for child_name, child_data in self.children_enriched.items():
            try:
                child_data.update(directory_data.children[child_name])
            except KeyError:
                logging.debug("Child not in directory data")
            try:
                child_parents = [
                    directory_data.parents[p] for p in child_data["parents"]
                ]
            except KeyError:
                logging.debug("No parents listed for child in directory data")
                child_parents = []
            child_data["parents"] = child_parents

    def correlate_teachers_to_students(
        self, sort=False, sort_attribute="index_slug", grade="all"
    ):
        """returns objects with teacher, grade and students
        object = {
            "teacher_name": "bob smith",
            "grade": "3",
            "language": "Spanish"
            "student_names": [
                "jack",
                "jill",

            ]
        }
        """
        if grade == "all":
            grades = ["0", "1", "2", "3", "4", "5"]
        else:
            grades = [grade]
        # group by teacher, grade
        teacher_grades = set(
            [
                (v["teacher_hr"], v["grade"], v["language"])
                for k, v in self.children.items()
            ]
        )
        result = []
        for teacher, grade, language in teacher_grades:
            if grade in grades:
                result.append(
                    {
                        "index_slug": f"{grade}-{language}-{teacher}",
                        "teacher_name": teacher,
                        "grade": grade,
                        "language": language,
                        "students": [
                            k
                            for k, v in self.children.items()
                            if v["teacher_hr"] == teacher
                        ],
                    }
                )
        if sort:
            result = sorted(result, key=lambda x: x[sort_attribute])
        return result

    def correlate_students_to_parents(self, sort=False, sort_attribute="student_name"):
        """returns objects with student, grade, parents info
        object = {
            "student_name": "jack",
            "grade": "3",
            "parents_info": "name\naddress\nemail\n\phone\n"
        }
        """
        result = []
        for child_name, child_data in self.children_enriched.items():
            result.append(
                {
                    "student_name": child_name,
                    "grade": child_data["grade"],
                    "parents_info": format_addresses(child_data["parents"]),
                }
            )
        if sort:
            result = sorted(result, key=lambda x: x[sort_attribute])
        return result

    def format_directory_data(self):
        """returns a sorted list of text groups headed by student name/grade
        followed by parents info"""
        return [
            (
                f"{student['student_name']} - {GRADE_REPR[student['grade']]}\n\n",
                f"{student['parents_info']}",
            )
            for student in self.correlate_students_to_parents(sort=True)
        ]

    def format_roster_data(self, grade="all"):
        result = []
        for klass in self.correlate_teachers_to_students(sort=True, grade=grade):
            grade_formatted = GRADE_REPR[klass["grade"]]
            students_formatted = "\n".join(klass["students"])
            result.append(
                (
                    f"{klass['teacher_name']} - {grade_formatted} - {klass['language']}\n\n",
                    f"{students_formatted}",
                )
            )
        return result


class DirectorySheetData(SheetData):
    def __init__(self, sheet_id, header_range, data_range):
        super().__init__(sheet_id, header_range, data_range)
        self.children = {}
        self.parents = {}
        self.converge_data()

    def converge_data(self):
        """make a list of children with their data and their parent/guardian info"""
        for item in self.data_structured:
            family = parse_family_from_item(item)
            for child_name, child_data in family["children"].items():
                if child_name not in self.children:
                    self.children[child_name] = child_data
                else:
                    self.children[child_name].update(child_data)
            for parent_name, parent_data in family["parents"].items():
                if parent_name not in self.parents:
                    self.parents[parent_name] = parent_data
                else:
                    self.parents[parent_name].update(parent_data)
