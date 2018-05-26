#  -*- coding: utf-8 -*-
# *****************************************************************************
# ufit, a universal scattering fitting suite
#
# Copyright (c) 2013-2018, Georg Brandl and contributors.  All rights reserved.
# Licensed under a 2-clause BSD license, see LICENSE.
# *****************************************************************************

"""Backend using "unifit" leastsq algorithm."""

from copy import copy
from time import time
from numpy import sqrt, infty, ones, zeros, absolute, maximum, minimum, \
    finfo, corrcoef, nonzero, diag, isnan, dot
from numpy.linalg import svd, pinv

from ufit.param import prepare_params, update_params
from ufit.utils import get_chisqr

__all__ = ['do_fit', 'backend_name']

backend_name = 'unifit'


def do_fit(data, fcn, params, add_kw):
    x, y, dy = data.fit_columns
    meta = data.meta
    varying, varynames, dependent, _ = prepare_params(params, meta)

    def leastsqfcn(x, params):
        pd = dict(zip(varynames, params))
        update_params(dependent, meta, pd)
        return fcn(pd, x)

    initpars = []
    initdp = []
    warned = False
    for p in varying:
        initpars.append(p.value)
        initdp.append(p.delta or p.value/10. or 0.01)
        if (p.pmin is not None or p.pmax is not None) and not warned:
            print('Sorry, unifit backend cannot handle parameter bounds.')
            warned = True
    try:
        res = __leastsq((x, y, dy), leastsqfcn, initpars, initdp,
                        **add_kw)
    except Exception as e:
        raise
        return False, str(e), 0

    success = res['converged']
    errmsg = res['errmsg']

    pd = {}
    for i, p in enumerate(varying):
        pd[p.name] = res['values'][i]
        p.error = res['errors'][i]
        p.correl = {}  # XXX
    update_params(dependent, meta, pd)
    for p in params:
        p.value = pd[p.name]

    return success, errmsg, get_chisqr(fcn, x, y, dy, params)


class FitError(Exception):
    pass


def __dfdp(x, f, p, dp, func):
    """
    Returns the partial derivatives of function 'func'.
    'x'(vect) is x axis values, 'y' is y values, 'p' and 'dp' are
    parameters and their variation.
    output 'df/dp' is a vector(or matrix) of partials varying of 'dp'.
    """

    y = zeros((len(x), len(p)))
    # pp = copy(p)
    dpp = copy(dp)

    for i in range(len(p)):
        pp = copy(p)
        if dpp[i] == 0.0:
            dpp[i] = 0.00001
        pp[i] = p[i] + dpp[i]
        t = func(x, pp)
        y[:, i] = (t-f)/dpp[i]
    return y


def __leastsq(xyw, func, p, dp, niter=50, mode='print', eps=1e-3):
    """Levenberg-Marquardt nonlinear regression of func(x,p) to y(x).

             ---------------
    OPTIONS IN:
      niter (integ) : maximal number of iterations (50 is default).
      mode (string) : can be 'print' or 'silent'. In silent mode output is not written to standard out
                      but is saved in a message string.

    Author:  EF <manuf@ldv.univ-montp2.fr>, RM <rfm2@ds2.uh.cwru.edu>, AJ <jutan@charon.engga.uwo.ca>
    Description: Non Linear Least Square multivariable fit.

    Adapted for Octave : E.Farhi.   04/98   (manuf@ldv.univ-montp2.fr)
    Richard I. Shrager (301)-496-1122
    Modified by A.Jutan (519)-679-2111  jutan@charon.engga.uwo.ca
    Modified by Ray Muzic 14-Jul-1992   rfm2@ds2.uh.cwru.edu

    Version 3.beta    revised 07/97.
    Part of 'Spectral tools'. E.Farhi. 06/97

    Adapted for python: M. Janoschek 12/2008 (marc.janoschek@frm2.tum.de)
    Refrences:
    Bard, Nonlinear Parameter Estimation, Academic Press, 1974.
    Draper and Smith, Applied Regression Analysis, John Wiley and Sons, 1981.
    """
    (x, y, wt) = xyw
    options = zeros((len(p),2))            #desired fractional precision in parameter estimates.
    options[:,1] = ones(len(p)) * infty    #maximum fractional step change in parameter vector.
                        #not yet implemented standards are set (zero for precision, infty for max change)
    #instr_p = self.add_pars                                #additional parameters that are NOT fitted
    #func = self.__getfunc(self.func, self.add_pars)        #python function object of the form 'y=f(x,instr_p)'.

    stol = eps      #tolerance on square error sum fractional improvement (1e-3 is default)


    #cycle message (mainly for silent mode)
    cyclemsg = ''
    errmsg = ''

    if not all(dp):
        raise FitError('no dp given for some parameters')

    #check if data vector have the same length
    m = len(y)
    n = len(p)
    ##w = len(wt)
    sh = x.shape
    m1 = sh[0]
    ##if len(sh) > 1:
    ##    m2 = sh[1]
    ##else:
    ##    m2 = 1

    if m1 != m:
      raise FitError('Input(x)/output(y) data must have same number of rows!')

    if len(options) == 0:
        options = zeros((n,2))
        options[:,1] = ones(n) * infty
    else:
        nor, noc = options.shape

        if nor != n:
            raise FitError('Options and parameter matrices must have same number of rows!')

        if noc != 2:
            options = zeros((n,2))
            options[:,1] = ones(n) * infty

    pprec = options[:,0]
    maxstep = options[:,1]

    #apply parameter constraints
    ##p = self.__apply_constraints(p)

    #setup for iterations (with initial data)
    f = func(x, p)
    fbest = copy(f)              #initial function values
    pbest = copy(p)              #initial parameters
    r     = wt*(y-f)             #error (elementwise multiplication of columnvectors
    sbest = dot(r,r)
    ss = sbest
    nrm = zeros(n)
    chgbrev = infty*ones(n)
    kvg = False
    epsLlast = 1
    epstab = [0.1, 1, 1e2, 1e4, 1e6]

    #print header for fitting cycles if direct output was demanded by user
    if mode == 'print':
        print('Iteration  Time(s)  Residual Variance')
        print('=====================================')
        print('%5i    %7.2f    %8.3f' % (0, 0, sbest/len(y)))

    for iteration in range(niter):
        t0 = time()
        pprev = copy(pbest) #current paras
        #print pprev
        prt   = __dfdp(x, fbest, pprev, dp, func) #partials of func for x
        r     = wt*(y-fbest)        #error
        sprev = copy(sbest)        #square error
        sgoal = (1-stol)*sprev        #square error to achieve

        for j in range(n):        #compute partials norm
            if dp[j] == 0.0:
                nrm[j] = 0.0
            else:
                prt[:,j] = wt*prt[:,j]
                nrm[j]   = dot(prt[:,j],prt[:,j])
                if nrm[j] > 0:
                    nrm[j] = 1./sqrt(nrm[j])

            prt[:,j] = nrm[j]*prt[:,j]    #normalizes partials

        prt,s,v = svd(prt, full_matrices=False)        #prt=unit matr, s=eigenval : prt=prt*s*v.T
        v = v.T
        g = dot(prt.T,r)            #gradient by Gauss-Newton formula

        for k in range(len(epstab)):
            epsL = maximum(epsLlast*epstab[k],1e-7)
            se  = sqrt(s*s+epsL)
            gse = g/se
            chg = dot(v,gse)*nrm    #change on params
                        #check the change constraints and apply is necessary
            for l in range(n):
                if maxstep[l] == infty:
                    break
                chg[l] = maximum(chg[l], -1 * absolute(maxstep[l]*pprev[l]))
                chg[l] = minimum(chg[l], absolute(maxstep[l]*pprev[l]))

            aprec = absolute(pprec*pbest)
            if any(absolute(chg) > 0.1*aprec):
                #only worth evaluating function if there is some non-miniscule change
                p = chg+pprev

                #apply parameter constraints
                ##p = self.__apply_constraints(p)

                f = func(x, p)
                r = wt*(y-f)
                ss = dot(r,r)
                if ss < sbest:
                    pbest = copy(p)
                    fbest = copy(f)
                    sbest = copy(ss)

                if ss <= sgoal:
                    #print 'ss <= sgoal', ss, sgoal
                    break

        epsLlast = epsL
        if ss < finfo(float).eps:
            print('Sum of squares within machine precision')
            break # machine precession

        aprec=absolute(pprec*pbest)
        if ((absolute(chg)).all() < aprec.all()) and ((absolute(chgprev)).all() < aprec.all()):
            kvg = True
            print('Parameter changes converged to specified precision')
            break
        else:
            chgprev = chg
            if ss > sgoal:
                #print 'ss > sgoal in outer loop!'
                break

        dt = time()-t0
        cyclemsg = '%5i    %7.2f    %8.3f' % (iteration+1, dt, ss/len(y))
        if mode == 'print':
            print(cyclemsg)

    kvg = (sbest > sgoal)

    #set return values
    p = copy(pbest)
    f = copy(fbest)
    ss = copy(sbest)
    kvg = (kvg or (sbest <= finfo(float).eps) or kvg)

    if not kvg:
        errmsg += '** CONVERGENCE NOT ACHIEVED! **\n'
    else:
        print('===== Converged =====================')

    #Calculate R (Ref Draper & Smith p.46)
    r=corrcoef(y*wt,f*wt)
    r2=r*r.T
    ss = sum(wt*(f-y))/len(y)

    #calculate variance cov matrix and correlation matrix of parameters
    #re-evaluate the Jacobian at optimal values
    jac = __dfdp(x, fbest, pprev, dp, func)
    ##msk = nonzero(dp)[0]
    ##n = len(msk)        # dfdp(x,fbest,pprev,dp,func, instr_p)
    ##jac = jac[:,msk]        # use only fitted parameters

    # following section is Ray Muzic's estimate for covariance and correlation
    # assuming covariance of data is a diagonal matrix proportional to
    # diag(1/wt.^2).
    # cov matrix of data est. from Bard Eq. 7-5-13, and Row 1 Table 5.1

    Qinv = diag(wt*wt)
    Q = diag((0*wt+1)/(wt**2))

    resid = y-f            #unweighted residuals
    covr=dot(resid.T,dot(Qinv,dot(resid,Q)))/(m-n) # covariance of residuals
    Vy=1/(1-n/m)*covr          # Eq. 7-13-22, Bard    covariance of the data

    jtgjinv=pinv(dot(jac.T,dot(Qinv,jac))) #pinv = pseudo-inverse of matrix

    if not isnan(jtgjinv).all():
        # Eq. 7-5-13, Bard cov of parmater estimates
        covp = dot(jtgjinv,dot(jac.T,dot(Qinv,dot(Vy,dot(Qinv,dot(jac,jtgjinv))))))

        corp = ones((n,n))
        for k in range(n):
            for j in range(k,n):
                if covp[k,k]*covp[j,j]:
                    corp[k,j] = covp[k,j]/sqrt(abs(covp[k,k]*covp[j,j]))

    else:
        errmsg += "Warning : leasqr : couldn\'t compute squared Jacobian inverse matrix (no covp, no corp).\n"
        covp = zeros((n,n))
        corp = ones((n,n))

    deltap = sqrt(diag(covp))

    res = {}
    res['values'] = []
    res['errors'] = []

    for i in range(len(p)):
        res['values'].append(p[i])
        res['errors'].append(deltap[i])

    #work out chi2
    v = len(y) - len(nonzero(dp))
    ChiSq = sum((wt*(f-y))**2)/v

    #write back results:
    res['converged'] = kvg
    res['cycles'] = iteration

    res['covmat'] = covp
    res['corr'] = corp
    res['errmsg'] = errmsg
    res['rchi2'] = ChiSq
    res['rv'] = sbest/len(y)
    res['r2'] = r2
    res['ycalc'] = f

    return res
