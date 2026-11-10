#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/file.h>
#include <time.h>
#include <unistd.h>
#include "bmi08x.h"
#include "bmi088_linux.h"
#include <stdarg.h>

struct endpoint { int fd; uint16_t address; char *error; };
struct bmi088_handle {
    int fd;
    struct endpoint accel, gyro;
    struct bmi08_dev dev;
    char error[256];
};
static void set_error(char *buffer, const char *format, ...)
{
    va_list args;
    va_start(args, format);
    vsnprintf(buffer, 256, format, args);
    va_end(args);
}
static void delay_us(uint32_t us, void *context)
{
    (void)context;
    struct timespec t = { us / 1000000, (long)(us % 1000000) * 1000 };
    while (nanosleep(&t, &t) && errno == EINTR) {}
}
static int8_t transfer(struct endpoint *ep, struct i2c_msg *msgs,
                       unsigned count, const char *op, uint8_t reg)
{
    struct i2c_rdwr_ioctl_data transaction = { msgs, count };
    int rc = ioctl(ep->fd, I2C_RDWR, &transaction);
    if (rc == (int)count) return BMI08_INTF_RET_SUCCESS;
    set_error(ep->error, "I2C %s addr=0x%02x reg=0x%02x: %s\n", op,
            ep->address, reg, rc < 0 ? strerror(errno) : "incomplete transfer");
    return -1;
}
static int8_t read_regs(uint8_t reg, uint8_t *data, uint32_t len, void *context)
{
    struct endpoint *ep = context;
    if (!len || len > 32) return -1;
    struct i2c_msg msgs[2] = {
        { .addr=ep->address, .flags=0, .len=1, .buf=&reg },
        { .addr=ep->address, .flags=I2C_M_RD, .len=(uint16_t)len, .buf=data }
    };
    return transfer(ep, msgs, 2, "READ", reg);
}
static int8_t write_regs(uint8_t reg, const uint8_t *data, uint32_t len, void *context)
{
    struct endpoint *ep = context;
    uint8_t buffer[33];
    if (!len || len > 32) return -1;
    buffer[0] = reg;
    memcpy(buffer + 1, data, len);
    struct i2c_msg msg = {
        .addr=ep->address, .flags=0, .len=(uint16_t)(len+1), .buf=buffer
    };
    /* On this board, resets may take effect but finish with a NACK.
     * Accept this only after checking chip IDs and reset register values. */
    if (((ep->address == 0x18 && reg == 0x7e) ||
         (ep->address == 0x68 && reg == 0x14)) && len == 1 && data[0] == 0xb6) {
        struct i2c_rdwr_ioctl_data transaction = { &msg, 1 };
        int rc = ioctl(ep->fd, I2C_RDWR, &transaction);
        int error = errno;
        if (rc == 1) return BMI08_INTF_RET_SUCCESS;
        if (rc < 0 && (error == ENXIO || error == EREMOTEIO)) {
            uint8_t id, power[2], config[2], gyro_config[3];
            delay_us(50000, NULL);
            if (ep->address == 0x18 && read_regs(0x00, &id, 1, ep) == 0 && id == 0x1e &&
                read_regs(0x7c, power, 2, ep) == 0 &&
                power[0] == 0x03 && power[1] == 0x00 &&
                read_regs(0x40, config, 2, ep) == 0 &&
                config[0] == 0xa8 && config[1] == 0x01) {
                fprintf(stderr, "Reset ACC: NACK received; reset confirmed by register readback.\n");
                return BMI08_INTF_RET_SUCCESS;
            }
            if (ep->address == 0x68 && read_regs(0x00, &id, 1, ep) == 0 && id == 0x0f &&
                read_regs(0x0f, gyro_config, 3, ep) == 0 &&
                gyro_config[0] == 0 && gyro_config[1] == 0x80 && gyro_config[2] == 0) {
                fprintf(stderr, "Reset GYRO: NACK received; reset confirmed by register readback.\n");
                return BMI08_INTF_RET_SUCCESS;
            }
        }
        set_error(ep->error, "Reset not confirmed: %s\n", rc < 0 ? strerror(error) : "incomplete transfer");
        return -1;
    }
    return transfer(ep, &msg, 1, "WRITE", reg);
}

#define CHECK(call) do { int8_t result = (call); if (result != BMI08_OK) { \
    if (!h->error[0]) set_error(h->error, "%s: Bosch error %d", #call, result); \
    return -1; \
} } while (0)
static int initialize(struct bmi088_handle *h, int probe_only)
{
    CHECK(bmi08xa_init(&h->dev));
    CHECK(bmi08g_init(&h->dev));
    if (probe_only) return 0;
    /* Reset to a known state before reloading the configuration. */
    CHECK(bmi08a_soft_reset(&h->dev));
    delay_us(50000, NULL);
    CHECK(bmi08g_soft_reset(&h->dev));
    delay_us(50000, NULL);
    CHECK(bmi08xa_init(&h->dev));
    CHECK(bmi08g_init(&h->dev));
    /* Follow the Bosch polling_streaming_pc sequence for the BMI088 variant. */
    CHECK(bmi08a_load_config_file(&h->dev));
    h->dev.accel_cfg.odr = BMI08_ACCEL_ODR_100_HZ;
    h->dev.accel_cfg.range = BMI088_ACCEL_RANGE_3G;
    h->dev.accel_cfg.power = BMI08_ACCEL_PM_ACTIVE;
    h->dev.accel_cfg.bw = BMI08_ACCEL_BW_NORMAL;
    CHECK(bmi08a_set_power_mode(&h->dev));
    CHECK(bmi08xa_set_meas_conf(&h->dev));
    h->dev.gyro_cfg.odr = BMI08_GYRO_BW_32_ODR_100_HZ;
    h->dev.gyro_cfg.bw = BMI08_GYRO_BW_32_ODR_100_HZ;
    h->dev.gyro_cfg.range = BMI08_GYRO_RANGE_500_DPS;
    h->dev.gyro_cfg.power = BMI08_GYRO_PM_NORMAL;
    CHECK(bmi08g_set_power_mode(&h->dev));
    CHECK(bmi08g_set_meas_conf(&h->dev));
    delay_us(100000, NULL);
    return 0;
}
struct bmi088_handle *bmi088_open(const char *path, int probe_only, char *error)
{
    struct bmi088_handle *h = calloc(1, sizeof(*h));
    if (!h) { set_error(error, "Out of memory"); return NULL; }
    h->fd = open(path, O_RDWR | O_CLOEXEC);
    if (h->fd < 0) {
        set_error(h->error, "%s: %s%s", path, strerror(errno),
                  errno == EACCES ? "; join the i2c group (see README.md)" : "");
        goto failure;
    }
    if (flock(h->fd, LOCK_EX | LOCK_NB) < 0) {
        set_error(h->error, "Cannot lock %s: %s; another reader may be running", path, strerror(errno));
        goto failure;
    }
    unsigned long capabilities;
    if (ioctl(h->fd, I2C_FUNCS, &capabilities) < 0 || !(capabilities & I2C_FUNC_I2C)) {
        set_error(h->error, "Bus does not support I2C_RDWR"); goto failure;
    }
    h->accel = (struct endpoint){h->fd, 0x18, h->error};
    h->gyro = (struct endpoint){h->fd, 0x68, h->error};
    h->dev.intf = BMI08_I2C_INTF;
    h->dev.variant = BMI088_VARIANT;
    h->dev.intf_ptr_accel = &h->accel;
    h->dev.intf_ptr_gyro = &h->gyro;
    h->dev.read = read_regs;
    h->dev.write = write_regs;
    h->dev.delay_us = delay_us;
    h->dev.read_write_len = 32;
    if (initialize(h, probe_only)) goto failure;
    return h;
failure:
    set_error(error, "%s", h->error);
    if (h->fd >= 0) close(h->fd);
    free(h);
    return NULL;
}
int bmi088_read(struct bmi088_handle *h, double *values)
{
    struct bmi08_sensor_data a, g;
    h->error[0] = 0;
    CHECK(bmi08a_get_data(&a, &h->dev));
    CHECK(bmi08g_get_data(&g, &h->dev));
    values[0] = a.x * 3.0 / 32768;
    values[1] = a.y * 3.0 / 32768;
    values[2] = a.z * 3.0 / 32768;
    values[3] = g.x * 500.0 / 32768;
    values[4] = g.y * 500.0 / 32768;
    values[5] = g.z * 500.0 / 32768;
    return 0;
}
const char *bmi088_error(struct bmi088_handle *h) { return h->error; }
void bmi088_close(struct bmi088_handle *h)
{
    if (h) { close(h->fd); free(h); }
}
