#ifndef BMI088_LINUX_H
#define BMI088_LINUX_H
/* Error buffers passed to bmi088_open must contain at least 256 bytes.
 * Handles are not thread-safe. Close each successfully opened handle once.
 * Values: ax, ay, az in g; gx, gy, gz in degrees per second. */
struct bmi088_handle;
struct bmi088_handle *bmi088_open(const char *path, int probe_only, char *error);
int bmi088_read(struct bmi088_handle *handle, double *values);
const char *bmi088_error(struct bmi088_handle *handle);
void bmi088_close(struct bmi088_handle *handle);
#endif
