/* Архипов Александр Сергеевич | НБИбд-01-24 */
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "Usage: %s FILE\n", argv[0]); return 2; }
    int fd = open(argv[1], O_RDONLY);
    if (fd < 0) { perror("open"); return 1; }
    char buffer[4096];
    ssize_t n;
    while ((n = read(fd, buffer, sizeof buffer)) > 0) {
        if (fwrite(buffer, 1, (size_t)n, stdout) != (size_t)n) {
            perror("write"); close(fd); return 1;
        }
    }
    if (n < 0) { perror("read"); close(fd); return 1; }
    close(fd);
    return 0;
}
