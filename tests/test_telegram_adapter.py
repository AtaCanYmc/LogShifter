import pytest
from unittest.mock import AsyncMock, patch
from logshift.adapters.telegram import TelegramAdapter


@pytest.mark.asyncio
async def test_telegram_adapter_dry_run():
    adapter = TelegramAdapter(bot_token="token", chat_id="chat")
    res = await adapter.ship(logs=[{"id": 1, "message": "hello"}], target="chat", dry_run=True)
    assert res is True


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_telegram_adapter_real_flow(mock_post):
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    adapter = TelegramAdapter(bot_token="token", chat_id="chat")
    res = await adapter.ship(logs=[{"id": 1, "message": "hello"}], target="chat", dry_run=False)
    assert res is True
    mock_post.assert_called_once()
