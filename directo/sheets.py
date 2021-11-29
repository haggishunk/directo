"""sheets module"""
from googleapiclient.discovery import build
from pprint import pprint
from directo.auth import get_creds, SCOPES_RO


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


class SheetData(object):
    def __init__(self, sheet_id):
        self.sheet_id = sheet_id
        self.header_range = construct_sheet_range(
            tab_name="Sheet1", col_start="A", col_end="Z", row_start="1", row_end="1"
        )
        self.data_range = construct_sheet_range(
            tab_name="Sheet1", col_start="A", col_end="Z", row_start="2", row_end=""
        )

    def get_sheet_header(self):
        return read_sheet_range(self.sheet_id, self.header_range)["values"][0]

    def get_sheet_data(self):
        return read_sheet_range(self.sheet_id, self.data_range)["values"]

    def get_sheet_items(self):
        headers = self.get_sheet_header()
        data = self.get_sheet_data()
        return list(map(lambda d: dict(zip(headers, d)), data))


class RosterSheetData(SheetData):
    def __init__(self, sheet_id):
        self.sheet_id = sheet_id
        self.children = {}
        self.header_range = construct_sheet_range(
            tab_name="Sheet1", col_start="A", col_end="D", row_start="1", row_end="1"
        )
        self.data_range = construct_sheet_range(
            tab_name="Sheet1", col_start="A", col_end="D", row_start="2", row_end=""
        )

    def parse_child_from_item(self, row_data):
        child_attributes = [
            "name_last",
            "name_first",
            "grade",
            "teacher_hr",
        ]
        child = dict([(k, v) for k, v in row_data.items() if k in child_attributes])
        result = {}
        result[format_name(child)] = child
        return result

    def read(self):
        """make a list of children with their data and their parent/guardian info"""
        for item in self.get_sheet_items():
            child = self.parse_child_from_item(item)
            self.children.update(child)


class DirectorySheetData(SheetData):
    def __init__(self, sheet_id):
        self.sheet_id = sheet_id
        self.children = {}
        self.parents = {}
        self.header_range = construct_sheet_range(
            tab_name="combined", col_start="E", col_end="AD", row_start="1", row_end="1"
        )
        self.data_range = construct_sheet_range(
            tab_name="combined", col_start="E", col_end="AD", row_start="2", row_end=""
        )

    def parse_parents_from_item(self, row_data):
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
                for k, v in row_data.items()
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
                for k, v in row_data.items()
                if k in parent_b_attributes and v != ""
            ]
        )
        result = {}
        result[format_name(parent_a)] = parent_a
        if "name_last" in parent_b:
            result[format_name(parent_b)] = parent_b
        return result

    def parse_children_from_item(self, row_data):
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
                for k, v in row_data.items()
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
                for k, v in row_data.items()
                if k in child_b_attributes
            ]
        )
        result = {}
        result[format_name(child_a)] = child_a
        if "name_last" in child_b:
            result[format_name(child_b)] = child_b
        return result

    def parse_family_from_item(self, row_data):
        parents = self.parse_parents_from_item(row_data)
        children = self.parse_children_from_item(row_data)
        for child_name, child_data in children.items():
            child_data["parents"] = list(set(parents.keys()))
        return {
            "children": children,
            "parents": parents,
        }

    def converge_data(self):
        """make a list of children with their data and their parent/guardian info"""
        for item in self.get_sheet_items():
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
