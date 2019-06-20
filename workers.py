def get_our_quants(data):
        return np.nanquantile(data, [.01, .05, .1, .25, .5, .75, .9, .95, .99], axis=0, overwrite_input=False, interpolation='linear', keepdims=False)