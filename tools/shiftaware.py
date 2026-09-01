#!/usr/bin/env python3
"""Compare scanner findings between variants WITH line-shift correction.

A fix that inserts lines moves every finding below it. Comparing (rule, line) pairs naively then
reports those as present-only-on-the-vulnerable-variant, which reads as a detection and is an
artefact of arithmetic. Solend alone produced six such phantoms.

For each insecure finding at line L we map L to its position in the fixed file using the diff
hunks, then ask whether the same rule fires there. Only a finding with no counterpart is real.
"""
import json,os,re,subprocess,sys

TOL=3

def hunks(repo, fix, path):
    out=subprocess.run(["git","diff","--unified=0",f"{fix}^",fix,"--",path],
                       cwd=repo,capture_output=True,text=True).stdout
    hs=[]
    for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",out,re.M):
        os_,oc=int(m.group(1)),int(m.group(2) or 1)
        ns,nc=int(m.group(3)),int(m.group(4) or 1)
        hs.append((os_,oc,ns,nc))
    return hs

def map_line(L,hs):
    """Line L in the parent -> its line in the child, or None if the fix removed it."""
    delta=0
    for os_,oc,ns,nc in hs:
        if L < os_: break
        if os_ <= L < os_+oc: return None      # inside a changed region
        delta = (ns+nc) - (os_+oc)
    return L+delta

def changed(hs):
    s=set()
    for os_,oc,_,_ in hs:
        for i in range(os_, os_+max(oc,1)+1): s.add(i)
    return s

def load(p):
    d=json.load(open(p)); items=d if isinstance(d,list) else d.get("findings",[])
    out=[]
    for it in items:
        n=it.get("name") or it.get("rule_name")
        for loc in it.get("locations",[]):
            m=re.match(r"^(.*?):(\d+):",loc)
            if m: out.append((n,re.sub(r"^.*/(insecure|secure)/","",m.group(1)),int(m.group(2))))
    return out


def main(out_dir="/tmp/c2crates-radar", manifest="/tmp/c2crates/manifest.json"):
    """Everything below used to run at import time, which made this module impossible to import
    and therefore impossible to test - which is exactly why the tool that corrected 23 phantom
    detections had no tests of its own. Wrapped so the functions above can be exercised."""
    OUT = out_dir
    man = json.load(open(manifest))
    real=0
    for c in man["cases"]:
        n=c["name"]
        fi,fs=f"{OUT}/{n}.insecure.json",f"{OUT}/{n}.secure.json"
        if not (os.path.exists(fi) and os.path.exists(fs)):
            print(f"{n:30} PAIR INCOMPLETE - not scored"); continue
        if c.get("valid",True) is False:
            print(f"{n:30} EXCLUDED - manifest marks the pair invalid"); continue
        repo="/tmp/c2cache/"+c["repo"].replace("/","__")
        files=c.get("files") or []
        ins,sec=load(fi),load(fs)
        sec_set=set((r,p,l) for r,p,l in sec)
        survivors=[]
        for r,p,L in ins:
            target=[f for f in files if p.endswith(os.path.basename(f))]
            hs=hunks(repo,c["fix"],target[0]) if target else []
            m=map_line(L,hs) if hs else L
            if m is None: continue                       # the fix deleted this line outright
            if any((r,p,m+d) in sec_set for d in range(-TOL,TOL+1)): continue
            survivors.append((r,p,L,hs))
        print(f"{n:30} insecure={len(ins):4} secure={len(sec):4} survives-shift-correction={len(survivors)}")
        for r,p,L,hs in survivors:
            ch=changed(hs)
            at = "*** AT FIX SITE ***" if any(abs(L-x)<=TOL for x in ch) else "not at fix site"
            print(f"      {r:34} {p.split(chr(47))[-1]}:{L:<6} {at}")
            if at.startswith("***"): real+=1
    print(f"\nRadar on real crates: {real} finding(s) that are differential AND at the fix site")



if __name__ == "__main__":
    main()
