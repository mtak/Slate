PIO := .venv/bin/pio
export PLATFORMIO_CORE_DIR := $(CURDIR)/.platformio

.PHONY: setup test test-basic test-memory build build-memory-test upload monitor clean

setup:
	./scripts/setup.sh

test: test-basic test-memory

test-basic:
	@mkdir -p .test-build
	$(CXX) -std=c++11 -Wall -Wextra -Werror -pedantic -Isrc src/frame.cpp tests/frame_test.cpp -o .test-build/frame_test
	./.test-build/frame_test

test-memory:
	@mkdir -p .test-build
	$(CXX) -std=c++11 -Wall -Wextra -Werror -pedantic -g -O1 -fno-omit-frame-pointer -fsanitize=address,undefined -Isrc src/frame.cpp src/frame_ingestion.cpp tests/frame_memory_test.cpp -o .test-build/frame_memory_test
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ./.test-build/frame_memory_test

build:
	$(PIO) run

build-memory-test:
	$(PIO) test -e slate_esp32_memory_test --without-uploading --without-testing

upload:
	@test -n "$(PORT)" || (echo "Set PORT to the ESP32 serial port, e.g. make upload PORT=/dev/ttyUSB0" >&2; exit 2)
	$(PIO) run --target upload --upload-port "$(PORT)"

monitor:
	@test -n "$(PORT)" || (echo "Set PORT to the ESP32 serial port, e.g. make monitor PORT=/dev/ttyUSB0" >&2; exit 2)
	$(PIO) device monitor --port "$(PORT)" --baud 115200

clean:
	$(PIO) run --target clean
