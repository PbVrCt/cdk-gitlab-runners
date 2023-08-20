from constructs import Construct
from aws_cdk import aws_ec2 as ec2


class Vpc_(Construct):
    @property
    def vpc(self):
        return self._vpc

    def __init__(
        self,
        scope: Construct,
        id: str,
        use_nat_gateways: bool,
        expose_port_22: bool,
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        """NOTE:
        By default the CDK creates a Security group that does not allow inbound traffic.
        By default the CDK creates the Internet gateway, and one Nat gateway per availability zone
        By default the CDK creates NetworkACLs (for the subnets) that allow all inbound and outbound traffic.
        By default the CDK creates a route table for each subnet, connecting it either to a NAT Gateway or the Internet Gateway.
        By default the CDK allocates the 10.0.0.0/16 address range, exhaustively spread across all subnets in the subnet configuration.
        """

        if use_nat_gateways:
            self._vpc = ec2.Vpc(
                self,
                "Vpc",
                max_azs=2,
                enable_dns_hostnames=True,
                enable_dns_support=True,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="PublicSubnet",
                        subnet_type=ec2.SubnetType.PUBLIC,
                    ),
                    ec2.SubnetConfiguration(
                        name="PrivateSubnet",
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    ),
                ],
            )
        else:
            self._vpc = ec2.Vpc(
                self,
                "Vpc",
                max_azs=2,
                nat_gateways=0,
                enable_dns_hostnames=True,
                enable_dns_support=True,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="PublicSubnet",
                        subnet_type=ec2.SubnetType.PUBLIC,
                    )
                ],
            )

        # VPC security group

        security_group = ec2.SecurityGroup(
            self, "SecurityGroup", vpc=self.vpc, allow_all_outbound=True
        )
        if expose_port_22:
            security_group.add_ingress_rule(
                peer=ec2.Peer.any_ipv4(),
                connection=ec2.Port.tcp(22),
                description="For the developper to ssh into the parent instance",
            )
        
        # S3 Gateway endpoint
            
        self._vpc.add_gateway_endpoint(
            "S3GatewayEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )