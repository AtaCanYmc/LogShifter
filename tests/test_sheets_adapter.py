import pytest
from unittest.mock import MagicMock, patch
from logshift.adapters.sheets import SheetsAdapter


@pytest.mark.asyncio
async def test_sheets_adapter_dry_run():
    adapter = SheetsAdapter(
        service_account_file="creds.json",
        spreadsheet_id="sheet_123",
        worksheet_name="Logs"
    )
    res = await adapter.ship(
        logs=[{"id": 1, "message": "hello"}],
        target="sheet_123",
        dry_run=True
    )
    assert res is True
    assert adapter.spreadsheet_id == "sheet_123"


@pytest.mark.asyncio
@patch("gspread.service_account")
async def test_sheets_adapter_real_flow(mock_sa):
    mock_client = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_worksheet = MagicMock()
    
    mock_sa.return_value = mock_client
    mock_client.open_by_key.return_value = mock_spreadsheet
    mock_spreadsheet.worksheet.return_value = mock_worksheet
    
    adapter = SheetsAdapter(
        service_account_file="creds.json",
        spreadsheet_id="sheet_123",
        worksheet_name="Logs"
    )
    
    res = await adapter.ship(
        logs=[{"id": 1, "message": "hello"}],
        target="sheet_123",
        dry_run=False
    )
    assert res is True
    mock_worksheet.append_rows.assert_called_once()
