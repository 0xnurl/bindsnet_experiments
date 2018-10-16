import os
import torch
import argparse
import pandas as pd

from brian2 import *
from time import time as t
from experiments import ROOT_DIR

from bindsnet.network import Network
from bindsnet.network.topology import Connection
from bindsnet.network.nodes import Input, LIFNodes
from bindsnet.encoding import poisson

benchmark_path = os.path.join(ROOT_DIR, 'benchmark')
if not os.path.isdir(benchmark_path):
    os.makedirs(benchmark_path)


def bindsnet_cpu(n_neurons, time):
    torch.set_default_tensor_type('torch.FloatTensor')

    network = Network()
    network.add_layer(Input(n=n_neurons), name='X')
    network.add_layer(LIFNodes(n=n_neurons), name='Y')
    network.add_connection(
        Connection(source=network.layers['X'], target=network.layers['Y']), source='X', target='Y'
    )

    data = {'X': poisson(datum=torch.rand(n_neurons), time=time)}
    network.run(inpts=data, time=time)


def bindsnet_gpu(n_neurons, time):
    if torch.cuda.is_available():
        torch.set_default_tensor_type('torch.cuda.FloatTensor')

        network = Network()
        network.add_layer(Input(n=n_neurons), name='X')
        network.add_layer(LIFNodes(n=n_neurons), name='Y')
        network.add_connection(
            Connection(source=network.layers['X'], target=network.layers['Y']), source='X', target='Y'
        )

        data = {'X': poisson(datum=torch.rand(n_neurons), time=time)}
        network.run(inpts=data, time=time)


def brian(n_neurons, time):
    eqs_neurons = '''
        dv/dt = (ge * (-60 * mV) + (-74 * mV) - v) / (10 * ms) : volt
        dge/dt = -ge / (5 * ms) : 1
    '''

    input = PoissonGroup(n_neurons, rates=15 * Hz)
    neurons = NeuronGroup(
        n_neurons, eqs_neurons, threshold='v > (-54 * mV)', reset='v = -60 * mV', method='exact'
    )
    S = Synapses(input, neurons, '''w: 1''')
    S.connect()
    S.w = 'rand() * 0.01'

    run(time * ms)


def neuron(n_neurons, time):
    return

    r_ex = 5.0  # [Hz] rate of exc. neurons
    epsc = 45.0  # [pA] amplitude of exc.
    ipsc = -45.0  # [pA] amplitude of inh.

    # synaptic currents
    d = 1.0  # [ms] synaptic delay
    lower = 5.0  # [Hz] lower bound of the search interval
    upper = 25.0  # [Hz] upper bound of the search interval
    prec = 0.05  # accuracy goal (in percent of inhibitory rate)

    neuron = Create("iaf_neuron")
    noise = Create("poisson_generator", 2)
    voltmeter = Create("voltmeter")
    spikedetector = Create("spike_detector")


def nest(n_neurons, time):
    pass


def main(start=100, stop=1000, step=100, time=1000):
    f = os.path.join(benchmark_path, f'benchmark_{start}_{stop}_{step}_{time}.csv')
    if os.path.isfile(f):
        os.remove(f)

    times = {
        'bindsnet_cpu': [], 'bindsnet_gpu': [], 'brian': [], 'neuron': [], 'nest': []
    }

    for n_neurons in range(start, stop + step, step):
        print(f'\nRunning benchmark with {n_neurons} neurons.')
        for framework in times.keys():
            print(f'- {framework}:', end=' ')

            t1 = t()

            fn = globals()[framework]
            fn(n_neurons=n_neurons, time=time)

            elapsed = t() - t1
            times[framework].append(elapsed)

            print(f'(elapsed: {elapsed:.4f})')

    df = pd.DataFrame.from_dict(times)
    df.index = list(range(start, stop + step, step))

    print(df)
    print()

    df.to_csv(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=100)
    parser.add_argument('--stop', type=int, default=1000)
    parser.add_argument('--step', type=int, default=100)
    parser.add_argument('--time', type=int, default=1000)
    args = parser.parse_args()

    main(start=args.start, stop=args.stop, step=args.step, time=args.time)
