import aws_cdk as cdk

from streamlit_serverless_app.frontend_stack import FrontendStack

app = cdk.App()

app_env_vars = {
    "STREAMLIT_SERVER_PORT": "8501"
}
environment_name = "dev"
environment_configuration = app.node.try_get_context("DeploymentEnvironments").get(environment_name)

account_id = environment_configuration.get("ACCOUNT_ID")
cdk_region = environment_configuration.get("REGION")
resource_prefix = environment_configuration.get("RESOURCE_PREFIX")
tags = environment_configuration.get("STACK-TAGS")
vpc_id = environment_configuration.get("VPC_ID")
multi_agent_region = environment_configuration.get("MULTI_AGENT_SOLUTION_REGION")
env = cdk.Environment(account=account_id, region=cdk_region)
# Create the front-end Stack
frontend_stack = FrontendStack(app,
                               f"{resource_prefix}-streamlit",
                               env=env,
                               vpc_id=vpc_id,
                               multi_agent_region=multi_agent_region
                               )
for key_tag, value_tag in tags.items():
    cdk.Tags.of(frontend_stack).add(str(key_tag), str(value_tag))
app.synth()
