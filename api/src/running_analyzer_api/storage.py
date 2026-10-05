"""S3-compatible object storage: presigned URLs so video bytes never pass through the API."""

from __future__ import annotations

import boto3
from botocore.client import Config

from .settings import settings


def _client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


# Internal client for the API's own calls; the public one signs URLs the browser can reach.
internal = _client(settings.s3_endpoint)
public = _client(settings.s3_public_endpoint)


def video_key(session_id, view: str) -> str:
    return f"sessions/{session_id}/{view}.mp4"


def presign_upload(key: str, content_type: str = "video/mp4", expires: int = 3600) -> str:
    return public.generate_presigned_url(
        "put_object", Params={"Bucket": settings.s3_bucket, "Key": key, "ContentType": content_type}, ExpiresIn=expires
    )


def presign_download(key: str, expires: int = 3600) -> str:
    return public.generate_presigned_url("get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=expires)


def presign_download_internal(key: str, expires: int = 600) -> str:
    """For the API's own tools (ffprobe), reachable on the internal network."""
    return internal.generate_presigned_url("get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=expires)


def head(key: str) -> dict | None:
    try:
        return internal.head_object(Bucket=settings.s3_bucket, Key=key)
    except internal.exceptions.ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def delete(key: str) -> None:
    internal.delete_object(Bucket=settings.s3_bucket, Key=key)
