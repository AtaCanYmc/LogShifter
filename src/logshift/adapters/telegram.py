import json
import logging
from typing import Any, Dict, List
import httpx
from base import TransportAdapter
from logshift.core.exceptions import AdapterError

logger = logging.getLogger("logshift.adapters.telegram")


class TelegramAdapter(TransportAdapter):
    """
    TelegramAdapter posts log notifications to a Telegram chat using Telegram Bot API.
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        name: str = "telegram",
        config: Dict[str, Any] | None = None
    ) -> None:
        super().__init__(name, config)
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def ship(self, logs: List[Dict[str, Any]], target: str, **kwargs: Any) -> bool:
        """
        Ships logs to a Telegram chat.
        
        Args:
            logs: List of log dicts.
            target: Chat ID (fallback/override).
            **kwargs: Includes dry_run parameter.
        """
        dry_run = kwargs.get("dry_run", False)
        chat_id = target or self.chat_id

        if not self.bot_token or not chat_id:
            raise AdapterError("Telegram Bot Token and Chat ID are required.")

        # Format logs as a pretty JSON block
        content = json.dumps(logs, indent=2, ensure_ascii=False)
        message_text = f"📢 **Logshift Archive Notification**\n\n```json\n{content}\n```"

        # Telegram has a strict 4096 character limit
        chunks = self._chunk_message(message_text, limit=4000)

        if dry_run:
            logger.info("---------------- DRY-RUN SIMULATION ----------------")
            logger.info(f"[Dry-Run Telegram] Target Chat: {chat_id}")
            logger.info(f"[Dry-Run Telegram] Bot Token: {self.bot_token[:5]}...")
            logger.info(f"[Dry-Run Telegram] Split into {len(chunks)} message chunks.")
            for i, chunk in enumerate(chunks):
                logger.info(f"[Dry-Run Telegram] Chunk {i+1} Sample:\n{chunk[:200]}...")
            logger.info("----------------------------------------------------")
            return True

        # Send chunks sequentially using httpx
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient() as client:
            for idx, chunk in enumerate(chunks):
                payload = {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown",
                }
                try:
                    response = await client.post(url, json=payload, timeout=10.0)
                    response.raise_for_status()
                except Exception as e:
                    raise AdapterError(f"Telegram API request failed on chunk {idx+1}/{len(chunks)}: {e}") from e

        logger.info(f"Successfully sent {len(chunks)} messages to Telegram.")
        return True

    def _chunk_message(self, text: str, limit: int = 4000) -> List[str]:
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
