from constructs import Construct
from aws_cdk import Stack, Environment

from src.stacks.cleanup_lambdas.aws_lambda.infrastructure import LambdaFunctions


class CleanupLambdas(Stack):
    @property
    def on_bastion_instance_stack_deletion_terminate_child_instances_function(self):
        return (
            self._lambda_functions.on_bastion_instance_stack_deletion_terminate_child_instances_function
        )

    @property
    def on_bastion_instance_termination_terminate_child_instances_function(self):
        return (
            self._lambda_functions.on_bastion_instance_termination_terminate_child_instances_function
        )

    def __init__(self, scope: Construct, id_: str, env: Environment, **kwargs) -> None:
        super().__init__(scope, id_, env=env, **kwargs)

        self._lambda_functions = LambdaFunctions(self, "LambdaFunctions")
