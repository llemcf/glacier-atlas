PREFECT_LOCAL_WORKPOOL    := $(shell echo $$PREFECT_LOCAL_WORKPOOL)
PREFECT_PROFILE_TESTING   := $(shell echo $$PREFECT_PROFILE_TESTING)

check-env:
	@echo "Checking if required environment variables are set..."
	@if [ -z "$(AWS_PROFILE_TESTING)" ]; then \
	    echo "Error: AWS_PROFILE_TESTING is not set"; \
	    exit 1; \
	fi
	@if [ -z "$(PREFECT_PROFILE_TESTING)" ]; then \
	    echo "Error: PREFECT_PROFILE_TESTING is not set"; \
	    exit 1; \
	fi
	@if [ -z "$(PREFECT_LOCAL_WORKPOOL)" ]; then \
	    echo "Error: PREFECT_LOCAL_WORKPOOL is not set"; \
	    exit 1; \
	fi
	@if [ -z "$(DOCKER_REGISTRY)" ]; then \
	    echo "Error: DOCKER_REGISTRY is not set"; \
	    exit 1; \
	fi
	@if [ -z "$(POETRY_HTTP_BASIC_DEEPKI_USERNAME)" ]; then \
	    echo "Error: POETRY_HTTP_BASIC_DEEPKI_USERNAME is not set"; \
	    exit 1; \
	fi
	@if [ -z "$(POETRY_HTTP_BASIC_DEEPKI_PASSWORD)" ]; then \
	    echo "Error: POETRY_HTTP_BASIC_DEEPKI_PASSWORD is not set"; \
	    exit 1; \
	fi
	@echo "All required environment variables are set."

# Start LOCAL work-pool
worpkpool-local: .env check-env
	prefect worker start --pool $(PREFECT_LOCAL_WORKPOOL)

# Prefect Deploy
dp: .env check-env
	@. .env
	@echo "\n-----------------------> Where to deploy ?"; \
	read -p "Enter (local/testing): " server; \
	if [ "$$server" == "testing" ]; then \
		echo prefect profile use $(PREFECT_PROFILE_TESTING); \
		prefect profile use $(PREFECT_PROFILE_TESTING); \
	fi; \
	if [ "$$server" == "local" ]; then \
		echo prefect profile use default; \
		prefect profile use default; \
	fi; \
	echo "\n-----------------------> Build ?"; \
	read -p "Enter (y/n): " build; \
	echo "\n-----------------------> Push ?"; \
	read -p "Enter (y/n): " push; \
	if [ "$$push" != "n" ]; then \
		echo "Have you refreshed your SSO token? (y/n)"; \
		read refresh_token; \
		if [ "$$refresh_token" != "y" ]; then \
			echo "Refresh your sso token"; \
			echo "Exiting deployment."; \
			exit 1; \
		fi; \
	fi; \
	echo "\n-----------------------> Launch deployment"; \
	echo python prefect_utils/prefect_deploy_main.py --server $$server --build $$build --push $$push; \
	python prefect_utils/prefect_deploy_main.py --server $$server --build $$build --push $$push ; \