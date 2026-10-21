import pathlib,re,base64,argparse
parser=argparse.ArgumentParser();parser.add_argument('--out',default='outputs');args=parser.parse_args()
R=pathlib.Path(args.out);p=R/'Deagle-SVCOMP2026-中文报告.html';s=p.read_text(encoding='utf-8');count=0
def replace(m):
 global count
 b=(R/m[1]).read_bytes();count+=1;return 'src="data:image/png;base64,'+base64.b64encode(b).decode()+'"'
s=re.sub(r'src="(figures/[^\"]+\.png)"',replace,s);p.write_text(s,encoding='utf-8');print('Embedded figures',count)
