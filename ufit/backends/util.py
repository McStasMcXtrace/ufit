# ufit backend utilities

from ufit.core import UFitError

# XXX replace by something more safe later
param_eval = eval

def prepare_params(params, data):
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
    pd['__meta'] = data.meta

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

    return varying, varynames, dep_order, pd


def update_params(parexprs, data, pd):
    pd['__meta'] = data.meta
    for p, expr in parexprs:
        pd[p] = param_eval(expr, pd)
    #del pd['__builtins__']
