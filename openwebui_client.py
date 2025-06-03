# openwebui_client.py
import httpx
import time
import logging
from typing import Any, Dict, List, Optional
from config import settings

logger = logging.getLogger(__name__)

class OpenWebUIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")  # Remove trailing slash if present
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_models(self) -> List[Dict[str, Any]]:
        """Fetches the list of available models from OpenWebUI."""
        url = f"{self.base_url}/api/models"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                models = data.get("data", data)
                if not isinstance(models, list):
                    models = []
                return models
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching models: {e}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error fetching models: {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching models: {e}")
            return []

class ModelManager:
    def __init__(self, client: OpenWebUIClient, cache_duration: int, 
                 whitelist: Optional[List[str]] = None, blacklist: Optional[List[str]] = None):
        self.client = client
        self.cache_duration = cache_duration
        self.whitelist = set(whitelist) if whitelist else None
        self.blacklist = set(blacklist) if blacklist else None
        self._cached_models: List[Dict[str, Any]] = []
        self._cache_timestamp: float = 0

    async def get_available_agents(self) -> List[Dict[str, Any]]:
        """
        Fetches, filters, and caches the list of available OpenWebUI models
        that qualify as 'Workspace' agents.
        """
        current_time = time.time()
        if not self._cached_models or (current_time - self._cache_timestamp) > self.cache_duration:
            logger.info("Cache expired or empty, fetching models from OpenWebUI.")
            all_models = await self.client.get_models()
            workspace_models = self._filter_workspace_models(all_models)
            self._cached_models = self._apply_whitelist_blacklist(workspace_models)
            self._cache_timestamp = current_time
            logger.info(f"Cached {len(self._cached_models)} available agents.")
        else:
            logger.debug("Using cached model list.")
        return self._cached_models

    def _filter_workspace_models(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters models to include only those with the 'info' field."""
        return [model for model in models if "info" in model]

    def _apply_whitelist_blacklist(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Applies whitelist and blacklist filtering to the model list."""
        filtered_models = []
        for model in models:
            model_id = model.get("id")
            if not model_id:
                continue
            # Apply blacklist (blacklist takes precedence)
            if self.blacklist and model_id in self.blacklist:
                logger.debug(f"Model {model_id} is in blacklist, excluding.")
                continue
            # Apply whitelist
            if self.whitelist and model_id not in self.whitelist:
                logger.debug(f"Model {model_id} is not in whitelist, excluding.")
                continue
            # If not blacklisted and passes whitelist (or no whitelist), include
            filtered_models.append(model)
        return filtered_models

    async def list_model_names(self) -> List[str]:
        """Returns a simple list of model IDs for available agents."""
        models = await self.get_available_agents()
        return [model.get("id") for model in models if model.get("id")]

# Create the client and model manager instances
openwebui_client = OpenWebUIClient(settings.OPENWEBUI_URL, settings.OPENWEBUI_API_KEY)
model_manager = ModelManager(
    openwebui_client,
    settings.CACHE_DURATION_SECONDS,
    settings.AGENT_WHITELIST,
    settings.AGENT_BLACKLIST
)