
#include <cstdio>
#include <cstdlib>
int main(int argc, char *argv[]) {
    int n = atoi(argv[1]);
    int len = (2*(n-1)*(n/2));
    int* matrix = (int*) malloc(len * sizeof(int));
    int cntr = 1;
    printf("[");
    for (int i = 0; i < len-1; ++i){
        printf("0,");
    }
    printf("0]");

}