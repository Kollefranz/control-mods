import re,sys
data=open(sys.argv[1],'rb').read()
minlen=int(sys.argv[2]) if len(sys.argv)>2 else 5
for m in re.finditer(rb'[\x20-\x7e]{%d,}'%minlen,data): print('A',m.group().decode())
for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}'%minlen,data): print('W',m.group().decode('utf-16le'))
