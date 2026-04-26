# SubHub — run from repository root. Requires https://docs.astral.sh/uv/
UV ?= uv

.PHONY: help sync run test

help: ## Show available targets
	@printf "SubHub targets (uv runs the virtualenv; no manual activation needed):\n\n"
	@printf "  make sync     Install / refresh dependencies (uv sync)\n"
	@printf "  make run      Start the SubHub Matrix bot (uv run subhub)\n"
	@printf "  make test     Run the test suite (uv run pytest)\n"
	@printf "\nPass extra flags via ARGS, e.g.  make run ARGS=\"--env .env.prod\"\n"

sync: ## Install or refresh dependencies
	$(UV) sync

run: ## Start the SubHub Matrix bot
	$(UV) run subhub $(ARGS)

test: ## Run tests
	$(UV) run pytest $(ARGS)
