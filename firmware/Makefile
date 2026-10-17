PIO := .venv/bin/pio
export PLATFORMIO_CORE_DIR := $(CURDIR)/.platformio

.PHONY: setup build upload monitor clean

setup:
	./scripts/setup.sh

build:
	$(PIO) run

upload:
	@test -n "$(PORT)" || (echo "Set PORT to the ESP32 serial port, e.g. make upload PORT=/dev/ttyUSB0" >&2; exit 2)
	$(PIO) run --target upload --upload-port "$(PORT)"

monitor:
	@test -n "$(PORT)" || (echo "Set PORT to the ESP32 serial port, e.g. make monitor PORT=/dev/ttyUSB0" >&2; exit 2)
	$(PIO) device monitor --port "$(PORT)" --baud 115200

clean:
	$(PIO) run --target clean
