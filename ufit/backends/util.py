# ufit backend utilities

from ufit import UFitError

def prepare_data(data, limits):
    if limits == (None, None):
        return data.x, data.y, data.dy
    if limits[0] is None:
        indices = data.x <= limits[1]
    elif limits[1] is None:
        indices = data.x >= limits[0]
    else:
        indices = (data.x >= limits[0]) & (data.x <= limits[1])
    return data.x[indices], data.y[indices], data.dy[indices]

# XXX replace by something more safe later
param_eval = eval

def prepare_params(params, meta):
    # find parameters that need to vary
    dependent = {}
    varying = []
    varynames = []
    for p in params:
        if p.expr:
            dependent[p.name] = p.expr
        else:
            varying.append(p)
            varynames.append(p.name)

    pd = dict((p.name, p.value) for p in varying)
    pd['data'] = meta

    # poor man's dependency tracking of parameter expressions
    dep_order = []
    maxit = len(dependent) + 1
    while dependent:
        maxit -= 1
        if maxit == 0:
            raise UFitError('detected unresolved parameter dependencies '
                            'among %s' % dependent.keys())
        for p, expr in dependent.items():
            try:
                pd[p] = param_eval(expr, pd)
            except NameError:
                pass
            else:
                del dependent[p]
                dep_order.append((p, expr))
    #pd.pop('__builtins__', None)

    return varying, varynames, dep_order, pd


def update_params(parexprs, meta, pd):
    pd['data'] = meta
    for p, expr in parexprs:
        pd[p] = param_eval(expr, pd)
    #pd.pop('__builtins__', None)

def get_chisqr(fcn, x, y, dy, params):
    paramdict = dict((p.name, p.value) for p in params)
    sum_sqr = ((fcn(paramdict, x) - y)**2 / dy**2).sum()
    nfree = len(y) - sum(1 for p in params if not p.expr)
    return sum_sqr / nfree
