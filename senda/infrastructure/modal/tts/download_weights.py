from typing import Optional

import modal

from .common import MODEL_DIR, app, chatterbox_tts_weights_vol

download_image = (
    modal.Image.debian_slim()
    .pip_install("huggingface_hub")
    .env({"HF_XET_HIGH_PERFORMANCE": "1", "HF_HOME": "/models"})
)


@app.function(
    image=download_image,
    volumes={MODEL_DIR: chatterbox_tts_weights_vol},
    secrets=[modal.Secret.from_name("hf-token")],
    timeout=1800,
)
def download_model(
    repo_id: str = "ResembleAI/chatterbox-turbo", revision: Optional[str] = None
) -> None:
    """Download model weights from Hugging Face Hub to the cache volume."""
    from huggingface_hub import snapshot_download

    print(
        f"Downloading weights for {repo_id} (revision: {revision or 'latest'}) to volume cache..."
    )
    snapshot_download(repo_id=repo_id, revision=revision)

    print("Committing weights volume...")
    chatterbox_tts_weights_vol.commit()
    print("Model weights cached successfully!")
