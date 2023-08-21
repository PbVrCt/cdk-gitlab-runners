"""
Generic helper construct to define lambda functions.
Consider replacing it by the CDK 'PythonFunction' L2 construct when it comes out.
Or moving to the SST framework, as it has better support for developing lambdas.
"""

import os

from typing import Union

from constructs import Construct
from aws_cdk import aws_lambda, aws_iam as iam, Duration, Aws


class LambdaPython(Construct):
    @property
    def function(self):
        return self._function

    def __init__(
        self,
        scope: Construct,
        id_: str,
        handler_filepath: str,
        env_vars: Union[dict[str, str], None] = None,
        memory_size=128,
        timeout=Duration.seconds(3),
        layer_names: list[str] = None,
        **kwargs,
    ):
        super().__init__(scope, id_, **kwargs)

        # Lambda layers definition

        powertools_layer = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            f"arn:aws:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV2:26",
        )

        # An example layer is commented out below.
        # If you would like to add your own layers, additionally you would have to zip them into this repository.

        # requests_layer = aws_lambda.LayerVersion(
        #     self,
        #     "RequestsLayer",
        #     code=aws_lambda.Code.from_asset(
        #         os.path.join(
        #             "aws_lambda_shared/aws_lambda_layers/requests_2_29/",
        #             "requests_2_29.zip",
        #         )
        #     ),
        #     compatible_runtimes=[
        #         aws_lambda.Runtime.PYTHON_3_8,
        #         aws_lambda.Runtime.PYTHON_3_9,
        #     ],
        #     license="BSD 3",
        #     description="requests library, version 2.29.0 . Later versions resulted in a packages versioning problem",
        # )

        # valid_layer_names = ["lambda_powertools", "requests"]
        valid_layer_names = ["lambda_powertools"]

        # Lambda layers validation

        layers = []

        if layer_names is not None:
            assert set(layer_names).issubset(
                valid_layer_names
            ), "Error: Invalid layer. Valid layers are: 'lambda_powertools, requests'. See aws_lambda_constructs.py for more details."

            # if "requests" in layer_names:
            #     layers.append(requests_layer)

        layers.append(powertools_layer)

        # Lambda definition

        handler_filepath_no_extension, _ = os.path.splitext(handler_filepath)
        handler_filename_no_extension = os.path.basename(handler_filepath_no_extension)
        handler_directory = os.path.dirname(handler_filepath)

        self._function = aws_lambda.Function(
            self,
            id_,
            function_name=id_.replace("_", "-"),
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_asset(handler_directory),
            handler=f"{handler_filename_no_extension}.handler",
            memory_size=memory_size,
            timeout=timeout,
            layers=layers,
            environment=env_vars,
        )

        self._id = id_

    # Method to grant inline policies

    def add_policy(self, actions: list[str], resources: list[str]):
        policy_name = self._id + "-".join(actions)
        policy_name = (
            policy_name.replace(":", "-").replace("/", "-").replace("*", "_")[:128]
        )
        # NOTE: The resouce arns are defined at deployment time, so I did not add them to the policy name.

        self._function.role.attach_inline_policy(
            iam.Policy(
                self,
                policy_name,
                policy_name=policy_name,
                statements=[
                    iam.PolicyStatement(
                        actions=actions,
                        resources=resources,
                    )
                ],
            )
        )
        return self
