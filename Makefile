# Makefile para iv_smile_project

# Variables (si no las exportas, edítalas aquí)
AWS_REGION ?= us-east-1
# REPO_URL se obtiene del output de Terraform
REPO_URL := $(shell cd infra && terraform output -raw ecr_repo_url)

.PHONY: infra-init infra-plan infra-apply docker-build docker-push deploy-all

# Inicializa Terraform en infra/
infra-init:
	cd infra && terraform init

# Muestra el plan de Terraform
infra-plan:
	cd infra && terraform plan

# Aplica los cambios de Terraform
infra-apply:
	cd infra && terraform apply -auto-approve

# Construye la imagen Docker usando la URL del repositorio ECR
docker-build:
	docker build -t $(REPO_URL):latest .

# Autentica y sube la imagen al repositorio ECR
docker-push:
	aws ecr get-login-password --region $(AWS_REGION) \
	  | docker login --username AWS --password-stdin $(REPO_URL)
	docker push $(REPO_URL):latest

# Ejecuta infra-apply, build y push en un solo comando
deploy-all: infra-apply docker-build docker-push 