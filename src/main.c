#define _POSIX_C_SOURCE 200809L
#include "bmi088_linux.h"
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
static volatile sig_atomic_t running = 1;
static void stop(int sig) { (void)sig; running = 0; }
int main(int argc, char **argv)
{
    const char *path = "/dev/i2c-1";
    long samples = 0;
    int probe = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--probe")) probe = 1;
        else if (!strcmp(argv[i], "--device") && i+1 < argc) path = argv[++i];
        else if (!strcmp(argv[i], "--samples") && i+1 < argc) {
            char *end;
            errno = 0;
            samples = strtol(argv[++i], &end, 10);
            if (errno || *end || samples <= 0) { fputs("Invalid sample count\n", stderr); return 2; }
        } else {
            fprintf(stderr, "Usage: %s [--device /dev/i2c-1] [--probe] [--samples N]\n", argv[0]);
            return strcmp(argv[i], "--help") ? 2 : 0;
        }
    }
    char error[256];
    struct bmi088_handle *h = bmi088_open(path, probe, error);
    if (!h) { fprintf(stderr, "%s\n", error); return 1; }
    puts("CHIP_ID: ACC=0x1e GYRO=0x0f");
    if (probe) { bmi088_close(h); return 0; }
    signal(SIGINT, stop);
    signal(SIGTERM, stop);
    puts("ACC [g], GYRO [deg/s]. Unsynchronized reads at about 10 Hz. Ctrl+C to stop.");
    int result = 0;
    for (long n=0; running && (!samples || n<samples); n++) {
        double v[6];
        if (bmi088_read(h, v)) { fprintf(stderr, "%s\n", bmi088_error(h)); result=1; break; }
        printf("ACC %+7.3f %+7.3f %+7.3f | GYRO %+8.2f %+8.2f %+8.2f\n", v[0], v[1], v[2], v[3], v[4], v[5]);
        fflush(stdout);
        struct timespec delay = {0, 100000000};
        nanosleep(&delay, NULL);
    }
    bmi088_close(h);
    return result;
}
