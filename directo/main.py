"""main module"""
import os
import sys
import logging
from pprint import pprint
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


def main():
    """main func"""

    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

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
        tab_name="Sheet1", col_start="A", col_end="E", row_start="1", row_end="1"
    )
    roster_data_range = construct_sheet_range(
        tab_name="Sheet1", col_start="A", col_end="E", row_start="2", row_end=""
    )
    roster_data = RosterSheetData(
        roster_sheet_id, roster_header_range, roster_data_range
    )
    roster_data.enrich_roster_with_normalized_directory(directory_data)

    if sys.argv[1] == "roster":
        logging.info("Compiling roster...")
        make_class_roster(roster_data)
    elif sys.argv[1] == "directory":
        logging.info("Compiling directory...")
        make_student_directory(roster_data)


if __name__ == "__main__":
    main()
