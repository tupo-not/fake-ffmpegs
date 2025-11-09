#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <stdlib.h>

#pragma comment(lib,"Ws2_32.lib")

int main(int argc,char**argv){
    WSADATA wsa;
    if(WSAStartup(MAKEWORD(2,2),&wsa)!=0) return 1;

    SOCKET s = socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if(s==INVALID_SOCKET){ WSACleanup(); return 2; }

    struct sockaddr_in srv;
    srv.sin_family = AF_INET;
    srv.sin_port = htons(33445);
    srv.sin_addr.s_addr = inet_addr("127.0.0.1");

    if(connect(s,(struct sockaddr*)&srv,sizeof(srv))==SOCKET_ERROR){
        closesocket(s); WSACleanup(); return 3;
    }

    // join argv by space
    size_t buf_sz = 1024, used = 0;
    char *buf = (char*)malloc(buf_sz);
    if(!buf){ closesocket(s); WSACleanup(); return 4; }
    buf[0]='\0';
    for(int i=1;i<argc;i++){
        if(i>1){ strcat(buf," "); used++; }
        size_t need = strlen(argv[i]);
        while(used+need+1>=buf_sz){ buf_sz*=2; buf = (char*)realloc(buf,buf_sz); }
        strcat(buf,argv[i]); used+=need;
    }

    send(s,buf,(int)strlen(buf),0);
    free(buf);
    shutdown(s,SD_SEND);

    // ---- Ждём подтверждение DONE ----
    char resp[21]={0};
    int recv_bytes = recv(s,resp,sizeof(resp)-1,0);
    if(recv_bytes>0 && strstr(resp,"now u can crash UwU")) {
        printf("[stub] received DONE, exiting\n");
    } else {
        printf("[stub] no DONE received, exiting anyway\n");
    }

    closesocket(s);
    WSACleanup();
    return 0;
}
