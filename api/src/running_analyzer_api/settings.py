from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    auth_internal_url: str = "http://auth:9999"
    s3_endpoint: str
    s3_public_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    web_url: str
    pipeline_version: str = "2026.10-prototype"
    # Only the Playback Video is kept after the Analysis (ADR 0008), so long uploads cost no lasting storage.
    max_video_bytes: int = 1024 * 1024 * 1024


settings = Settings()
