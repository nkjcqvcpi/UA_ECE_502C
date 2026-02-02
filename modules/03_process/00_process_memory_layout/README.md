# Test the memory layout of a process

## Preparation

In this folder, compile `test.c` to get executable file `test` in folder `build`.

```bash
make
```

## Test

To see sections of the executable file:

```bash
readelf -S test
```

To use GDB
```bash
gdb ./test
```

And inside GDB:
```bash
break main
info proc mappings
```

See other commands in GDB: [Link](https://visualgdb.com/gdbreference/commands/).