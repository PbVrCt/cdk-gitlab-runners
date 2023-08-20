#!/bin/bash -xe
NUMBER_OF_WORKERS=$(cat /etc/cdk_gitlab_runners/number_of_workers.json | jq -r '.NumberOfWorkers')
EC2_REGION=$(cat /etc/cdk_gitlab_runners/ec2_region.json | jq -r '.EC2Region')

# 4. Prepare the worker configurations and register them on Gitlab Server

# Loop through the workers configuration
for (( i=0; i<$NUMBER_OF_WORKERS; i++ )); do

    CONFIG_FILE="/etc/cdk_gitlab_runners/config_${i}.toml"
    PARAMETERS_FILE="/etc/cdk_gitlab_runners/worker_config_${i}.json"

    # Authenticate to ECR repositores

    AUTHENTICATION_SCRIPT="/etc/cdk_gitlab_runners/authenticate_to_ecr.sh"
    NUM_REPOSITORIES=$(jq -r '.NonEcrRepositories | length' $PARAMETERS_FILE)

    if [ $NUM_REPOSITORIES -gt 0 ]; then
        for ((j=0; j<NUM_REPOSITORIES; j++)); do
            REPOSITORY=$(cat $PARAMETERS_FILE | jq -r --argjson index $j '.EcrRepositories[$index]')
            # Authenticate the first time
            sudo $AUTHENTICATION_SCRIPT $EC2_REGION $REPOSITORY
            # Authenticate on a cron job
            echo "0 */11 * * * $AUTHENTICATION_SCRIPT $EC2_REGION $REPOSITORY" > /tmp/mycron
            sudo crontab /tmp/mycron
            rm /tmp/mycron
        done
    fi

    # Authenticate to non-ECR repositores

    AUTHENTICATION_SCRIPT="/etc/cdk_gitlab_runners/authenticate_to_non_ecr.sh"
    NUM_REPOSITORIES=$(jq -r '.NonEcrRepositories | length' $PARAMETERS_FILE)

    if [ $NUM_REPOSITORIES -gt 0 ]; then
        for ((j=0; j<NUM_REPOSITORIES; j++)); do
            REPOSITORY=$(cat $PARAMETERS_FILE | jq -r --argjson index $j '.NonEcrRepositories[$index].repository')
            USERNAME=$(cat $PARAMETERS_FILE | jq -r --argjson index $j '.NonEcrRepositories[$index].username')
            PASSWORD_SECRET_NAME=$(cat $PARAMETERS_FILE | jq -r --argjson index $j '.NonEcrRepositories[$index].password_secret_name')
            # Get the PASSWORD from AWS SSM
            PASSWORD=$(aws ssm get-parameter --name $PASSWORD_SECRET_NAME --with-decryption --query Parameter.Value --output text)
            # Authenticate the first time
            sudo $AUTHENTICATION_SCRIPT $REPOSITORY $USERNAME $PASSWORD
            # Authenticate on a cron job
            echo "0 */11 * * * $AUTHENTICATION_SCRIPT $REPOSITORY $USERNAME $PASSWORD" > /tmp/mycron
            sudo crontab /tmp/mycron
            rm /tmp/mycron
        done
    fi

    # # Authenticate with DOCKER_AUTH_CONFIG. 
    # # This did not work for ECR or with the docker executor.
    # # To authenticate to ECR I tried multiple different things that I found over the internet.

    # FORMATTED_CREDENTIALS=$(jq -n --arg key0 "auths" --argjson val0 "{}" -n '[$key0, $val0] | { (.[0]): .[1]}')
    # NUM_REPOSITORIES=$(jq -r '.NonEcrRepositories | length' $PARAMETERS_FILE)
    # if [ $NUM_REPOSITORIES -gt 0 ]; then
    #     for ((j=0; j<NUM_REPOSITORIES; j++)); do
    #         REGISTRY=$(cat $PARAMETERS_FILE | jq -r --argjson index $j '.NonEcrRepositories[$index].registry')
    #         USERNAME=$(cat $PARAMETERS_FILE | jq -r --argjson index $j '.NonEcrRepositories[$index].username')
    #         PASSWORD_SECRET_NAME=$(cat $PARAMETERS_FILE | jq -r --argjson index $j '.NonEcrRepositories[$index].password_secret_name')
    #         # Get the PASSWORD from AWS SSM
    #         PASSWORD=$(aws ssm get-parameter --name $PASSWORD_SECRET_NAME --with-decryption --query Parameter.Value --output text)
    #         # Create the base64 encoded auth string
    #         CREDENTIALS_STRING="${USERNAME}:${PASSWORD}"
    #         CREDENTIALS_STRING=$(echo -n "${CREDENTIALS_STRING}" | openssl base64)
    #         # Insert the encoded string into the JSON structure
    #         FORMATTED_CREDENTIALS=$(echo "${FORMATTED_CREDENTIALS}" | jq --arg key0 "${REGISTRY}" --arg val0 "${CREDENTIALS_STRING}" '.auths[$key0].auth = $val0')
    #         FORMATTED_CREDENTIALS_DOCKER=$(echo "${FORMATTED_CREDENTIALS}" | jq --arg key0 "https://index.docker.io/v1/" --arg val0 "${CREDENTIALS_STRING}" '.auths[$key0].auth = $val0')
    #     done
    # fi
    # FORMATTED_CREDENTIALS=$(echo "${FORMATTED_CREDENTIALS}" | jq -c . | sed 's/"/\\\\\\"/g')
    # sed -i "s|<DockerAuthConfig>|${FORMATTED_CREDENTIALS}|" $CONFIG_FILE

    
    # Prepare the remaining configuration

    TOKEN_SECRET_NAME=$(cat $PARAMETERS_FILE | jq -r '.TokenSecretName')
    CACHE_BUCKET_NAME=$(cat $PARAMETERS_FILE | jq -r '.CacheBucketName')
    AVAILABILITY_ZONE=$(cat $PARAMETERS_FILE | jq -r '.AvailabilityZone')
    CHILD_RUNNERS_INSTANCES_VPC_ID=$(cat $PARAMETERS_FILE | jq -r '.ChildRunnersInstancesVpcId')
    CHILD_RUNNERS_INSTANCES_INSTANCE_PROFILE_NAME=$(cat $PARAMETERS_FILE | jq -r '.ChildRunnersInstancesInstanceProfileName')

    TOKEN=$(aws ssm get-parameter --name $TOKEN_SECRET_NAME --with-decryption --query Parameter.Value --output text)
    BASTION_INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    BASTION_INSTANCE_AUTO_SCALING_GROUP_NAME=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$BASTION_INSTANCE_ID" "Name=key,Values=aws:autoscaling:groupName" --query 'Tags[*].Value' --output text)

    sed -i "s|<EC2Region>|$EC2_REGION|" $CONFIG_FILE
    sed -i "s|<CacheBucketName>|$CACHE_BUCKET_NAME|" $CONFIG_FILE
    sed -i "s|<CacheBucketRegion>|$EC2_REGION|" $CONFIG_FILE
    sed -i "s|<ChildRunnersInstancesVpcId>|$CHILD_RUNNERS_INSTANCES_VPC_ID|" $CONFIG_FILE
    sed -i "s|<ChildRunnersInstancesInstanceProfileName>|$CHILD_RUNNERS_INSTANCES_INSTANCE_PROFILE_NAME|" $CONFIG_FILE
    sed -i "s|<BastionInstanceId>|$BASTION_INSTANCE_ID|" $CONFIG_FILE
    sed -i "s|<BastionInstanceAutoScalingGroupName>|$BASTION_INSTANCE_AUTO_SCALING_GROUP_NAME|" $CONFIG_FILE

    # Register the worker

    sudo gitlab-runner register \
        --non-interactive \
        --template-config="${CONFIG_FILE}" \
        --token="${TOKEN}"

done