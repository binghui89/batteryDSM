from __future__ import division
from pyomo.environ import *
from initialize import *
from pyomo.opt import SolverFactory
from matplotlib import pyplot as plt
import pandas as pd
from IPython import embed as IP

class Parameter():
    pass

param = Parameter()
param.c_rate      = 1 # Maximum C rate, h^(-1)
param.deltaT      = 0.25 # Time interval, in hour
param.delta       = 0.88 # Healthy depth of discharge, dimentionless
param.s0          = 0 # Initial SOC of battery, dimentionless
param.eta         = 0.80 # Round-trip efficiency of battery, dimentionless
param.eta_I       = 0.95 # Inverter efficiency, dimentionless
param.inf         = 1E6 # Infinity, be careful selecting the value
param.C_I         = 2000 # Installation cost, USD
param.C_C         = 200 # Battery capital cost, USD/kWh
param.r           = 0.1 # Discount rate, dimentionless
param.life        = 20 # Battery life time, years

# Constraint rules
def PeakLoad_Constraint( model, tar, t ):
    return model.yp[tar] >= model.y[t]

def Battery_Constraint( model, t ):
    expr = (model.z[t] == model.z_plus[t] - model.z_minus[t])
    return expr

def BatteryCharge_1_Constraint(model, t):
    return model.z_plus[t] <= param.inf*(1 - model.b[t])

def BatteryCharge_Constraint( model, t ):
    return model.z_plus[t] <= param.c_rate*param.deltaT*model.x

def BatteryDischarge_1_Constraint(model, t):
    return model.z_minus[t] <= param.inf*model.b[t]

def BatteryDischarge_Constraint( model, t ):
    return model.z_minus[t] <= param.c_rate*param.deltaT*model.x

def BatteryLevelLower_Constraint( model, t ):
    lb = max( 0.05, (1 - param.delta)/2 )
    return model.s[t] >= lb*model.x

def BatteryLevelUpper_Constraint( model, t ):
    ub = 1 - (1 - param.delta)/2
    return model.s[t] <= ub*model.x

def BatteryLevel_Constraint( model, t ):
    if t == model.T.first():
        return model.s[t] == param.s0 + model.z[t]
    else:
        t_prev = model.T.prev(t)
        return model.s[t] == model.s[t_prev] + model.z[t]

def DemandImprove_Constraint( model, t ):
    eta = sqrt(param.eta)*param.eta_I
    return model.y[t] == model.demand[t] + eta*model.z[t]/param.deltaT

def DemandLimitUpper_Constraint( model, t ):
    return model.DL - model.demand[t] <= param.inf*(1 - model.b[t])

def DemandLimitLower_Constraint( model, t ):
    return model.DL - model.demand[t] >= -1*param.inf*model.b[t]

def DemandImprovedUpper_Constraint( model, t ):
    return model.DL - model.y[t] <= param.inf*(1 - model.b[t])

def DemandImprovedLower_Constraint( model, t ):
    return model.DL - model.y[t] >= -1*param.inf*model.b[t]

# Objective function rules
def BatteryCost_rule(model):
    ccr = param.r*(1 + param.r)**param.life/( (1 + param.r)**param.life - 1 )
    return (param.C_I + param.C_C*model.x)/12*ccr

def Tariff_rule(model):
    bill_energy = sum(model.y[t]*model.tariff_energy[t] for t in model.T)
    bill_demand = sum(model.yp[i]*model.tariff_demand[i] for i in model.tar)
    return bill_energy + bill_demand + model.tariff_service

def Objective_rule(model):
    return BatteryCost_rule(model) + Tariff_rule(model)

def build_model(df=None):
    model = AbstractModel()

    # Parameters
    if df is None:
        model.T                       = Set( ordered = True ) # Time periods
        model.demand                  = Param( model.T )
        model.tariff_energy           = Param( model.T )
        model.tariff_demand_original  = Param( model.T ) # The original demand tariff indexed by T
        model.tariff_service          = Param()
    else:
        model.T                       = Set( ordered = True, initialize=df.index) # Time periods
        model.demand                  = Param( model.T, initialize=df['Demand (kW)'].to_dict() )
        model.tariff_energy           = Param( model.T, initialize=df['Tariff (energy)'].to_dict() )
        model.tariff_demand_original  = Param( model.T, initialize=df['Tariff (demand)'].to_dict() ) # The original demand tariff indexed by T
        model.tariff_service          = Param( initialize=df['Tariff (service)'].iloc[0] )

    # Additional sets and parameters
    model.tar           = Set( initialize = Init_tar ) # Number of demand tariffs
    model.T_tar         = Set(
        model.tar, within = model.T, initialize = Init_T_tar
    ) # Tariff time periods
    # The actual demand tariff input to the model
    model.tariff_demand = Param( model.tar, initialize = Init_tariff_demand ) 
    model.PeakLoad_tart = Set( dimen = 2, initialize = PeakLoadIndices )

    # Decision variables
    model.x       = Var( domain = NonNegativeReals )
    model.DL      = Var( domain = NonNegativeReals ) # Demand limit
    model.y       = Var( model.T, domain = NonNegativeReals )
    model.yp      = Var( model.tar, domain = NonNegativeReals )
    model.z_plus  = Var( model.T, domain = NonNegativeReals )
    model.z_minus = Var( model.T, domain = NonNegativeReals )
    model.z       = Var( model.T, domain = Reals )
    model.s       = Var( model.T, domain = NonNegativeReals )
    model.b       = Var( model.T, domain = Binary ) # 0: Charge, 1: Discharge

    # Constraints
    model.PeakLoadConstraint = Constraint(
        model.PeakLoad_tart, rule = PeakLoad_Constraint
    )
    model.BatteryConstraint = Constraint( model.T, rule = Battery_Constraint)
    model.BatteryCharge_1Constraint = Constraint(
        model.T, rule = BatteryCharge_1_Constraint
    )
    model.BatteryChargeConstraint = Constraint(
        model.T, rule = BatteryCharge_Constraint
    )
    model.BatteryDischarge_1Constraint = Constraint(
        model.T, rule = BatteryDischarge_1_Constraint
    )
    model.BatteryDischargeConstraint = Constraint(
        model.T, rule = BatteryDischarge_Constraint
    )
    model.BatteryLevelLowerConstraint = Constraint(
        model.T, rule = BatteryLevelLower_Constraint
    )
    model.BatteryLevelUpperConstraint = Constraint(
        model.T, rule = BatteryLevelUpper_Constraint
    )
    model.BatteryLevel_Constraint = Constraint(
        model.T, rule = BatteryLevel_Constraint
    )
    model.DemandImproveConstraint = Constraint(
        model.T, rule = DemandImprove_Constraint
    )
    model.DemandLimitUpperConstraint = Constraint(
        model.T, rule = DemandLimitUpper_Constraint
    )
    model.DemandLimitLowerConstraint = Constraint(
        model.T, rule = DemandLimitLower_Constraint
    )
    model.DemandImprovedUpperConstraint = Constraint(
        model.T, rule = DemandImprovedUpper_Constraint
    )
    model.DemandImprovedLowerConstraint = Constraint(
        model.T, rule = DemandImprovedLower_Constraint
    )

    # Objective function
    model.TotalCost = Objective(rule=Objective_rule, sense=minimize)

    return model

model = build_model()

if __name__ == "__main__":
    modeldata = DataPortal( model=model )
    modeldata.load( filename='test.dat' )
    instance = model.create_instance(modeldata)
    solver = SolverFactory('cplex')
    # solver.options['lpmethod'] = 2
    # solver.options['mip tolerances integrality'] = 1e-15
    results = solver.solve(instance)
    instance.solutions.load_from(results)