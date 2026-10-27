/* pstack: print pc/lr + frame-pointer chain of every thread of a process (aarch64).
 * usage: pstack <pid>      (needs root; the process is stopped only briefly) */
#define _GNU_SOURCE
#include <dirent.h>
#include <elf.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/uio.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

static int rd(pid_t tid, uint64_t addr, uint64_t *out)
{
    struct iovec l = { out, 8 }, r = { (void *)addr, 8 };
    return process_vm_readv(tid, &l, 1, &r, 1, 0) == 8 ? 0 : -1;
}

static void dump(pid_t pid, pid_t tid)
{
    char path[64], name[64] = "?";
    snprintf(path, sizeof path, "/proc/%d/task/%d/comm", pid, tid);
    FILE *f = fopen(path, "r");
    if (f) { if (fgets(name, sizeof name, f)) name[strcspn(name, "\n")] = 0; fclose(f); }
    if (ptrace(PTRACE_SEIZE, tid, 0, 0) || ptrace(PTRACE_INTERRUPT, tid, 0, 0)) {
        printf("tid %d (%s): attach failed: %s\n", tid, name, strerror(errno));
        return;
    }
    waitpid(tid, NULL, __WALL);
    struct user_regs_struct regs;
    struct iovec io = { &regs, sizeof regs };
    if (ptrace(PTRACE_GETREGSET, tid, (void *)NT_PRSTATUS, &io) == 0) {
        printf("tid %d (%s)\n  pc 0x%llx\n  lr 0x%llx\n", tid, name,
               (unsigned long long)regs.pc, (unsigned long long)regs.regs[30]);
        uint64_t fp = regs.regs[29];
        for (int i = 0; i < 32 && fp; ++i) {
            uint64_t next, ret;
            if (rd(pid, fp, &next) || rd(pid, fp + 8, &ret)) break;
            printf("  fp 0x%llx\n", (unsigned long long)ret);
            if (next <= fp) break;
            fp = next;
        }
    }
    ptrace(PTRACE_DETACH, tid, 0, 0);
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: pstack <pid>\n"); return 1; }
    pid_t pid = atoi(argv[1]);
    char path[64];
    snprintf(path, sizeof path, "/proc/%d/task", pid);
    DIR *d = opendir(path);
    if (!d) { perror(path); return 1; }
    struct dirent *e;
    while ((e = readdir(d)))
        if (e->d_name[0] != '.') dump(pid, atoi(e->d_name));
    closedir(d);
    return 0;
}
