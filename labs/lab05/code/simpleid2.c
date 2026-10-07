/* Архипов Александр Сергеевич | НБИбд-01-24 */
#include <stdio.h>
#include <unistd.h>
int main(void) {
    printf("e_uid=%lu, e_gid=%lu\n", (unsigned long)geteuid(), (unsigned long)getegid());
    printf("real_uid=%lu, real_gid=%lu\n", (unsigned long)getuid(), (unsigned long)getgid());
    return 0;
}
