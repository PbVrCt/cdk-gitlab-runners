from constructs import Construct
from aws_cdk import (
    Stack,
    Aws,
    Duration,
    aws_ec2 as ec2,
    aws_autoscaling as autoscaling,
    aws_iam as iam,
)


class EC2Instance(Construct):
    @property
    def auto_scaling_group(self):
        return self._auto_scaling_group

    @property
    def auto_scaling_group_name(self):
        return self._auto_scaling_group.auto_scaling_group_name

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        cache_bucket_name: str,
        cache_bucket_arn: str,
        instance_size: ec2.InstanceSize,
        max_concurrent_jobs_across_workers,
        worker_registrations: list[dict],
        ssh_key_pair_name: str,
        instance_security_group_expose_port_22: bool,
        managed_policies: list = [],
        inline_policies: dict = {},
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        # Validate the worker_registrations argument

        error = "The worker configurations argument must be formatted as in the readme"
        for c in worker_registrations:
            assert "token_secret_name" in c.keys(), error
            assert isinstance(c["token_secret_name"], str), error
            assert "config_file" in c.keys(), error
            assert isinstance(c["config_file"], str)
            if "child_runners_managed_policies" in c.keys():
                assert isinstance(c["child_runners_managed_policies"], list)
            else:
                c["child_runners_managed_policies"] = []
            if "child_runners_inline_policies" in c.keys():
                assert isinstance(c["child_runners_inline_policies"], dict) and all(
                    isinstance(k, str) and isinstance(v, iam.PolicyDocument)
                    for k, v in c["child_runners_inline_policies"].items()
                ), error
            else:
                c["child_runners_inline_policies"] = {}
            if "non_ecr_repositories" in c.keys():
                assert isinstance(c["non_ecr_repositories"], list) and all(
                    isinstance(c, dict)
                    and "repository" in c
                    and isinstance(c["repository"], str)
                    and "username" in c
                    and isinstance(c["username"], str)
                    and "password_secret_name" in c
                    and isinstance(c["password_secret_name"], str)
                    for c in c["non_ecr_repositories"]
                ), error
            else:
                c["non_ecr_repositories"] = []
            if "ecr_repositories" in c.keys():
                assert isinstance(c["ecr_repositories"], list) and all(
                    isinstance(r, str) for r in c["ecr_repositories"]
                ), error
            else:
                c["ecr_repositories"] = []

        # Role for the bastion instance

        managed_policies_base = [
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2FullAccess"),
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonEC2ContainerRegistryReadOnly"
            ),
        ]

        managed_policies.extend(managed_policies_base)

        inline_policies["BastionInstanceBasePolicies"] = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=["s3:*"],
                    resources=[cache_bucket_arn],
                ),
                iam.PolicyStatement(
                    actions=["ssm:GetParameter"],
                    resources=[
                        "arn:aws:ssm:{}:{}:*".format(Aws.REGION, Aws.ACCOUNT_ID)
                    ],
                ),
                iam.PolicyStatement(
                    actions=["iam:PassRole"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=["sts:GetServiceBearerToken"],
                    resources=["*"],
                ),
            ],
        )

        bastion_instance_role = iam.Role(
            self,
            "BastionInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=managed_policies,
            inline_policies=inline_policies,
        )

        # Roles for the child instances. Unused when the docker executor is employed.

        for i, _ in enumerate(worker_registrations):
            role_name = "{}ChildRunnersRole{}".format(Stack.of(self).stack_name, i)
            role_construct_id = "ChildRunnersRole{}".format(i)
            instance_profile_construct_id = "ChildRunnersInstanceProfile{}".format(i)

            worker_registrations[i]["child_runners_inline_policies"][
                "ChildRunnersBasePolicies"
            ] = iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=["s3:*"],
                        resources=[cache_bucket_arn],
                    ),
                ],
            )

            child_instances_role = iam.Role(
                self,
                role_construct_id,
                role_name=role_name,
                assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                managed_policies=worker_registrations[i][
                    "child_runners_managed_policies"
                ],
                inline_policies=worker_registrations[i][
                    "child_runners_inline_policies"
                ],
            )

            child_instances_instance_profile = iam.CfnInstanceProfile(
                self,
                instance_profile_construct_id,
                instance_profile_name=role_name,
                roles=[child_instances_role.role_name],
            )

            worker_registrations[i][
                "instance_profile"
            ] = child_instances_instance_profile

        # Bastion instance security group

        """NOTE:
        The runner manager in the bastion instance takes care of creating a new security group for the child instances.
        This security group includes an ingress rule on port TCP 2376, allowing the runner manager to use the Docker daemon API for communication.
        An ingress rule on port TCP 22 also exists; I suppose to enable developers to SSH into the child instances instances from the bastion instance.

        NOTE:
        Instance security groups and VPC security group are two distinct security groups.
        You can fin the specifications for the VPC security group in the VPC stack.
        """

        instance_security_group = ec2.SecurityGroup(
            self, "EC2SecurityGroup", vpc=vpc, allow_all_outbound=True
        )
        if instance_security_group_expose_port_22:
            instance_security_group.add_ingress_rule(
                peer=ec2.Peer.any_ipv4(),
                connection=ec2.Port.tcp(22),
                description="For the developer to ssh into the parent instance",
            )

        # Bastion instance initialization

        # Step 1: Install requirements

        initilization_steps = [
            ec2.InitFile.from_file_inline(
                "/etc/cdk_gitlab_runners/install_requirements.sh",
                "src/runtime/bastion_instance_initialization/install_requirements.sh",
            ),
            ec2.InitCommand.shell_command(
                "chmod +x /etc/cdk_gitlab_runners/install_requirements.sh"
            ),
            ec2.InitCommand.shell_command("cd /tmp"),
            ec2.InitCommand.shell_command(
                "/etc/cdk_gitlab_runners/install_requirements.sh"
            ),
        ]

        # Step 2: Register the workers

        initilization_steps.extend(
            [
                ec2.InitFile.from_object(
                    "/etc/cdk_gitlab_runners/number_of_workers.json",
                    {"NumberOfWorkers": len(worker_registrations)},
                ),
                ec2.InitFile.from_object(
                    "/etc/cdk_gitlab_runners/ec2_region.json",
                    {
                        "EC2Region": Aws.REGION,
                    },
                ),
            ]
        )

        for i, _ in enumerate(worker_registrations):
            initilization_steps.extend(
                [
                    ec2.InitFile.from_object(
                        "/etc/cdk_gitlab_runners/worker_config_{}.json".format(i),
                        {
                            "EcrRepositories": worker_registrations[i][
                                "ecr_repositories"
                            ],
                            "NonEcrRepositories": worker_registrations[i][
                                "non_ecr_repositories"
                            ],
                            "TokenSecretName": worker_registrations[i][
                                "token_secret_name"
                            ],
                            "CacheBucketName": cache_bucket_name,
                            "ChildRunnersInstancesVpcId": vpc.vpc_id,
                            "ChildRunnersInstancesInstanceProfileName": worker_registrations[
                                i
                            ][
                                "instance_profile"
                            ].instance_profile_name,
                        },
                    ),
                    ec2.InitFile.from_file_inline(
                        "/etc/cdk_gitlab_runners/config_{}.toml".format(i),
                        worker_registrations[i]["config_file"],
                    ),
                ]
            )

        initilization_steps.extend(
            [
                ec2.InitFile.from_file_inline(
                    "/etc/cdk_gitlab_runners/register_workers.sh",
                    "src/runtime/bastion_instance_initialization/register_workers.sh",
                ),
                ec2.InitFile.from_file_inline(
                    "/etc/cdk_gitlab_runners/authenticate_to_ecr.sh",
                    "src/runtime/bastion_instance_initialization/authenticate_to_ecr.sh",
                ),
                ec2.InitFile.from_file_inline(
                    "/etc/cdk_gitlab_runners/authenticate_to_non_ecr.sh",
                    "src/runtime/bastion_instance_initialization/authenticate_to_non_ecr.sh",
                ),
                ec2.InitCommand.shell_command(
                    "chmod +x /etc/cdk_gitlab_runners/authenticate_to_ecr.sh"
                ),
                ec2.InitCommand.shell_command(
                    "chmod +x /etc/cdk_gitlab_runners/authenticate_to_non_ecr.sh"
                ),
                ec2.InitCommand.shell_command(
                    "chmod +x /etc/cdk_gitlab_runners/register_workers.sh"
                ),
                ec2.InitCommand.shell_command(
                    "/etc/cdk_gitlab_runners/register_workers.sh"
                ),
            ]
        )

        # Step 3: Update job concurrency limit
        initilization_steps.extend(
            [
                ec2.InitFile.from_object(
                    "/etc/cdk_gitlab_runners/max_concurrent_jobs.json",
                    {"MaxConcurrentJobs": max_concurrent_jobs_across_workers},
                ),
                ec2.InitFile.from_file_inline(
                    "/etc/cdk_gitlab_runners/update_job_concurrency_limit.sh",
                    "src/runtime/bastion_instance_initialization/update_job_concurrency_limit.sh",
                ),
                ec2.InitCommand.shell_command(
                    "chmod +x /etc/cdk_gitlab_runners/update_job_concurrency_limit.sh"
                ),
                ec2.InitCommand.shell_command(
                    "/etc/cdk_gitlab_runners/update_job_concurrency_limit.sh"
                ),
            ]
        )

        # Cloudformation Init setup

        """NOTE:
        With Amazon Linux AMIs, Cloudformation Init comes enabled by default.
        As you are using an Ubuntu Server AMI, the user_data script below is required for the cloudformation_init script to function
        https://github.com/aws/aws-cdk/issues/9841#issuecomment-1025003320"""

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "sudo apt-get update -y",
            "sudo apt-get install -y epel-release",
            "sudo apt-get install -y python3 python3-pip",
            "sudo mkdir -p /opt/aws/bin",
            "sudo pip3 install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-py3-latest.tar.gz",
            "sudo ln -s /usr/local/bin/cfn* /opt/aws/bin",
        )

        cloudformation_init = ec2.CloudFormationInit.from_config_sets(
            config_sets={"default": ["install"]},
            configs={"install": ec2.InitConfig(initilization_steps)},
        )

        # Bastion instance

        if ssh_key_pair_name == "":
            self._auto_scaling_group = autoscaling.AutoScalingGroup(
                self,
                "AutosScalingGroup",
                vpc=vpc,
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.T4G,
                    instance_size,
                ),
                machine_image=ec2.MachineImage.from_ssm_parameter(
                    "/aws/service/canonical/ubuntu/server/20.04/stable/20210223/arm64/hvm/ebs-gp2/ami-id",
                    user_data=user_data,
                ),
                init=cloudformation_init,
                signals=autoscaling.Signals.wait_for_all(timeout=Duration.minutes(10)),
                role=bastion_instance_role,
                security_group=instance_security_group,
            )
        else:
            self._auto_scaling_group = autoscaling.AutoScalingGroup(
                self,
                "AutosScalingGroup",
                vpc=vpc,
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.T4G,
                    instance_size,
                ),
                machine_image=ec2.MachineImage.from_ssm_parameter(
                    "/aws/service/canonical/ubuntu/server/20.04/stable/20210223/arm64/hvm/ebs-gp2/ami-id",
                    user_data=user_data,
                ),
                init=cloudformation_init,
                signals=autoscaling.Signals.wait_for_all(timeout=Duration.minutes(10)),
                key_name=ssh_key_pair_name,
                role=bastion_instance_role,
                security_group=instance_security_group,
            )
