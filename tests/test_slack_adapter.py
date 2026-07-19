import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from logshift.adapters.slack import SlackAdapter


@pytest.mark.asyncio
async def test_slack_adapter_dry_run():
    adapter = SlackAdapter(webhook_url="https://hooks.slack.com/services/123/abc")
    res = await adapter.ship(
        logs=[{"id": 1, "message": "hello"}],
        target="https://hooks.slack.com/services/123/abc",
        dry_run=True,
    )
    assert res is True


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_slack_adapter_real_flow(mock_post):
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    adapter = SlackAdapter(webhook_url="https://hooks.slack.com/services/123/abc")
    res = await adapter.ship(
        logs=[{"id": 1, "message": "hello"}],
        target="https://hooks.slack.com/services/123/abc",
        dry_run=False,
    )
    assert res is True
    mock_post.assert_called_once()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_slack_adapter_rate_limit(mock_sleep, mock_post):
    # Set up mock response sequence: first call returns 429, second returns 200
    response_429 = MagicMock()
    response_429.status_code = 429
    response_429.headers = {"Retry-After": "0.5"}

    response_200 = MagicMock()
    response_200.status_code = 200
    response_200.raise_for_status = MagicMock()

    mock_post.side_effect = [response_429, response_200]

    adapter = SlackAdapter(webhook_url="https://hooks.slack.com/services/123/abc")
    res = await adapter.ship(
        logs=[{"id": 1, "message": "hello"}],
        target="https://hooks.slack.com/services/123/abc",
        dry_run=False,
    )
    assert res is True

    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(0.5)
