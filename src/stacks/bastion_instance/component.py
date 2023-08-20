from constructs import Construct
from aws_cdk import (
    Stack,
    Environment,
    aws_ec2 as ec2,
    aws_lambda,
    aws_iam as iam,
    aws_logs as logs,
    CustomResource,
    aws_autoscaling as autoscaling,
    custom_resources as cr,
)

from src.stacks.bastion_instance.ec2.infrastructure import EC2Instance
from src.stacks.bastion_instance.eventbridge.infrastructure import EventbridgeRule


class BastionInstance(Stack):
    @property
    def auto_scaling_group_name(self):
        return self._ec2_instance.auto_scaling_group_name

    @property
    def lifecycle_hook_name(self):
        return self._ec2_instance.lifecycle_hook_name

    def __init__(
        self,
        scope: Construct,
        id_: str,
        env: Environment,
        vpc: ec2.Vpc,
        cache_bucket_name: str,
        cache_bucket_arn: str,
        cleanup_lambda_on_stack_deletion: aws_lambda.Function,
        cleanup_lambda_on_instance_termination: aws_lambda.Function,
        instance_size: ec2.InstanceSize,
        max_concurrent_jobs_across_workers: int,
        worker_registrations: list[dict],
        ssh_key_pair_name: str = "",
        instance_security_group_expose_port_22: list = [],
        managed_policies: list = [],
        inline_policies: dict = {},
        **kwargs,
    ) -> None:
        super().__init__(scope, id_, env=env, **kwargs)

        # Infrastructure

        self._ec2_instance = EC2Instance(
            self,
            "EC2Instance",
            vpc,
            cache_bucket_name,
            cache_bucket_arn,
            instance_size,
            max_concurrent_jobs_across_workers,
            worker_registrations,
            ssh_key_pair_name,
            instance_security_group_expose_port_22,
            managed_policies,
            inline_policies,
        )

        # Trigger a cleanaup lambda when the bastion instance is being terminated, using a lifecycle hook and an eventbridge event

        self._lifecycle_hook = autoscaling.LifecycleHook(
            self,
            "LifecycleHook",
            auto_scaling_group=self._ec2_instance.auto_scaling_group,
            lifecycle_transition=autoscaling.LifecycleTransition.INSTANCE_TERMINATING,
        )

        EventbridgeRule(
            self,
            "Eventbridge",
            self._ec2_instance.auto_scaling_group_name,
            self._lifecycle_hook.lifecycle_hook_name,
            cleanup_lambda_on_instance_termination,
        )

        # Trigger a cleanup lambda when this stack is being deleted, using a custom resource

        provider = cr.Provider(
            self,
            "Provider",
            on_event_handler=cleanup_lambda_on_stack_deletion,
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
                "bastion_instance_auto_scaling_group_name": self._ec2_instance.auto_scaling_group_name,
            },
            service_token=provider.service_token,
        )
