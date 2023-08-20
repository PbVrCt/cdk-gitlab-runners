from constructs import Construct
from aws_cdk import (
    aws_lambda,
    aws_events as events,
    aws_events_targets as targets,
)


class EventbridgeRule(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        auto_scaling_group_name: str,
        lifecycle_hook_name: str,
        cleanup_lambda: aws_lambda.Function,
        **kwargs,
    ):
        super().__init__(scope, id_, **kwargs)

        rule = events.Rule(
            self,
            "EventRule",
            event_pattern=events.EventPattern(
                source=["aws.autoscaling"],
                detail_type=["EC2 Instance-terminate Lifecycle Action"],
                detail={
                    "AutoScalingGroupName": [auto_scaling_group_name],
                    "LifecycleHookName": [lifecycle_hook_name],
                },
            ),
        )

        rule.add_target(targets.LambdaFunction(cleanup_lambda))
