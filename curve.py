import numpy as np
from matplotlib import pyplot as plt
from IPython import embed as IP

def degrade(Crate, T, Ah):
    # Eqn 5, Wang, John, et al. "Cycle-life model for graphite-LiFePO4 cells." Journal of Power Sources 196.8 (2011): 3942-3948.
    B = 30330
    Qloss = B*np.exp( (-31700 + 370.3*Crate)/(8.314*T) )*Ah**0.552
    Qloss_percent = Qloss/1E2
    return Qloss_percent

def piecewiselinear(Crate, T):
    Ah1 = 2500
    Ah2 = 15000
    Q1  = degrade(Crate, T, Ah1)
    Q2  = degrade(Crate, T, Ah2)
    k1  = Q1/Ah1
    b1  = 0
    k2  = (Q2 - Q1)/(Ah2 - Ah1)
    results = {
        'k1':  k1,
        'b1':  b1,
        'k2':  k2,
        'Ah1': Ah1,
        'Ah2': Ah2,
    }
    return results

if __name__ == "__main__":
    t = np.array( range(1, 8761) )
    Crate = 1 # h^(-1)
    cap = 2.2 # Ah
    T = 273.15 + 25 # Kelvin
    throughput = Crate*cap*t
    Qloss_percent = degrade(Crate, T, throughput)
    plt.plot(throughput, Qloss_percent, 'k', label = 'Want et al.')
    x = np.array( [0, 1424] )
    y = degrade(Crate, T, x)
    plt.plot(x, y, 'r', label = '1 piece')
    x = np.array( [0, 2500, 15000] )
    y = degrade(Crate, T, x)
    plt.plot(x, y, 'b', label = '2 piece')
    plt.xlabel("Throughput (Ah)")
    plt.ylabel("Qloss")
    plt.legend()
    plt.show()