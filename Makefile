# Variables
REPO_NAME := alexbrand
IMAGE_NAME := $(REPO_NAME)/tabular-data-mcp
VERSION := $(shell git rev-parse --short HEAD)
TAG := $(IMAGE_NAME):$(VERSION)
LATEST_TAG := $(IMAGE_NAME):latest

# Build the container image
build:
	docker buildx build --platform linux/amd64 -t $(TAG) -t $(LATEST_TAG) .

# Push the container image
push:
	docker push $(TAG)
	docker push $(LATEST_TAG)

# Build and push in one command
build-push: build push

# Show current variables
info:
	@echo "Repository: $(REPO_NAME)"
	@echo "Image name: $(IMAGE_NAME)"
	@echo "Version: $(VERSION)"
	@echo "Tag: $(TAG)"
	@echo "Latest tag: $(LATEST_TAG)"

.PHONY: build push build-push info
