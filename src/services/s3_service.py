import boto3
from botocore.exceptions import NoCredentialsError
from fastapi import HTTPException
import string
import random


class S3Service:
    def __init__(self, bucket_name="senda-ai"):
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name

    def upload_file(self, file_path: str, object_name: str):
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            return f"https://{self.bucket_name}.s3.amazonaws.com/{object_name}"
        except NoCredentialsError as e:
            raise HTTPException(
                status_code=500, detail="AWS credentials not found."
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error uploading to S3: {e}"
            ) from e

    def get_presigned_url(self, object_name: str, expiration: int = 3600):
        try:
            response = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )
            return response
        except NoCredentialsError as e:
            raise HTTPException(
                status_code=500, detail="AWS credentials not found."
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating presigned URL: {e}"
            ) from e

    def generate_s3_safe_random_string_random(self, length: int = 10):
        """
        Generates an S3-safe random string using the random module.
        """
        alphabet = string.ascii_letters + string.digits
        random_string = "".join(random.choices(alphabet, k=length))

        return random_string
