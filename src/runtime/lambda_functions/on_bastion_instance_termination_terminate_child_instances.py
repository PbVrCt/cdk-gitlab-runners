from os import environ

from boto3 import client
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit

metrics = Metrics(
    service="gitlab_runners_cleanup", namespace="cdk_autoscaling_gitlab_runners"
)
tracer = Tracer(service="gitlab_runners_cleanup")
logger = Logger(service="gitlab_runners_cleanup")

aws_region = environ["AWS_REGION"]


@metrics.log_metrics(capture_cold_start_metric=True)
@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event, context):
    bastion_instance_id = event["detail"]["EC2InstanceId"]
    # Filter the instances that were spawned by the runner manager being terminated.
    ec2 = client("ec2")
    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "tag:{}".format("bastion_instance_id"),
                "Values": [bastion_instance_id],
            }
        ]
    )
    # Terminate said instances.
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            try:
                ec2.terminate_instances(InstanceIds=[instance["InstanceId"]])
            except ClientError as e:
                logger.exception(
                    f'Failed to terminate instance {instance["InstanceId"]}: {e.response["Error"]["Message"]}'
                )
    return {"statusCode": 200, "body": "Successfully handled event"}
