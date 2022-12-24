"""main module"""
import os
import sys
import logging
from directo.sheets import (
    DirectorySheetData,
    RosterSheetData,
    construct_sheet_range,
)
from directo.docs import DirectoryDoc

# The ID of a sample spreadsheet.
directory_sheet_id = os.environ.get("DIRECTORY_SHEET_ID")
roster_sheet_id = os.environ.get("ROSTER_SHEET_ID")


def make_class_roster(roster_data):
    doc = DirectoryDoc()
    doc.new("class roster")
    for grade in ["0", "1", "2", "3", "4", "5"]:
        doc.new_table(2)
        doc.fill_table_with_data(roster_data.format_roster_data(grade=grade))
        doc.unbroken_cells()
        doc.general_format_cells(font_size=9)
        doc.bold_cells_first_line()
    # another option is to make a new table for each grade-language
    return


def make_student_directory(roster_data):
    doc = DirectoryDoc()
    doc.new("student directory")
    doc.new_table(2)
    doc.fill_table_with_data(roster_data.format_directory_data())
    doc.unbroken_cells()
    doc.general_format_cells(font_size=9)
    doc.bold_cells_first_line()
    return


def get_directory_data(tab_name=None, col_start=None, col_end=None, row_start=None):
    directory_header_range = construct_sheet_range(
        tab_name=tab_name,
        col_start=col_start,
        col_end=col_end,
        row_start=row_start,
        row_end=row_start,
    )
    data_row_start = str(int(row_start) + 1)
    directory_data_range = construct_sheet_range(
        tab_name=tab_name,
        col_start=col_start,
        col_end=col_end,
        row_start=data_row_start,
        row_end="",
    )
    return DirectorySheetData(
        directory_sheet_id, directory_header_range, directory_data_range
    )


def get_roster_data(tab_name=None, col_start=None, col_end=None, row_start=None):
    roster_header_range = construct_sheet_range(
        tab_name=tab_name,
        col_start=col_start,
        col_end=col_end,
        row_start=row_start,
        row_end=row_start,
    )
    data_row_start = str(int(row_start) + 1)
    roster_data_range = construct_sheet_range(
        tab_name=tab_name,
        col_start=col_start,
        col_end=col_end,
        row_start=data_row_start,
        row_end="",
    )
    return RosterSheetData(roster_sheet_id, roster_header_range, roster_data_range)


def main():
    """main func"""

    if os.environ.get("DEBUG") is not None:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARN
    logging.basicConfig(level=log_level, stream=sys.stdout)

    roster_data = get_roster_data(
        tab_name="Sheet1", col_start="A", col_end="E", row_start="1"
    )

    if sys.argv[1] == "roster":
        print("Compiling roster...")
        make_class_roster(roster_data)
    elif sys.argv[1] == "directory":
        print("Compiling directory...")
        roster_data.enrich_roster_with_normalized_directory(
            get_directory_data(
                tab_name="working", col_start="E", col_end="AD", row_start="1"
            )
        )
        make_student_directory(roster_data)


if __name__ == "__main__":
    main()
