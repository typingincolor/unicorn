# Stellar Unicorn Build/Deploy Makefile
# Requires: mpremote (pip install mpremote)

# Files to deploy to Pico
PICO_FILES = config.py core.py main.py

.PHONY: deploy install-deps check-deps clean reset run repl

# Deploy all files to Pico
deploy: check-deps
	@echo "Deploying to Stellar Unicorn..."
	@for file in $(PICO_FILES); do \
		echo "  Copying $$file..."; \
		mpremote cp $$file :$$file; \
	done
	@echo "Done! Restart Pico to apply changes."

# Install umqtt.simple on Pico
install-deps:
	@echo "Installing umqtt.simple on Pico..."
	mpremote mip install umqtt.simple
	@echo "Done!"

# Check if mpremote is installed
check-deps:
	@which mpremote > /dev/null || (echo "Error: mpremote not found. Install with: pip install mpremote" && exit 1)

# Remove deployed files from Pico
clean:
	@echo "Removing files from Pico..."
	-mpremote rm :config.py
	-mpremote rm :core.py
	-mpremote rm :main.py
	@echo "Done!"

# Soft reset Pico
reset:
	@echo "Resetting Pico..."
	mpremote reset

# Deploy and reset
run: deploy reset

# Open REPL
repl:
	mpremote repl

# Run simulator locally
sim:
	python3 simulator.py

# Install local dev dependencies
dev-deps:
	pip install -r requirements.txt mpremote

# Show help
help:
	@echo "Stellar Unicorn Makefile"
	@echo ""
	@echo "Pico Commands:"
	@echo "  make deploy      - Copy files to Pico"
	@echo "  make install-deps - Install umqtt.simple on Pico"
	@echo "  make run         - Deploy and reset Pico"
	@echo "  make reset       - Soft reset Pico"
	@echo "  make repl        - Open MicroPython REPL"
	@echo "  make clean       - Remove files from Pico"
	@echo ""
	@echo "Local Commands:"
	@echo "  make sim         - Run simulator"
	@echo "  make dev-deps    - Install dev dependencies"
