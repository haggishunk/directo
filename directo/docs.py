"""docs module"""
from googleapiclient.discovery import build
from directo.auth import get_creds, SCOPES_RO


def read_doc_title(doc_id):
    """Shows basic usage of the Docs API.
    Prints the title of a sample document.
    """
    service = build("docs", "v1", credentials=get_creds(SCOPES_RO))
    # Retrieve the documents contents from the Docs service.
    document = service.documents().get(documentId=doc_id).execute()
    return document.get("title")
