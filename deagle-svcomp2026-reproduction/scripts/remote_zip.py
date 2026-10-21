import io,urllib.request,json,pathlib,time,zipfile,sys,threading
class HTTPRange(io.RawIOBase):
 def __init__(self,url,size):self.url=url;self.size=size;self.pos=0;self.ranges=[]
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,off,whence=0):
  self.pos=off if whence==0 else self.pos+off if whence==1 else self.size+off
  if self.pos<0:raise ValueError('negative position')
  return self.pos
 def read(self,n=-1):
  if n<0:n=self.size-self.pos
  n=min(n,self.size-self.pos)
  if not n:return b''
  start=self.pos;end=start+n-1
  for lo,hi,b in self.ranges:
   if lo<=start and hi>=end:self.pos+=n;return b[start-lo:end-lo+1]
  end=min(self.size-1,max(end,start+65535))
  for attempt in range(4):
   try:
    req=urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}','User-Agent':'Deagle-reproduction/1.0'})
    with urllib.request.urlopen(req,timeout=90) as r:
     if r.status!=206:raise IOError(f'Range refused: {r.status}')
     cr=r.headers.get('Content-Range','')
     if not cr.startswith(f'bytes {start}-'):raise IOError('Wrong range: '+cr)
     b=r.read(end-start+2)
    if len(b)!=end-start+1:raise IOError('Wrong length')
    self.ranges.append((start,end,b));self.pos+=n;return b[:n]
   except Exception:
    if attempt==3:raise
    time.sleep(2*(attempt+1))
def open_record(record):
 d=json.load(open(f'evidence/zenodo-{record}.json'));f=d['files'][0]
 h=HTTPRange(f['links']['self'],f['size']);return zipfile.ZipFile(h),h
if __name__=='__main__':
 for record in map(int,sys.argv[1:]):
  print('OPEN',record,flush=True)
  z,h=open_record(record);items=[{'name':i.filename,'size':i.file_size,'compressed':i.compress_size,'crc':i.CRC} for i in z.infolist()]
  pathlib.Path(f'evidence/zip-index-{record}.json').write_text(json.dumps(items))
  print('ENTRIES',len(items),'SAMPLES',items[:5],flush=True)
  if record==19736446:
   selected=[i for i in z.infolist() if 'deagle' in i.filename.lower() and (i.filename.endswith(('.zip','.bz2','.json.gz','.txt','.xml')))]
   for i in selected:
    if i.file_size>500000000:print('SKIP LARGE',i.filename,i.file_size,flush=True);continue
    p=pathlib.Path('archives/official-results')/i.filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(i));print('EXTRACTED',i.filename,i.file_size,flush=True)
