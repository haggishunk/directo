"""docs module"""
from googleapiclient.discovery import build
from directo.auth import get_creds, SCOPES_RO, SCOPES_RW
import logging
import time


# api interactions
def get_doc_json(doc_id):
    service = build("docs", "v1", credentials=get_creds(SCOPES_RO))
    return service.documents().get(documentId=doc_id).execute()


def create_doc(body):
    service = build("docs", "v1", credentials=get_creds(SCOPES_RW))
    doc = service.documents().create(body=body).execute()
    return doc["documentId"]


def get_doc(doc_id, read_only=False):
    if read_only:
        scopes = SCOPES_RO
    else:
        scopes = SCOPES_RW
    service = build("docs", "v1", credentials=get_creds(scopes))
    doc = service.documents().get(documentId=doc_id).execute()
    return doc["documentId"]


def batch_update_doc(doc_id, requests):
    service = build("docs", "v1", credentials=get_creds(SCOPES_RW))
    while len(requests) > 0:
        request_group = []
        for _ in range(100):
            try:
                request_group.append(requests.pop(0))
            except Exception:
                pass
        _ = (
            service.documents()
            .batchUpdate(documentId=doc_id, body={"requests": request_group})
            .execute()
        )
        time.sleep(1)
    return


# document json data extraction
def table_last_row_index(table):
    """returns the index of the last row to append by"""
    return table["rows"] - 1


def table_last_row_content_append_indexes(table):
    """returns the index to append cell content by"""
    return [
        cell["content"][-1]["endIndex"] - 1
        for cell in table["tableRows"][-1]["tableCells"]
    ]


def last_table_index(doc_json):
    table_content_indexes = []
    for i, content in enumerate(doc_json["body"]["content"]):
        if "table" in content:
            table_content_indexes.append(i)
    return table_content_indexes[-1]


def all_cells_content_indexes(table_json, first_para_only=False):
    result = []
    for row in table_json["tableRows"]:
        for cell in row["tableCells"]:
            if first_para_only:
                content = cell["content"][0]
            else:
                content = cell
            result.append((content["startIndex"], content["endIndex"]))
    return result


# request bodies
def insert_table_request(rows, columns):
    return {
        "insertTable": {
            "rows": rows,
            "columns": columns,
            "endOfSegmentLocation": {"segmentId": ""},
        },
    }


def insert_text_request(text, index):
    return {"insertText": {"text": text, "location": {"index": index}}}


def update_table_style_request(style, table_range, table_start_index):
    return {
        "tableCellStyle": style,
        "fields": ",".join(list(style.keys())),
        "tableRange": table_range,
        "tableStart": table_start_index,
    }


def update_text_style_request(style, index_start, index_end):
    return {
        "updateTextStyle": {
            "textStyle": style,
            "fields": ",".join(list(style.keys())),
            "range": {
                "startIndex": index_start,
                "endIndex": index_end,
            },
        }
    }


def update_paragraph_style_request(style, index_start, index_end):
    return {
        "updateParagraphStyle": {
            "paragraphStyle": style,
            "fields": ",".join(list(style.keys())),
            "range": {
                "startIndex": index_start,
                "endIndex": index_end,
            },
        }
    }


# collection manipulation
def reversed_insert_text_requests(text_groups, content_append_indices):
    """make a list of text insertion requests in reverse (right to left) order
    since index mutates flowing forward (left to right)"""
    text_groups_with_indices = list(zip(text_groups, content_append_indices))
    requests = []
    for text_group, index in text_groups_with_indices:
        requests_for_text_group = [
            insert_text_request(text, index) for text in text_group
        ]
        logging.debug(requests_for_text_group)
        requests.extend(requests_for_text_group)
    return list(reversed(requests))


def group_cell_data_items(cell_data_items, per_group, default_item_value=("\n")):
    """cell data items are returned by this generator in lists with the requested per group size"""
    while len(cell_data_items) > 0:
        result = []
        for _ in range(per_group):
            try:
                result.append(cell_data_items.pop(0))
            except IndexError:
                result.append(default_item_value)
        yield result


class DirectoryDoc(object):
    def __init__(self):
        self.doc_id = None
        self.doc_json = None
        self.table_index = None
        self.active_table_json = None
        self.table_start_index = None
        self.columns_count = None

    def new(self, title):
        body = {
            "title": title,
            "body": {},
        }
        self.doc_id = create_doc(body)
        self.refresh_doc_json()

    def new_table(self, columns):
        requests = [insert_table_request(rows=1, columns=columns)]
        self.batch_update(requests)
        self.activate_table(last_table_index(self.doc_json))
        self.refresh_table_json()

    def get(self, doc_id, read_only=False):
        self.doc_id = get_doc(doc_id, read_only)
        self.refresh_doc_json()

    def batch_update(self, requests):
        batch_update_doc(self.doc_id, requests)
        self.refresh_doc_json()
        try:
            self.refresh_table_json()
        except Exception:
            pass

    def refresh_doc_json(self):
        """"""
        self.doc_json = get_doc_json(self.doc_id)

    def activate_table(self, index):
        """more permanent state persistence method for targeted table operations"""
        self.table_index = index
        self.refresh_table_json()

    def refresh_table_json(self):
        """this can be done repeatedly to update table mutable data"""
        table_content = self.doc_json["body"]["content"][self.table_index]
        self.active_table_json = table_content["table"]
        self.table_start_index = table_content["startIndex"]
        self.columns_count = self.active_table_json["columns"]

    def append_table_row(self):
        requests = [
            {
                "insertTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": self.table_start_index},
                        "rowIndex": table_last_row_index(self.active_table_json),
                        "columnIndex": 1,
                    },
                    "insertBelow": "true",
                }
            }
        ]
        self.batch_update(requests)
        return

    def fill_last_table_row(self, text_groups):
        """sew together cell content append indexes with data for text insertion
        data_group complies with InsertText"""
        content_append_indexes = table_last_row_content_append_indexes(
            self.active_table_json
        )
        requests = reversed_insert_text_requests(text_groups, content_append_indexes)
        self.batch_update(requests)

    def fill_table_with_data(self, data):
        for data_group in group_cell_data_items(data, self.columns_count):
            self.fill_last_table_row(data_group)
            self.append_table_row()

    def apply_text_style(self, style, first_para_only=False):
        requests = [
            update_text_style_request(style, index_start, index_end)
            for (index_start, index_end) in all_cells_content_indexes(
                self.active_table_json, first_para_only=first_para_only
            )
        ]
        self.batch_update(requests)

    def apply_paragraph_style(self, style, first_para_only=False):
        requests = [
            update_paragraph_style_request(style, index_start, index_end)
            for (index_start, index_end) in all_cells_content_indexes(
                self.active_table_json, first_para_only=first_para_only
            )
        ]
        self.batch_update(requests)

    def bold_cells_first_line(self):
        style = {"bold": True}
        self.apply_text_style(style, first_para_only=True)

    def general_format_cells(self, font_size=8, font_family="Calibri"):
        style = {
            "fontSize": {"magnitude": font_size, "unit": "PT"},
            "weightedFontFamily": {"fontFamily": font_family, "weight": 400},
        }
        self.apply_text_style(style)

    def unbroken_cells(self):
        style = {
            "keepLinesTogether": True,
            "keepWithNext": True,
        }
        self.apply_paragraph_style(style)
