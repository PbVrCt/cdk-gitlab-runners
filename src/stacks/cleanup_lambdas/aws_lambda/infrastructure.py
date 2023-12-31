from constructs import Construct
from aws_cdk import Duration


from aws_lambda_shared.aws_lambda_construct import LambdaPython


class LambdaFunctions(Construct):
    @property
    def on_bastion_instance_termination_terminate_child_instances_function(self):
        return self._on_bastion_instance_termination_terminate_child_instances.function

    @property
    def on_bastion_instance_stack_deletion_terminate_child_instances_function(self):
        return (
            self._on_bastion_instance_stack_deletion_terminate_child_instances.function
        )

    def __init__(self, scope: Construct, id_: str, **kwargs):
        super().__init__(scope, id_, **kwargs)

        # NOTE:
        # These lambdas should be inside the BastionInstance() stack.
        # At some point I had trouble triggering them from that stack, so I placed them here.
        # At this point I don't plan to move them, and test that they work once again, because I have not set up automated tests.

        self._on_bastion_instance_termination_terminate_child_instances = LambdaPython(
            self,
            "OnBastionInstanceTerminationTerminateChildInstances",
            handler_filepath="src/runtime/lambda_functions/on_bastion_instance_termination_terminate_child_instances.py",
            env_vars={},
            timeout=Duration.seconds(27),
        ).add_policy(
            ["ec2:DescribeInstances", "ec2:TerminateInstances"],
            ["*"],
        )

        self._on_bastion_instance_stack_deletion_terminate_child_instances = LambdaPython(
            self,
            "OnBastionInstanceStackDeletionTerminateChildInstances",
            handler_filepath="src/runtime/lambda_functions/on_bastion_instance_stack_deletion_terminate_child_instances.py",
            env_vars={},
            timeout=Duration.seconds(27),
        ).add_policy(
            ["ec2:DescribeInstances", "ec2:TerminateInstances"],
            ["*"],
        )
