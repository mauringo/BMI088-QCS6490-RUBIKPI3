CC ?= cc
PYTHON ?= python3
CFLAGS ?= -O2 -Wall -Wextra -Wpedantic
API = vendor/BMI08x_SensorAPI
SOURCES = src/bmi088_linux.c $(API)/bmi08a.c $(API)/bmi08g.c $(API)/bmi08xa.c
HEADERS = src/bmi088_linux.h $(API)/bmi08.h $(API)/bmi08x.h $(API)/bmi08_defs.h

.PHONY: all clean test hardware-test
all: bmi088 libbmi088.so
bmi088: src/main.c $(SOURCES) $(HEADERS)
	$(CC) $(CPPFLAGS) $(CFLAGS) -I$(API) src/main.c $(SOURCES) $(LDFLAGS) -o $@
libbmi088.so: $(SOURCES) $(HEADERS)
	$(CC) $(CPPFLAGS) $(CFLAGS) -fPIC -shared -I$(API) $(SOURCES) $(LDFLAGS) -o $@
clean:
	rm -f bmi088 libbmi088.so

test: all
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	$(PYTHON) bmi088_read.py --help > /dev/null
	./bmi088 --help > /dev/null 2>&1

hardware-test: all
	$(PYTHON) tests/hardware_smoke.py
