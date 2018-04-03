from pyomo.environ import *
from IPython import embed as IP

def PeakLoadIndices( model ):
    indices = set(
        (tar, t)
        for tar in model.tar
        for t in model.T_tar[tar]
    )
    return indices

def Init_tar( model ):
    set_tariff_demand  = set(model.tariff_demand_original.values())
    list_tariff_demand = list(set_tariff_demand)
    indices = set()
    for p in list_tariff_demand:
        i = str(p)
        indices.add( i ) 
    return indices

def Init_T_tar( model, tar ):
    indices = set()
    for t, p in model.tariff_demand_original.iteritems():
        if abs(float(tar) - p) <= 1E-4:
            indices.add(t)
    return indices

def Init_tariff_demand( model, tar ):
    return float(tar)