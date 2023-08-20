import os
from typing import Union

from constructs import Construct
from aws_cdk import aws_lambda, aws_iam as iam, Duration, Aws


# Generic helper construct. Consider replacing it by the CDK 'PythonFunction' L2 construct when it comes out. Or move to the SST framework
class LambdaPython(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        handler_filepath: str,
        env_vars: Union[dict[str, str], None] = None,
        memory_size=128,
        timeout=Duration.seconds(3),
        layers: list[str] = [],
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        # Layers

        powertools_layer = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:{}:017000801446:layer:AWSLambdaPowertoolsPythonV2:26".format(
                Aws.REGION
            ),
        )

        # requests_2_29_layer = aws_lambda.LayerVersion(
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

        assert set(layers).issubset(
            ["lambda_powertools"]
        ), "Error: Invalid layer. Valid layers are: 'lambda_powertools'. See aws_lambda_constructs.py for more details."
        layers_ = [powertools_layer]
        # if "requests" in layers:
        #     layers_.append(requests_2_29_layer)

        # Lambda definition
        handler_filepath_no_extension, _ = os.path.splitext(handler_filepath)
        handler_filename_no_extension = os.path.basename(handler_filepath_no_extension)
        handler_directory = os.path.dirname(handler_filepath)

        self._id = id
        self.fn = aws_lambda.Function(
            self,
            self._id,
            function_name=self._id.replace("_", "-"),
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            code=aws_lambda.Code.from_asset(handler_directory),
            handler="{}.handler".format(handler_filename_no_extension),
            memory_size=memory_size,
            timeout=timeout,
            layers=layers_,
            environment=env_vars,
        )

    # Add policy method

    def add_policy(self, actions: list[str], resources: list[str], managed=False):
        policy_name = self._id + "-".join(
            actions
        )  # + "-".join(resources) ## "-".join(resources) does not work because the resouce arns are defined at deployment time
        policy_name = (
            policy_name.replace(":", "-").replace("/", "-").replace("*", "_")[:128]
        )
        self.fn.role.attach_inline_policy(
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
