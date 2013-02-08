# ufit backend utilities

def update_evalpars(pars, d):
    # XXX poor man's dependency tracking
    rest = pars.copy()
    while rest:
        for p, expr in rest.items():
            try:
                d[p] = eval(expr, d)
            except NameError:
                pass
            else:
                del rest[p]
    del d['__builtins__']
