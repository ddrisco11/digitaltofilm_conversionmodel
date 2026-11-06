#include <math.h>
#include <stdlib.h>
#include <string.h>

/* The same no-flux stencil and float32 reaction equations as wet_print.py. */
static void laplace(const float *a,float *out,int h,int w) {
    for(int y=0;y<h;y++) for(int x=0;x<w;x++) {
        int i=y*w+x;
        float vertical=a[(y?y-1:y)*w+x]-2*a[i]+a[(y<h-1?y+1:y)*w+x];
        float horizontal=a[y*w+(x?x-1:x)]-2*a[i]+a[y*w+(x<w-1?x+1:x)];
        out[i]=vertical+horizontal;
    }
}
int develop(const float *active,float *result,int h,int w,int steps,float bath) {
    size_t n=(size_t)h*w;
    float *memory=calloc(n*7,sizeof(float));
    if(!memory)return 1;
    float *dev=memory,*silver=dev+n,*oxidized=silver+n,*coupler=oxidized+n;
    float *dye=coupler+n,*lap=dye+n,*extra=lap+n;
    for(size_t i=0;i<n;i++){dev[i]=1;coupler[i]=1;}
    for(int step=0;step<steps;step++) {
        laplace(dev,lap,h,w);
        for(size_t i=0;i<n;i++) {
            dev[i]+=.4f*(.15f*lap[i]+bath*(1-dev[i]));
            float reacted=(active[i]-silver[i])*(-expm1f(-.13f*.4f*dev[i]));
            if(reacted>dev[i])reacted=dev[i];
            dev[i]-=reacted;silver[i]+=reacted;oxidized[i]+=reacted;
        }
        laplace(oxidized,extra,h,w);
        for(size_t i=0;i<n;i++) {
            oxidized[i]+=.4f*.18f*extra[i];
            float coupled=oxidized[i]*(-expm1f(-.7f*.4f*coupler[i]));
            if(coupled>coupler[i])coupled=coupler[i];
            oxidized[i]-=coupled;
            oxidized[i]*=expf(-.03f*.4f);
            dye[i]+=coupled;coupler[i]-=coupled;
        }
    }
    memcpy(result,dye,n*sizeof(float));free(memory);return 0;
}
