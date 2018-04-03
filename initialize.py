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
        # i = (p, )
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

# def Initialize_tar_demand( model ):
#     set_tariff_demand  = set(model.tariff_demand_original.values())
#     list_tariff_demand = list(set_tariff_demand)
#     dict_T_tar         = dict()
#     dict_tariff_demand = dict()
#     for p in list_tariff_demand:
#         i = list_tariff_demand.index(p) + 1 # Let's start from 1
#         dict_T_tar[i] = set()
#         dict_tariff_demand[i] = p
#     for t, p in model.tariff_demand_original.iteritems():
#         i = list_tariff_demand.index(p) + 1
#         dict_T_tar[i].add(t)
#     model.tar   = Set(initialize = set( dict_T_tar.keys() )) # Number of demand tariffs
#     model.T_tar = Set( model.tar, within = model.T, initialize = dict_T_tar ) # Tariff time periods
#     model.PeakLoad_tart = Set( initialize = PeakLoadIndices )
#     # model.tariff_demand = dict_tariff_demand
#     model.tariff_demand = Param( model.tar, initialize = dict_tariff_demand )