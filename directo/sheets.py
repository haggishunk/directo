"""sheets module"""
from googleapiclient.discovery import build
from directo.auth import get_creds, SCOPES_RO
from jinja2 import Template
import logging


def read_sheet_range(sheet_id, sheet_range):
    service = build("sheets", "v4", credentials=get_creds(SCOPES_RO))
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=sheet_range)
        .execute()
    )
    return result


def construct_sheet_range(
    tab_name="Sheet1", col_start="A", col_end="Z", row_start="1", row_end=""
):
    return f"{tab_name}!{col_start}{row_start}:{col_end}{row_end}"


def format_name(item):
    return f"{item['name_last']}, {item['name_first']}"


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

    def parse_child_from_item(self, item):
        child_attributes = [
            "name_last",
            "name_first",
            "grade",
            "teacher_hr",
        ]
        child = dict([(k, v) for k, v in item.items() if k in child_attributes])
        result = {}
        result[format_name(child)] = child
        return result

    def read(self):
        """make a list of children with their data and their parent/guardian info"""
        for item in self.data_structured:
            child = self.parse_child_from_item(item)
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
                child_data["parents"] = child_parents
            except KeyError:
                logging.debug("No parents listed for child in directory data")

    def by_teacher_grade(self):
        teacher_grades = sorted(
            set(
                [
                    (v["teacher_hr"], v["grade"])
                    for k, v in self.children_enriched.items()
                ]
            ),
            key=lambda x: x[1],
        )
        result = {}
        for tg in teacher_grades:
            result[f"{tg[1]} - {tg[0]}"] = [
                k for k, v in self.children_enriched.items() if v["teacher_hr"] == tg[0]
            ]
        return result

    def by_student_with_parents(self):
        result = {}
        for child_name, child_data in self.children_enriched.items():
            try:
                parents_formatted = "\n\n".join(
                    [format_address(p) for p in child_data["parents"]]
                )
            except KeyError:
                parents_formatted = ""
            result[f"{child_name} - {child_data['grade']}"] = parents_formatted
        return result


class DirectorySheetData(SheetData):
    def __init__(self, sheet_id, header_range, data_range):
        super().__init__(sheet_id, header_range, data_range)
        self.children = {}
        self.parents = {}
        self.converge_data()

    def parse_parents_from_item(self, item):
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

    def parse_children_from_item(self, item):
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

    def parse_family_from_item(self, item):
        parents = self.parse_parents_from_item(item)
        children = self.parse_children_from_item(item)
        for child_name, child_data in children.items():
            child_data["parents"] = list(set(parents.keys()))
        return {
            "children": children,
            "parents": parents,
        }

    def converge_data(self):
        """make a list of children with their data and their parent/guardian info"""
        for item in self.data_structured:
            family = self.parse_family_from_item(item)
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
