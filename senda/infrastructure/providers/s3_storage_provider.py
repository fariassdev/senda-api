"""S3 storage provider implementation for audio file uploads."""

import logging
import secrets
import string
from typing import BinaryIO

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from senda.core.exceptions import StorageProviderException
from senda.domain.services.audio_generation import IStorageProvider

logger = logging.getLogger(__name__)


class S3StorageProvider(IStorageProvider):
    """AWS S3 storage provider for uploading audio files.

    This provider handles uploading audio files to AWS S3 and generating
    public URLs for accessing the uploaded files.
    """

    def __init__(
        self,
        bucket_name: str = "senda-ai",
        region: str = "us-east-1",
        audio_prefix: str = "audio/",
    ) -> None:
        """Initialize the S3 storage provider.

        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region for the bucket
            audio_prefix: Prefix path for audio files in the bucket
        """
        self._bucket_name = bucket_name
        self._region = region
        self._audio_prefix = audio_prefix
        self._session = aioboto3.Session()

        logger.info(
            f"Initialized S3StorageProvider with bucket={bucket_name}, region={region}"
        )

    def _generate_random_string(self, length: int = 10) -> str:
        """Generate a random string for unique filenames.

        Args:
            length: Length of the random string

        Returns:
            Random alphanumeric string
        """
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text to be safe for filenames.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized filename-safe string
        """
        safe_text = text.replace(" ", "_")
        safe_text = "".join(c for c in safe_text if c.isalnum() or c in ("_", "-"))
        return safe_text[:50]

    async def upload_audio(
        self, file_data: bytes, lesson_id: int, lesson_title: str
    ) -> str:
        """Upload audio file to S3 and return public URL.

        Args:
            file_data: Audio file data to upload
            lesson_id: ID of the lesson for filename generation
            lesson_title: Title of the lesson for filename generation

        Returns:
            Public URL of the uploaded audio file

        Raises:
            StorageProviderException: If upload fails
        """
        if not file_data:
            logger.warning("Empty file data provided for upload")
            raise StorageProviderException(message="Cannot upload empty file")

        safe_title = self._sanitize_filename(lesson_title)
        random_suffix = self._generate_random_string()
        filename = f"{lesson_id}_{safe_title}_{random_suffix}.mp3"
        object_key = f"{self._audio_prefix}{filename}"

        logger.info(f"Uploading audio file to S3: {object_key}")

        try:
            async with self._session.client(
                "s3", region_name=self._region
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=self._bucket_name,
                    Key=object_key,
                    Body=file_data,
                    ContentType="audio/mpeg",
                )

            public_url = f"https://{self._bucket_name}.s3.amazonaws.com/{object_key}"
            logger.info(f"Successfully uploaded audio file: {public_url}")
            return public_url

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"S3 client error during upload: {error_code} - {e}")

            if error_code == "NoSuchBucket":
                raise StorageProviderException(
                    message=f"S3 bucket '{self._bucket_name}' does not exist"
                ) from e
            elif error_code in ("AccessDenied", "InvalidAccessKeyId"):
                raise StorageProviderException(
                    message="S3 access denied - check credentials"
                ) from e
            else:
                raise StorageProviderException(
                    message=f"S3 upload failed: {error_code}"
                ) from e

        except BotoCoreError as e:
            logger.error(f"Boto core error during upload: {e}")
            raise StorageProviderException(
                message="S3 service error - check configuration"
            ) from e

        except Exception as e:
            logger.exception(f"Unexpected error during S3 upload: {e}")
            raise StorageProviderException(
                message=f"Audio upload failed: {str(e)}"
            ) from e

    async def upload_file(self, file_data: bytes, key: str, content_type: str) -> str:
        """Upload a generic file to S3 and return its public URL."""
        if not file_data:
            logger.warning("Empty file data provided for upload")
            raise StorageProviderException(message="Cannot upload empty file")

        logger.info(f"Uploading file to S3: {key} (type: {content_type})")

        try:
            async with self._session.client(
                "s3", region_name=self._region
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=self._bucket_name,
                    Key=key,
                    Body=file_data,
                    ContentType=content_type,
                )

            public_url = f"https://{self._bucket_name}.s3.amazonaws.com/{key}"
            logger.info(f"Successfully uploaded file to S3: {public_url}")
            return public_url

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(f"S3 client error during upload: {error_code} - {e}")
            raise StorageProviderException(
                message=f"S3 upload failed: {error_code}"
            ) from e
        except BotoCoreError as e:
            logger.error(f"Boto core error during upload: {e}")
            raise StorageProviderException(
                message="S3 service error - check configuration"
            ) from e
        except Exception as e:
            logger.exception(f"Unexpected error during S3 upload: {e}")
            raise StorageProviderException(
                message=f"File upload failed: {str(e)}"
            ) from e
