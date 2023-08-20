from constructs import Construct
from aws_cdk import RemovalPolicy, aws_s3 as s3, Duration


class Bucket(Construct):
    @property
    def bucket_name(self):
        return self._bucket.bucket_name

    @property
    def bucket_arn(self):
        return self._bucket.bucket_arn

    def __init__(self, scope: Construct, id_: str, **kwargs):
        super().__init__(scope, id_, **kwargs)

        self._bucket = s3.Bucket(
            self,
            "bucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_policy=True, block_public_acls=True
            ),
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Add a lifecycle rule to delete cached objects after 5 days
        self._bucket.add_lifecycle_rule(
            id="ClearCacheBucketObjectsAfterExpiration", expiration=Duration.days(5)
        )
