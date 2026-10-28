import pytest

from app.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        openai_api_key="test",
        upload_dir=str(tmp_path / "uploads"),
        embedding_dim=32,
        _env_file=None,
    )
