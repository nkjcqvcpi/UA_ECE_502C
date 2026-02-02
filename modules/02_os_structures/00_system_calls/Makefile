# Makefile

CC       := gcc
CFLAGS   := -Wall -Wextra -O2 -g
BUILDDIR := build
TARGET   := $(BUILDDIR)/hello
SRC      := hello.c

.PHONY: all clean

all: $(TARGET)

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

$(TARGET): $(SRC) | $(BUILDDIR)
	$(CC) $(CFLAGS) -o $@ $^

clean:
	rm -rf $(BUILDDIR)