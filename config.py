# Makes dictionaries dottable with keys:
# Instead of dict['key] you then use dict.key

class DotDict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__