from constructs import Construct
from aws_cdk import Stack, Environment

from src.stacks.cache_bucket.s3.infrastructure import Bucket


class CacheBucket(Stack):
    @property
    def bucket_name(self):
        return self._bucket.bucket_name

    @property
    def bucket_arn(self):
        return self._bucket.bucket_arn

    def __init__(self, scope: Construct, id: str, env: Environment, **kwargs) -> None:
        super().__init__(scope, id, env=env, **kwargs)

        self._bucket = Bucket(self, "S3Bucket")
