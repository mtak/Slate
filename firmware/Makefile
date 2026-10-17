PIO := .venv/bin/pio
export PLATFORMIO_CORE_DIR := $(CURDIR)/.platformio

.PHONY: setup test build upload monitor clean

setup:
	./scripts/setup.sh

test:
	@mkdir -p .test-build
	$(CXX) -std=c++11 -Wall -Wextra -Werror -pedantic -Isrc src/frame.cpp tests/frame_test.cpp -o .test-build/frame_test
	./.test-build/frame_test

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
