from constructs import Construct
from aws_cdk import Duration

from aws_lambda_shared.aws_lambda_construct import LambdaPython


class LambdaFunctions(Construct):
    @property
    def on_vpc_stack_deletion_delete_vpc_dependencies_function(self):
        return self._on_vpc_stack_deletion_delete_vpc_dependencies.function

    def __init__(self, scope: Construct, id_: str, vpc_id: str, **kwargs):
        super().__init__(scope, id_, **kwargs)

        self._on_vpc_stack_deletion_delete_vpc_dependencies = LambdaPython(
            self,
            "OnVpcStackDeletionDeleteVpcDependencies",
            handler_filepath="src/runtime/lambda_functions/on_vpc_stack_deletion_delete_vpc_dependencies.py",
            env_vars={"VPC_ID": vpc_id},
            timeout=Duration.seconds(27),
        ).add_policy(
            [
                "ec2:DescribeInstances",
                "ec2:TerminateInstances",
                "ec2:DescribeSubnets",
                "ec2:DeleteSubnet",
                "ec2:DescribeSecurityGroups",
                "ec2:DeleteSecurityGroup",
                "ec2:DescribeNatGateways",
                "ec2:DeleteNatGateway",
                "ec2:DescribeVpcs",
            ],
            ["*"],
        )
