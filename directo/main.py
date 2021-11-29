"""main module"""
import os
from pprint import pprint
from directo.sheets import (
    DirectorySheetData,
    RosterSheetData,
    construct_sheet_range,
)

# The ID of a sample spreadsheet.
directory_sheet_id = os.environ.get("DIRECTORY_SHEET_ID")
roster_sheet_id = os.environ.get("ROSTER_SHEET_ID")


def main():
    """main func"""

    directory_header_range = construct_sheet_range(
        tab_name="working", col_start="E", col_end="AD", row_start="1", row_end="1"
    )
    directory_data_range = construct_sheet_range(
        tab_name="working", col_start="E", col_end="AD", row_start="2", row_end=""
    )
    directory_data = DirectorySheetData(
        directory_sheet_id, directory_header_range, directory_data_range
    )
    roster_header_range = construct_sheet_range(
        tab_name="Sheet1", col_start="A", col_end="D", row_start="1", row_end="1"
    )
    roster_data_range = construct_sheet_range(
        tab_name="Sheet1", col_start="A", col_end="D", row_start="2", row_end=""
    )
    roster_data = RosterSheetData(
        roster_sheet_id, roster_header_range, roster_data_range
    )
    roster_data.enrich_roster_with_normalized_directory(directory_data)
    pprint(roster_data.children_enriched)
    pprint(roster_data.by_teacher_grade())
    pprint(roster_data.by_student_with_parents())


if __name__ == "__main__":
    main()
