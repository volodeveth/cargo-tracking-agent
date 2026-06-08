from __future__ import annotations
from ..models.schemas import ShipmentResult


def export_to_sheets(results: list[ShipmentResult], spreadsheet_id: str,
                     credentials_path: str) -> bool:
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        return False
    if not (spreadsheet_id and credentials_path):
        return False
    creds = Credentials.from_service_account_file(
        credentials_path, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    service = build("sheets", "v4", credentials=creds)
    rows = [["id", "number", "status"]]
    for r in results:
        rows.append([r.input.id, r.input.number,
                     r.tracking.current_status.value if r.tracking and r.tracking.current_status else ""])
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range="A1",
        valueInputOption="RAW", body={"values": rows}).execute()
    return True
