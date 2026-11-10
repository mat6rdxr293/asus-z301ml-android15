import socket,sys,hashlib
ip,port,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind((ip,port)); s.listen(1)
c,a=s.accept(); h=hashlib.sha256(); n=0
with open(out,'wb') as f:
    while True:
        b=c.recv(1<<20)
        if not b: break
        f.write(b); h.update(b); n+=len(b)
print('RECV',n,h.hexdigest(),flush=True)
