"""main module"""
import os
import directo.sheets

# The ID of a sample spreadsheet.
directory_sheet_id = os.environ.get("DIRECTORY_SHEET_ID")
roster_sheet_id = os.environ.get("ROSTER_SHEET_ID")


def main():
    """main func"""
    directory_data = directo.sheets.DirectorySheetData(directory_sheet_id)
    roster_data = directo.sheets.RosterSheetData(roster_sheet_id)
    roster_children = roster_data.children.copy()
    directory_children = directory_data.children.copy()
    for child_name, child_data in roster_children.items():
        try:
            child_data.update(directory_children[child_name])
        except KeyError:
            pass


if __name__ == "__main__":
    main()
