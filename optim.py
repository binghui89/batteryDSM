from __future__ import division
from pyomo.environ import *
from initialize import *
from pyomo.opt import SolverFactory
from matplotlib import pyplot as plt
from IPython import embed as IP

class Parameter():
    pass

param = Parameter()
param.charge_rate = 50 # charge rate, kW
param.deltaT      = 0.25 # Time interval, in hour
param.delta       = 0.88 # Healthy depth of discharge, dimentionless
param.s0          = 0 # Initial SOC of battery, dimentionless
param.eta         = 0.80 # Round-trip efficiency of battery, dimentionless
param.eta_I       = 0.95 # Inverter efficiency, dimentionless
param.inf         = 1E9 # Infinity
param.C_I         = 2000 # Installation cost, USD
param.C_C         = 200 # Battery capital cost, USD/kWh
param.r           = 0.1 # Discount rate, dimentionless
param.life        = 20 # Battery life time, years

model = AbstractModel()

# Sets
model.T     = Set( ordered = True ) # Time periods

# Parameters
model.demand                  = Param( model.T )
model.tariff_energy           = Param( model.T )
model.tariff_demand_original  = Param( model.T )
model.tariff_service          = Param()

# Additional sets and parameters
model.tar           = Set( initialize = Init_tar ) # Number of demand tariffs
model.T_tar         = Set( model.tar, within = model.T, initialize = Init_T_tar ) # Tariff time periods
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
def PeakLoad_Constraint( model, tar, t ):
    return model.yp[tar] >= model.y[t]
model.PeakLoadConstraint = Constraint(
    model.PeakLoad_tart, rule = PeakLoad_Constraint
)

def Battery_Constraint( model, t ):
    expr = (model.z[t] == model.z_plus[t] - model.z_minus[t])
    return expr
model.BatteryConstraint = Constraint( model.T, rule = Battery_Constraint)

def BatteryCharge_Constraint( model, t ):
    return model.z_plus[t] <= param.charge_rate*param.deltaT*(1 - model.b[t])
model.BatteryChargeConstraint = Constraint(
    model.T, rule = BatteryCharge_Constraint
)

def BatteryDischarge_Constraint( model, t ):
    return model.z_minus[t] <= param.charge_rate*param.deltaT*model.b[t]
model.BatteryDischargeConstraint = Constraint(
    model.T, rule = BatteryDischarge_Constraint
)

def BatteryLevelLower_Constraint( model, t ):
    lb = max( 0.05, (1 - param.delta)/2 )
    return model.s[t] >= lb*model.x
model.BatteryLevelLowerConstraint = Constraint(
    model.T, rule = BatteryLevelLower_Constraint
)

def BatteryLevelUpper_Constraint( model, t ):
    ub = 1 - (1 - param.delta)/2
    return model.s[t] <= ub*model.x
model.BatteryLevelUpperConstraint = Constraint(
    model.T, rule = BatteryLevelUpper_Constraint
)

def BatteryLevel_Constraint( model, t ):
    if t == model.T.first():
        return model.s[t] == param.s0 + model.z[t]
    else:
        t_prev = model.T.prev(t)
        return model.s[t] == model.s[t_prev] + model.z[t]
model.BatteryLevel_Constraint = Constraint(
    model.T, rule = BatteryLevel_Constraint
)

def DemandImprove_Constraint( model, t ):
    eta = sqrt(param.eta)*param.eta_I
    return model.y[t] == model.demand[t] + eta*model.z[t]/param.deltaT
model.DemandImproveConstraint = Constraint(
    model.T, rule = DemandImprove_Constraint
)

def DemandLimitUpper_Constraint( model, t ):
    return model.DL - model.demand[t] <= param.inf*(1 - model.b[t])
model.DemandLimitUpperConstraint = Constraint(
    model.T, rule = DemandLimitUpper_Constraint
)

def DemandLimitLower_Constraint( model, t ):
    return model.DL - model.demand[t] >= -1*param.inf*model.b[t]
model.DemandLimitLowerConstraint = Constraint(
    model.T, rule = DemandLimitLower_Constraint
)

def DemandImprovedUpper_Constraint( model, t ):
    # return model.y[t] - model.DL <= param.inf*model.b[t]
    return model.DL - model.y[t] <= param.inf*(1 - model.b[t])
model.DemandImprovedUpperConstraint = Constraint(
    model.T, rule = DemandImprovedUpper_Constraint
)

def DemandImprovedLower_Constraint( model, t ):
    # return model.y[t] - model.DL >= -1*param.inf*(1 - model.b[t])
    return model.DL - model.y[t] >= -1*param.inf*model.b[t]
model.DemandImprovedLowerConstraint = Constraint(
    model.T, rule = DemandImprovedLower_Constraint
)

# Objective function
def BatteryCost_rule(model):
    ccr = param.r*(1 + param.r)**param.life/( (1 + param.r)**param.life - 1 )
    return (param.C_I + param.C_C*model.x)/12*ccr

def Tariff_rule(model):
    bill_energy = sum(model.y[t]*model.tariff_energy[t] for t in model.T)
    bill_demand = sum(model.yp[i]*model.tariff_demand[i] for i in model.tar)
    return bill_energy + bill_demand + model.tariff_service

def Objective_rule(model):
    return BatteryCost_rule(model) + Tariff_rule(model)
model.TotalCost = Objective(rule=Objective_rule, sense=minimize)

def plot_instance(instance, xlimit=None):
    T  = list() # Time
    b  = list() # Binary variables
    z  = list() # Net battery energy exchange
    z_plus = list()
    z_minus = list()
    y  = list() # Improved load
    d  = list() # Original load
    s  = list() # SOC
    DL = list()
    for t in instance.T.iterkeys():
        T.append(t)
        b.append( value(instance.b[t]) )
        z.append( value(instance.z[t]) )
        z_plus.append( value(instance.z_plus[t]) )
        z_minus.append( value(instance.z_minus[t]) )
        y.append( value(instance.y[t]) )
        d.append( value(instance.demand[t]) )
        s.append( value(instance.s[t]) )
        DL.append( instance.DL.value )
    plt.figure()
    plt.plot(T, d, '-k', T, y, '-b', T, DL, '-r')
    plt.legend(['Demand', 'Improved demand', 'Demand limit'])
    plt.xlabel('Time (15-min)')
    plt.ylabel('Power (kW)')
    if xlimit:
        plt.xlim(xlimit)
    plt.figure()
    plt.plot(T, z, '-g', T, s, '-k')
    plt.legend(['Battery energy exchange', 'Battery energy level'])
    plt.xlabel('Time (15-min)')
    plt.ylabel('Energy (kWh)')
    if xlimit:
        plt.xlim(xlimit)
    plt.figure()
    plt.plot(T, b)
    if xlimit:
        plt.xlim(xlimit)
    plt.show()

if __name__ == "__main__":
    modeldata = DataPortal( model=model )
    modeldata.load( filename='test.dat' )
    instance = model.create_instance(modeldata)
    solver = SolverFactory('cplex')
    # solver.options['lpmethod'] = 2
    results = solver.solve(instance)
    instance.solutions.load_from(results)
    plot_instance(instance, [1, 1000])