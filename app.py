import json

from constructs import Construct
from aws_cdk import App, Environment, Stage, Tags, aws_ec2 as ec2, aws_iam as iam

from src.stacks.vpc.component import Vpc
from src.stacks.cache_bucket.component import CacheBucket
from src.stacks.cleanup_lambdas.component import CleanupLambdas
from src.stacks.bastion_instance.component import BastionInstance

app = App()

# Configuration

with open("./src/config/config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
    project_name = config["project_name"]

worker_registration = {
    "config_file": "src/config/docker_machine_example.toml",
    "token_secret_name": config["token_secret_name"],
}

# Infrastructure (CDK stacks)


class AppStage(Stage):
    def __init__(
        self, scope: Construct, id_: str, env: Environment, outdir=None, **kwargs
    ):
        super().__init__(scope, id_, env=env, outdir=outdir, **kwargs)

        vpc_stack = Vpc(
            self,
            f"{project_name}Vpc",
            env=env,
            use_nat_gateways=config["use_nat_gateways"],
            expose_port_22=False,
        )

        cache_bucket_stack = CacheBucket(self, f"{project_name}CacheBucket", env=env)

        cleanup_lambdas_stack = CleanupLambdas(
            self, f"{project_name}CleanupLambdas", env=env
        )

        BastionInstance(
            self,
            f"{project_name}BastionInstance",
            env=env,
            vpc=vpc_stack.vpc,
            cache_bucket_name=cache_bucket_stack.bucket_name,
            cache_bucket_arn=cache_bucket_stack.bucket_arn,
            cleanup_lambda_on_stack_deletion=cleanup_lambdas_stack.on_bastion_instance_stack_deletion_terminate_child_instances_function,
            cleanup_lambda_on_instance_termination=cleanup_lambdas_stack.on_bastion_instance_termination_terminate_child_instances_function,
            instance_size=ec2.InstanceSize.NANO,  # Adjust between NANO, MICRO and SMALL based on the number of concurrent jobs.
            max_concurrent_jobs_across_workers=40,  # More than 40: SMALL, Less than 40: NANO or MICRO.
            worker_registrations=[worker_registration],
            ssh_key_pair_name="SSHKey",
            instance_security_group_expose_port_22=True,
        )

        # Add tags to all app resources
        Tags.of(self).add(key="ProjectName", value=config["project_name"])
        Tags.of(self).add(key="StageName", value=self.stage_name)


# Deployment

prod_env = Environment(account=config["account_id"], region=config["region"])
AppStage(app, "prod", env=prod_env)

# Required boilerplate

app.synth()
