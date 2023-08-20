from os import environ
from json import loads

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
    auto_scaling_group_name = event["ResourceProperties"]["bastion_instance_auto_scaling_group_name"]
    # Execute the following code only when the stack is being deleted.
    if event["RequestType"] == "Delete":
        # Filter the child instances that were spawned by runner managers which were registered in the bastion instance of the stack.
        ec2 = client("ec2")
        response = ec2.describe_instances(
            Filters=[
                {
                    "Name": "tag:{}".format("bastion_instance_auto_scaling_group_name"),
                    "Values": [auto_scaling_group_name],
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
