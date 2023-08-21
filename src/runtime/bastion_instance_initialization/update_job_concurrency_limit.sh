#!/bin/bash -xe

# Once all workers are registered, set the job concurrency limit across workers.
PARAMETERS_FILE=/etc/cdk_gitlab_runners/max_concurrent_jobs.json
CONFIG_FILE=/etc/gitlab-runner/config.toml # Gitlab Runner updates this file after each worker registration.
MAX_CONCURRENT_JOBS=$(cat $PARAMETERS_FILE | jq -r '.MaxConcurrentJobs')
sudo sed -i "s|concurrent.*|concurrent = $MAX_CONCURRENT_JOBS|" $CONFIG_FILE

# Is this command needed?
# sudo gitlab-runner restart