from constructs import Construct
from aws_cdk import (
    Stack,
    Environment,
    aws_iam as iam,
    aws_logs as logs,
    CustomResource,
    custom_resources as cr,
)

from src.stacks.vpc.ec2.infrastructure import Vpc_
from src.stacks.vpc.aws_lambda.infrastructure import LambdaFunctions


class Vpc(Stack):
    @property
    def vpc(self):
        return self.vpc_.vpc

    @property
    def expose_port_22(self):
        return self._expose_port_22

    def __init__(
        self,
        scope: Construct,
        id: str,
        env: Environment,
        use_nat_gateways: bool,
        expose_port_22: bool = False,
        **kwargs
    ) -> None:
        super().__init__(scope, id, env=env, **kwargs)

        self._expose_port_22 = expose_port_22
        
        # Infrastructure

        self.vpc_ = Vpc_(self, "Vpc", use_nat_gateways, expose_port_22)

        self.lambda_functions = LambdaFunctions(
            self, "LambdaFunctions", self.vpc_.vpc.vpc_id
        )

        # Trigger a cleanup lambda when this stack is being deleted, using a custom resource 

        provider = cr.Provider(
            self,
            "Provider",
            on_event_handler=self.lambda_functions.on_vpc_stack_deletion_delete_vpc_dependencies_function,
            log_retention=logs.RetentionDays.ONE_DAY,
        )

        provider.on_event_handler.role.add_to_policy(
            iam.PolicyStatement(
                actions=["ec2:TerminateInstances"],
                resources=["*"],
            )
        )

        CustomResource(
            self,
            "TerminateInstancesCustomResource",
            properties={
                "vpc_id": self.vpc_.vpc.vpc_id,
            },
            service_token=provider.service_token,
        )
