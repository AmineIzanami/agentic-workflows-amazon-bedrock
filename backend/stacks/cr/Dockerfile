FROM public.ecr.aws/lambda/python:3.11

ARG version=1.0

# Copies requirements.txt file into the container
COPY requirements.txt .
RUN yum update -y
# RUN yum install -y gcc postgresql-devel
# Installs dependencies found in your requirements.txt file
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

ARG INCUBATOR_VER=unknown

WORKDIR ${LAMBDA_TASK_ROOT}
COPY . .

