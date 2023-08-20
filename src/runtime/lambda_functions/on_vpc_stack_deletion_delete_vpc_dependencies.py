from boto3 import client, resource
from botocore.exceptions import ClientError

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit

metrics = Metrics(
    service="gitlab_runners_cleanup", namespace="cdk_autoscaling_gitlab_runners"
)
tracer = Tracer(service="gitlab_runners_vpc_deletion")
logger = Logger(service="gitlab_runners_vpc_deletion")


@metrics.log_metrics(capture_cold_start_metric=True)
@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(event, context):
    # Execute the following code only when the stack is being deleted.
    if event["RequestType"] == "Delete":
        vpc_id = event["ResourceProperties"]["vpc_id"]
        ec2 = client("ec2")
        ec2_resource = resource("ec2")
        # Terminate the EC2 instances.
        response = ec2.describe_instances(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                try:
                    ec2.terminate_instances(InstanceIds=[instance["InstanceId"]])
                except ClientError as e:
                    logger.exception(
                        f'Failed to terminate instance {instance["InstanceId"]}: {e.response["Error"]["Message"]}'
                    )
        # Delete the subnets.
        subnets = ec2_resource.subnets.filter(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        for subnet in subnets:
            subnet.delete()
        # Delete the security groups.
        response = ec2.describe_security_groups(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )
        for sg in response["SecurityGroups"]:
            if sg["GroupName"] != "default":
                try:
                    ec2.delete_security_group(GroupId=sg["GroupId"])
                except ClientError as e:
                    logger.exception(
                        f'Failed to delete security group {sg["GroupId"]}: {e.response["Error"]["Message"]}'
                    )
        # Delete the NAT gateways.
        nat_gateways = ec2.describe_nat_gateways()["NatGateways"]
        for nat in nat_gateways:
            if nat["VpcId"] == vpc_id:
                try:
                    ec2.delete_nat_gateway(NatGatewayId=nat["NatGatewayId"])
                except ClientError as e:
                    logger.exception(
                        f'Failed to delete NAT gateway {nat["NatGatewayId"]}: {e.response["Error"]["Message"]}'
                    )
    return {"statusCode": 200, "body": "Successfully handled event"}
