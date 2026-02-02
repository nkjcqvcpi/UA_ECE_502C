# Test  how system calls work

## Preparation

In this folder, compile `hello.c` to get executable file `hello` in folder `build`.

```bash
make
```

## Test

Use `strace` to see the `write` system call when executing the program.

```bash
strace -e trace=write ./hello # Only see write, or
strace ./hello # See full system call trace
```

You should see something like

```c
write(1, "hello\n", 6) = 6
```

The actuall function call chain should be:

```c
your main()
  └── printf(...)
       └── (libc formatting + buffering)
            └── write(fd=1, buf="hello\n", n=6)     [user-space libc]
                 └── syscall(SYS_write, ...)        [CPU instruction to enter kernel]
                      └── sys_write(...)            [kernel implementation]
```

Now confirm the executable `hello` linked and used `libc`.

```bash
ldd ./hello
```

You will a line like:

```
libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x...)
```

Now confirm `libc` invoked system call `write`. View the binary file and search for `write`.

```bash
objdump -T "/lib/x86_64-linux-gnu/libc.so.6" | grep -E '\bwrite\b'
```

Then you should find an exported symbol for `write`, proving `libc` has the API `write`. Then look into the API `write`.

```bash
objdump -d "/lib/x86_64-linux-gnu/libc.so.6" | grep -A 10 "__write@@"
```

Then you can find the assembly code for this API, which clearly used `syscall` instruction with call ID `1`, which is system call `write`. Check the table [here](https://www.chromium.org/chromium-os/developer-library/reference/linux-constants/syscalls/).

```
000000000011c590 <__write@@GLIBC_2.2.5>:
  11c590:	f3 0f 1e fa          	endbr64
  11c594:	80 3d a5 ea 0e 00 00 	cmpb   $0x0,0xeeaa5(%rip)        # 20b040 <__libc_single_threaded@@GLIBC_2.32>
  11c59b:	74 13                	je     11c5b0 <__write@@GLIBC_2.2.5+0x20>
  11c59d:	b8 01 00 00 00       	mov    $0x1,%eax
  11c5a2:	0f 05                	syscall
  ...
```