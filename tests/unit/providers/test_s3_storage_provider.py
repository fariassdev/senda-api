"""Unit tests for S3 storage provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from senda.core.exceptions import StorageProviderException
from senda.infrastructure.providers.s3_storage_provider import S3StorageProvider


class TestS3StorageProvider:
    """Test suite for S3StorageProvider."""

    @pytest.fixture
    def storage_provider(self) -> S3StorageProvider:
        """Create an S3StorageProvider instance."""
        return S3StorageProvider(
            bucket_name="test-bucket", region="us-east-1", audio_prefix="audio/"
        )

    @pytest.fixture
    def sample_audio_data(self) -> bytes:
        """Sample MP3 audio data."""
        return b"fake_mp3_audio_data" * 50

    @pytest.mark.asyncio
    async def test_initialization(self, storage_provider):
        """Test provider initialization with correct parameters."""
        assert storage_provider._bucket_name == "test-bucket"
        assert storage_provider._region == "us-east-1"
        assert storage_provider._audio_prefix == "audio/"

    def test_sanitize_filename(self, storage_provider):
        """Test filename sanitization."""
        assert storage_provider._sanitize_filename("Test Lesson") == "Test_Lesson"
        assert (
            storage_provider._sanitize_filename("Hello! @#$ World")
            == "Hello__World"  # Space -> "_", special chars removed, space -> "_" = 2 underscores
        )
        assert storage_provider._sanitize_filename("Test_123-456") == "Test_123-456"
        assert (
            storage_provider._sanitize_filename("   spaces   ") == "___spaces___"
        )  # Space -> "_"

        long_name = "a" * 100
        assert len(storage_provider._sanitize_filename(long_name)) == 50

    def test_generate_random_string(self, storage_provider):
        """Test random string generation."""
        random_str1 = storage_provider._generate_random_string(10)
        random_str2 = storage_provider._generate_random_string(10)

        assert len(random_str1) == 10
        assert len(random_str2) == 10
        assert random_str1 != random_str2
        assert random_str1.isalnum()
        assert random_str2.isalnum()

        random_str_long = storage_provider._generate_random_string(20)
        assert len(random_str_long) == 20

    @pytest.mark.asyncio
    async def test_upload_audio_success(self, storage_provider, sample_audio_data):
        """Test successful audio upload to S3."""
        lesson_id = 123
        lesson_title = "Introduction to Mindfulness"

        mock_s3_client = AsyncMock()
        mock_s3_client.put_object = AsyncMock()

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            result_url = await storage_provider.upload_audio(
                file_data=sample_audio_data,
                lesson_id=lesson_id,
                lesson_title=lesson_title,
            )

            assert result_url.startswith("https://test-bucket.s3.amazonaws.com/audio/")
            assert f"{lesson_id}_" in result_url
            assert "Introduction_to_Mindfulness" in result_url
            assert result_url.endswith(".mp3")

            mock_s3_client.put_object.assert_called_once()
            call_kwargs = mock_s3_client.put_object.call_args.kwargs
            assert call_kwargs["Bucket"] == "test-bucket"
            assert call_kwargs["Key"].startswith("audio/")
            assert call_kwargs["Body"] == sample_audio_data
            assert call_kwargs["ContentType"] == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_upload_audio_empty_file(self, storage_provider):
        """Test error when file data is empty."""
        with pytest.raises(StorageProviderException) as exc_info:
            await storage_provider.upload_audio(
                file_data=b"", lesson_id=1, lesson_title="Test"
            )

        assert "empty file" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_audio_no_such_bucket(
        self, storage_provider, sample_audio_data
    ):
        """Test error when S3 bucket does not exist."""
        mock_s3_client = AsyncMock()
        error_response = {"Error": {"Code": "NoSuchBucket"}}
        mock_s3_client.put_object.side_effect = ClientError(error_response, "PutObject")

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            with pytest.raises(StorageProviderException) as exc_info:
                await storage_provider.upload_audio(
                    file_data=sample_audio_data, lesson_id=1, lesson_title="Test"
                )

            assert "does not exist" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_audio_access_denied(
        self, storage_provider, sample_audio_data
    ):
        """Test error when S3 access is denied."""
        mock_s3_client = AsyncMock()
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_s3_client.put_object.side_effect = ClientError(error_response, "PutObject")

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            with pytest.raises(StorageProviderException) as exc_info:
                await storage_provider.upload_audio(
                    file_data=sample_audio_data, lesson_id=1, lesson_title="Test"
                )

            assert "access denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_audio_invalid_access_key(
        self, storage_provider, sample_audio_data
    ):
        """Test error when AWS access key is invalid."""
        mock_s3_client = AsyncMock()
        error_response = {"Error": {"Code": "InvalidAccessKeyId"}}
        mock_s3_client.put_object.side_effect = ClientError(error_response, "PutObject")

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            with pytest.raises(StorageProviderException) as exc_info:
                await storage_provider.upload_audio(
                    file_data=sample_audio_data, lesson_id=1, lesson_title="Test"
                )

            assert "access denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_audio_generic_client_error(
        self, storage_provider, sample_audio_data
    ):
        """Test generic S3 client error handling."""
        mock_s3_client = AsyncMock()
        error_response = {"Error": {"Code": "InternalError"}}
        mock_s3_client.put_object.side_effect = ClientError(error_response, "PutObject")

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            with pytest.raises(StorageProviderException) as exc_info:
                await storage_provider.upload_audio(
                    file_data=sample_audio_data, lesson_id=1, lesson_title="Test"
                )

            assert "InternalError" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_audio_botocore_error(
        self, storage_provider, sample_audio_data
    ):
        """Test BotoCore error handling."""
        mock_s3_client = AsyncMock()
        mock_s3_client.put_object.side_effect = BotoCoreError()

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            with pytest.raises(StorageProviderException) as exc_info:
                await storage_provider.upload_audio(
                    file_data=sample_audio_data, lesson_id=1, lesson_title="Test"
                )

            assert "service error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_audio_unexpected_error(
        self, storage_provider, sample_audio_data
    ):
        """Test unexpected error handling."""
        mock_s3_client = AsyncMock()
        mock_s3_client.put_object.side_effect = ValueError("Unexpected error")

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            with pytest.raises(StorageProviderException) as exc_info:
                await storage_provider.upload_audio(
                    file_data=sample_audio_data, lesson_id=1, lesson_title="Test"
                )

            assert "upload failed" in str(exc_info.value).lower()

    def test_public_url_for_key_uses_cdn_when_configured(self) -> None:
        provider = S3StorageProvider(
            bucket_name="test-bucket",
            region="us-east-1",
            cdn_base_url="https://cdn.senda.com",
        )
        assert (
            provider.public_url_for_key("audio/1/job/playlist.m3u8")
            == "https://cdn.senda.com/audio/1/job/playlist.m3u8"
        )

    @pytest.mark.asyncio
    async def test_upload_file_sets_cache_control(self, storage_provider) -> None:
        mock_s3_client = AsyncMock()
        mock_s3_client.put_object = AsyncMock()

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            await storage_provider.upload_file(
                file_data=b"segment",
                key="audio/1/job/segment_000.ts",
                content_type="video/mp2t",
                cache_control="public, max-age=31536000",
            )

        call_kwargs = mock_s3_client.put_object.call_args.kwargs
        assert call_kwargs["CacheControl"] == "public, max-age=31536000"
        assert call_kwargs["ContentType"] == "video/mp2t"

    @pytest.mark.asyncio
    async def test_upload_audio_filename_structure(
        self, storage_provider, sample_audio_data
    ):
        """Test that generated filename has correct structure."""
        mock_s3_client = AsyncMock()
        mock_s3_client.put_object = AsyncMock()

        with patch.object(storage_provider._session, "client") as mock_client_context:
            mock_client_context.return_value.__aenter__.return_value = mock_s3_client

            result_url = await storage_provider.upload_audio(
                file_data=sample_audio_data,
                lesson_id=456,
                lesson_title="Advanced Meditation",
            )

            assert "456_Advanced_Meditation_" in result_url
            parts = result_url.split("_")
            assert len(parts) >= 4

            random_suffix = parts[-1].replace(".mp3", "")
            assert len(random_suffix) == 10
            assert random_suffix.isalnum()
