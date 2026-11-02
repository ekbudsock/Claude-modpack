import sys
M=0xFFFFFFFF
GS=[0x09F4FBBD,0x9681884A,0x352027E9,0xF3DEE5A7]
PAR=[0x7AA9648F,0x7FAE6994,0xC0EFAAD5,0x42712C57]
def dec(o1,o2,s):
    t=0xC6EF3720
    for _ in range(32):
        o2=(o2-((((o1<<4)&M)+s[2])^((o1+t)&M)^((o1>>5)+s[3])))&M
        o1=(o1-((((o2<<4)&M)+s[0])^((o2+t)&M)^((o2>>5)+s[1])))&M
        t=(t-0x9E3779B9)&M
    return o1,o2
def enc(o1,o2,s):
    t=0
    for _ in range(32):
        t=(t+0x9E3779B9)&M
        o1=(o1+((((o2<<4)&M)+s[0])^((o2+t)&M)^((o2>>5)+s[1])))&M
        o2=(o2+((((o1<<4)&M)+s[2])^((o1+t)&M)^((o1>>5)+s[3])))&M
    return o1,o2
if __name__=="__main__":
    for code in sys.argv[1:]:
        for line in code.split('+'):
            a,b=(int(x,16) for x in line.split())
            g=dec(a,b,GS); p=dec(a,b,PAR)
            print(f"{line}  GSv1-> {g[0]:08X} {g[1]:08X}   PARv3-> {p[0]:08X} {p[1]:08X}")
        print()
