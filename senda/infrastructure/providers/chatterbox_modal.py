"""Shared Modal.com configuration and auth for Chatterbox integrations."""

import base64
from dataclasses import dataclass

from senda.core.settings.base import BaseAppSettings


@dataclass(frozen=True)
class ChatterboxModalSettings:
    """Endpoint URLs and credentials for Chatterbox on Modal."""

    synthesize_endpoint: str
    sync_voice_endpoint: str
    delete_voice_endpoint: str
    token_id: str
    token_secret: str
    proxy_auth_token_id: str | None
    proxy_auth_token_secret: str | None
    timeout: float

    @classmethod
    def from_app_settings(cls, settings: BaseAppSettings) -> "ChatterboxModalSettings":
        return cls(
            synthesize_endpoint=settings.modal_tts_endpoint.rstrip("/"),
            sync_voice_endpoint=settings.modal_sync_voice_endpoint.rstrip("/"),
            delete_voice_endpoint=settings.modal_delete_voice_endpoint.rstrip("/"),
            token_id=settings.modal_token_id,
            token_secret=settings.modal_token_secret,
            proxy_auth_token_id=settings.modal_proxy_auth_token_id,
            proxy_auth_token_secret=settings.modal_proxy_auth_token_secret,
            timeout=settings.modal_tts_timeout,
        )

    def auth_headers(self, *, content_type: str = "application/json") -> dict[str, str]:
        credentials = base64.b64encode(
            f"{self.token_id}:{self.token_secret}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": content_type,
        }
        if self.proxy_auth_token_id and self.proxy_auth_token_secret:
            headers["Modal-Key"] = self.proxy_auth_token_id
            headers["Modal-Secret"] = self.proxy_auth_token_secret
        return headers
