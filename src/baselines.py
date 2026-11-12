"""Partial scores, not clinical implementations. Missing components score zero."""
import numpy as np
def scores(d):
 # Values are patient-wise LOCF; still missing means unobserved (zero points).
 rr,sat,sbp,hr,t=[d[c] for c in ["Resp","O2Sat","SBP","HR","Temp"]]
 q=(rr>=22).astype(int)+(sbp<=100).astype(int)
 n=np.select([rr<=8,rr<=11,rr<=20,rr<=24,rr>24],[3,1,0,2,3],0)
 n+=np.select([sat<=91,sat<=93,sat<=95,sat>=96],[3,2,1,0],0)
 n+=np.select([sbp<=90,sbp<=100,sbp<=110,sbp<=219,sbp>=220],[3,2,1,0,3],0)
 n+=np.select([hr<=40,hr<=50,hr<=90,hr<=110,hr<=130,hr>130],[3,1,0,1,2,3],0)
 n+=np.select([t<=35,t<=36,t<=38,t<=39,t>39],[3,1,0,1,2],0)
 return q,n
