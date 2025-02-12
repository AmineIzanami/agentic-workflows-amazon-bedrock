PARAMS=(
  "RUNTIME_ENV=your_runtime_env"
  "SUPERVISOR_AGENT_ID=your_supervisor_agent_id"
  "SUPERVISOR_AGENT_ALIAS_ID=your_supervisor_agent_alias_id"
  "BEDROCK_REGION=your_bedrock_region"
  "RAG_BUCKET_NAME=your_rag_bucket_name"
  "SOW_BUCKET_NAME=your_sow_bucket_name"
  "LANGFUSE_PUBLIC_KEY=your_langfuse_public_key"
  "LANGFUSE_SECRET_KEY=your_langfuse_secret_key"
  "LANGFUSE_HOST=your_langfuse_host"
  "USER_POOL_ID=your_user_pool_id"
  "USER_POOL_CLIENT_ID=your_user_pool_client_id"
  "USER_POOL_CLIENT_SECRET=your_user_pool_client_secret"
  "USER_POOL_COGNITO_DOMAIN=your_user_pool_cognito_domain"
  "USER_POOL_REDIRECT_URI=your_user_pool_redirect_uri"
)

STREAMLIT_REGION=eu-west-3

for param in "${PARAMS[@]}"; do
  KEY="${param%%=*}"
  VALUE="${param#*=}"
  TYPE="String"

  if [[ "$KEY" == *"SECRET"* || "$KEY" == *"KEY" ]]; then
    TYPE="SecureString"
  fi

  aws ssm put-parameter --region $STREAMLIT_REGION --cli-input-json \
  "{\"Name\": \"/multiagent/streamlit/configuration/$KEY\", \"Value\": \"$VALUE\", \"Type\": \"$TYPE\", \"Overwrite\": true}"
done
