"""Venn's fixed fmin downhill-simplex and Polak-Ribiere/Wolfe optimizers."""
import math

def bisect(f,a,b,iterations=100,tolerance=1e-10):
    fa=f(a);fb=f(b);delta=b-a
    if fa*fb>0:raise ValueError('Initial bisect points must have opposite signs')
    if not fa:return a
    if not fb:return b
    for _ in range(iterations):
        delta/=2;mid=a+delta;fm=f(mid)
        if fm*fa>=0:a=mid
        if abs(delta)<tolerance or not fm:return mid
    return a+delta

def nelder_mead(f,initial,iterations=None,error_delta=1e-6,tolerance=None):
    n=len(initial)
    if not n:return (),f(())
    simplex=[(list(initial),f(initial))]
    for i in range(n):
        point=list(initial);point[i]=point[i]*1.05 if point[i] else .001;simplex.append((point,f(point)))
    for _ in range(iterations or n*200):
        simplex.sort(key=lambda item:item[1]);best=simplex[0];worst=simplex[-1]
        if abs(best[1]-worst[1])<error_delta and max(abs(a-b) for a,b in zip(best[0],simplex[1][0]))<(tolerance if tolerance is not None else 1e-5):break
        center=[sum(simplex[j][0][i] for j in range(n))/n for i in range(n)]
        reflect=[2*a-b for a,b in zip(center,worst[0])];rf=f(reflect)
        if rf<best[1]:
            expanded=[3*a-2*b for a,b in zip(center,worst[0])];ef=f(expanded);simplex[-1]=(expanded,ef) if ef<rf else (reflect,rf)
        elif rf>=simplex[-2][1]:
            if rf>worst[1]:contract=[.5*a+.5*b for a,b in zip(center,worst[0])];threshold=worst[1]
            else:contract=[1.5*a-.5*b for a,b in zip(center,worst[0])];threshold=rf
            cf=f(contract)
            if cf<threshold:simplex[-1]=(contract,cf)
            else:
                for i in range(1,n+1):
                    point=[.5*a+.5*b for a,b in zip(best[0],simplex[i][0])];simplex[i]=(point,f(point))
        else:simplex[-1]=(reflect,rf)
    simplex.sort(key=lambda item:item[1]);return tuple(simplex[0][0]),simplex[0][1]

def dot(a,b):return sum(x*y for x,y in zip(a,b))

def conjugate_gradient(f,initial,iterations=None):
    def evaluate(point):gradient=[0.]*len(point);value=f(point,gradient);return list(point),value,gradient
    current=evaluate(initial);pk=[-g for g in current[2]];step=1.
    for _ in range(iterations or len(initial)*20):
        x,phi0,gradient=current;derivative0=dot(gradient,pk);a=step or 1.;oldphi=phi0;a0=0.;next_=current
        def zoom(lo,high,phi_lo):
            nonlocal next_
            for _ in range(16):
                mid=(lo+high)/2;next_=evaluate([v+mid*d for v,d in zip(x,pk)]);phi=next_[1];prime=dot(next_[2],pk)
                if phi>phi0+1e-6*mid*derivative0 or phi>=phi_lo:high=mid
                else:
                    if abs(prime)<=-.1*derivative0:return mid
                    if prime*(high-lo)>=0:high=lo
                    lo=mid;phi_lo=phi
            return 0.
        for i in range(10):
            next_=evaluate([v+a*d for v,d in zip(x,pk)]);phi=next_[1];prime=dot(next_[2],pk)
            if phi>phi0+1e-6*a*derivative0 or i and phi>=oldphi:step=zoom(a0,a,oldphi);break
            if abs(prime)<=-.1*derivative0:step=a;break
            if prime>=0:step=zoom(a,a0,phi);break
            oldphi=phi;a0=a;a*=2;step=a
        if not step:pk=[-g for g in current[2]]
        else:
            delta=dot(gradient,gradient);beta=max(0,dot([a-b for a,b in zip(next_[2],gradient)],next_[2])/delta) if delta else 0
            pk=[beta*d-g for d,g in zip(pk,next_[2])];current=next_
        if math.sqrt(dot(current[2],current[2]))<=1e-5:break
    return tuple(current[0]),current[1]
