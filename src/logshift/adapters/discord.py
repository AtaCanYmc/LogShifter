import asyncio
import json
import logging
from typing import Any, Dict, List
import httpx
from base import TransportAdapter
from logshift.core.exceptions import AdapterError

logger = logging.getLogger("logshift.adapters.discord")


class DiscordAdapter(TransportAdapter):
    """
    DiscordAdapter posts log notifications to a Discord channel via Webhooks,
    featuring built-in rate-limit (HTTP 429) retry logic.
    """

    def __init__(
        self,
        webhook_url: str,
        name: str = "discord",
        config: Dict[str, Any] | None = None
    ) -> None:
        super().__init__(name, config)
        self.webhook_url = webhook_url

    async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:
        """
        Ships logs to a Discord Webhook.
        
        Args:
            logs: List of log dicts.
            target: Webhook URL (fallback/override).
            **kwargs: Includes dry_run parameter.
        """
        dry_run = kwargs.get("dry_run", False)
        webhook_url = target or self.webhook_url

        if not webhook_url:
            raise AdapterError("Discord Webhook URL is required.")

        # Format logs as a pretty JSON block
        content = json.dumps(logs, indent=2, ensure_ascii=False)
        message_text = f"📢 **Logshift Archive Notification**\n```json\n{content}\n```"

        # Discord has a strict 2000 character limit for message content
        chunks = self._chunk_message(message_text, limit=1900)

        if dry_run:
            logger.info("---------------- DRY-RUN SIMULATION ----------------")
            logger.info(f"[Dry-Run Discord] Webhook URL: {webhook_url[:15]}...")
            logger.info(f"[Dry-Run Discord] Split into {len(chunks)} message chunks.")
            for i, chunk in enumerate(chunks):
                logger.info(f"[Dry-Run Discord] Chunk {i+1} Sample:\n{chunk[:200]}...")
            logger.info("----------------------------------------------------")
            return True

        # Send chunks sequentially using httpx with rate limit checks
        async with httpx.AsyncClient() as client:
            for idx, chunk in enumerate(chunks):
                await self._post_with_rate_limit(client, webhook_url, chunk, idx + 1, len(chunks))

        logger.info(f"Successfully sent {len(chunks)} messages to Discord.")
        return True

    async def _post_with_rate_limit(
        self,
        client: httpx.AsyncClient,
        url: str,
        content: str,
        chunk_num: int,
        total_chunks: int,
        max_attempts: int = 5
    ) -> None:
        payload = {
            "content": content
        }

        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = response.json().get("retry_after", 2.0)
                    logger.warning(
                        f"Discord Rate Limit hit. Attempt {attempt}/{max_attempts}. "
                        f"Sleeping for {retry_after}s before retrying..."
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return  # Successful post
            except httpx.HTTPStatusError as e:
                # If it's a 429 we already handled it in the continue, otherwise raise
                if e.response.status_code != 429:
                    raise AdapterError(
                        f"Discord API returned HTTP {e.response.status_code} "
                        f"on chunk {chunk_num}/{total_chunks}: {e}"
                    ) from e
            except Exception as e:
                raise AdapterError(
                    f"Failed to post chunk {chunk_num}/{total_chunks} to Discord: {e}"
                ) from e

        raise AdapterError(
            f"Failed to post chunk {chunk_num}/{total_chunks} to Discord: "
            f"Rate limited repeatedly after {max_attempts} attempts."
        )

    def _chunk_message(self, text: str, limit: int = 1900) -> List[str]:
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
