import asyncio
import json
import logging
from typing import Any, Dict, List

import httpx

from logshift.core.adapter import TransportAdapter
from logshift.core.exceptions import AdapterError

logger = logging.getLogger("logshift.adapters.slack")


class SlackAdapter(TransportAdapter):
    """
    SlackAdapter posts log notifications to a Slack channel via Webhooks,
    featuring built-in rate-limit (HTTP 429) retry logic.
    """

    def __init__(
        self, webhook_url: str, name: str = "slack", config: Dict[str, Any] | None = None
    ) -> None:
        super().__init__(name, config)
        self.webhook_url = webhook_url

    async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:
        """
        Ships logs to a Slack Webhook.

        Args:
            logs: List of log dicts.
            target: Webhook URL (fallback/override).
            **kwargs: Includes dry_run parameter.
        """
        dry_run = kwargs.get("dry_run", False)
        webhook_url = target or self.webhook_url

        if not webhook_url:
            raise AdapterError("Slack Webhook URL is required.")

        # Format logs as a pretty JSON block
        content = json.dumps(logs, indent=2, ensure_ascii=False)
        message_text = f"📢 *Logshift Archive Notification*\n```json\n{content}\n```"

        # Slack has a limit of 3000 characters per text block section
        chunks = self._chunk_message(message_text, limit=2900)

        if dry_run:
            logger.info("---------------- DRY-RUN SIMULATION ----------------")
            logger.info(f"[Dry-Run Slack] Webhook URL: {webhook_url[:15]}...")
            logger.info(f"[Dry-Run Slack] Split into {len(chunks)} message chunks.")
            for i, chunk in enumerate(chunks):
                logger.info(f"[Dry-Run Slack] Chunk {i + 1} Sample:\n{chunk[:200]}...")
            logger.info("----------------------------------------------------")
            return True

        # Send chunks sequentially using httpx with rate limit checks
        async with httpx.AsyncClient() as client:
            for idx, chunk in enumerate(chunks):
                await self._post_with_rate_limit(client, webhook_url, chunk, idx + 1, len(chunks))

        logger.info(f"Successfully sent {len(chunks)} messages to Slack.")
        return True

    async def _post_with_rate_limit(
        self,
        client: httpx.AsyncClient,
        url: str,
        content: str,
        chunk_num: int,
        total_chunks: int,
        max_attempts: int = 5,
    ) -> None:
        payload = {"text": content}

        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(url, json=payload, timeout=10.0)

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 2.0))
                    logger.warning(
                        f"Slack Rate Limit hit. Attempt {attempt}/{max_attempts}. "
                        f"Sleeping for {retry_after}s before retrying..."
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return  # Successful post
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 429:
                    raise AdapterError(
                        f"Slack API returned HTTP {e.response.status_code} "
                        f"on chunk {chunk_num}/{total_chunks}: {e}"
                    ) from e
            except Exception as e:
                raise AdapterError(
                    f"Failed to post chunk {chunk_num}/{total_chunks} to Slack: {e}"
                ) from e

        raise AdapterError(
            f"Failed to post chunk {chunk_num}/{total_chunks} to Slack: "
            f"Rate limited repeatedly after {max_attempts} attempts."
        )

    def _chunk_message(self, text: str, limit: int = 2900) -> List[str]:
        chunks = []
        while len(text) > 0:
            if len(text) <= limit:
                chunks.append(text)
                break
            # Find a clean split point (newline or space)
            split_idx = text.rfind("\n", 0, limit)
            if split_idx == -1 or split_idx < limit * 0.8:
                split_idx = text.rfind(" ", 0, limit)
            if split_idx == -1:
                split_idx = limit

            # Extract chunk
            chunk_content = text[:split_idx]

            # Make sure markdown fences are closed if we split inside them
            if chunk_content.count("```") % 2 != 0:
                chunk_content += "\n```"

            chunks.append(chunk_content)

            # Prepare remaining text (prepending open markdown code fence if it was split)
            remaining = text[split_idx:].strip()
            if text[:split_idx].count("```") % 2 != 0:
                remaining = "```json\n" + remaining
            text = remaining

        return chunks
