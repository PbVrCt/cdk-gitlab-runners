#!/bin/bash -xe
sudo apt-get update -y
sudo apt-get upgrade -y

# 0. Install utils

sudo apt-get install -y unzip
sudo apt-get install -y jq
sudo apt-get install -y openssl
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip -o awscliv2.zip
sudo ./aws/install


# 0. Install aws-ecr-credential-helper and make it available to Gitlab Runner.

"""NOTE:
The aws-ecr-credential-helper installation remains commented out as the worker could not use the helper for authentication to ecr.
If you want to use it inside the jobs, uncomment the following 3 lines and mount it in the job containers as a volume.
"""

# sudo apt-get install amazon-ecr-credential-helper -y
# sudo cp bin/docker-credential-ecr-login /usr/local/bin/
# sudo chmod +x /usr/local/bin/docker-credential-ecr-login


# The steps below are from: https://docs.gitlab.com/runner/configuration/runner_autoscale_aws/#prepare-the-runner-manager-instance (as of 2023-04)

# 1. Install Gitlab Runner (https://docs.gitlab.com/runner/install/linux-repository.html as of 2023-04)

curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh" | sudo bash
apt-cache madison gitlab-runner
sudo apt-get install gitlab-runner=16.0.2 -y

# 2. Install Docker Engine (https://9bo.hateblo.jp/entry/2019/03/31/202606)

sudo apt-get remove docker docker-engine docker.io && \
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common && \
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - && \
sudo apt-key fingerprint 0EBFCD88 && \
sudo add-apt-repository \
   "deb [arch=arm64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable" && \
sudo apt-get update && sudo apt-get install docker-ce -y

# 3. Install Docker Machine (CKI fork) (https://gitlab.com/gitlab-org/ci-cd/docker-machine/-/blob/main/docs/install-machine.md as of 2023-04)

"""NOTE:
The Gitlab fork of Docker Machine has an issue where spawned spot instances are untagged.
https://gitlab.com/gitlab-org/ci-cd/docker-machine/-/issues/112
A solution is available in the comments: Install the CKI fork instead.
(The tags are used for the deletion of child instances when terminating the bastion instance)

UPDATE 2023-08:
The issue has been solved, but I haven't had the time to update the installed version and check that it works.
"""

curl -L -o docker-machine-Linux-aarch64 https://arr-cki-prod-docker-machine.s3.amazonaws.com/v0.16.2-gitlab.19-cki.3/docker-machine-Linux-aarch64
sudo cp docker-machine-Linux-aarch64 /usr/local/bin/docker-machine
sudo chmod +x /usr/local/bin/docker-machine
export PATH=$PATH:/usr/local/bin
source ~/.bashrc
sudo ln -sf /usr/local/bin/docker-machine /usr/bin/docker-machine # https://gitlab.com/gitlab-org/gitlab-runner/-/issues/2328#note_163927197