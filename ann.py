import numpy as np
from typing import Callable
import activations
import deltafuncs
import deltacoef
import networkx as nx
import matplotlib.pyplot as plt
import random
from enum import Enum

class StopReason(Enum):
    MAX_ITERATIONS = 1
    CONVERGENCE = 2

class Neuron(object):
    def __init__(
        self,
        activation: Callable | str = 'sigmoid',
        weights: list[float] = None,
    ):
        self.activation = activation
        if isinstance(activation, str):
            self.activation: Callable = getattr(activations, activation)
            self.delta_func: Callable = getattr(deltafuncs, activation)
            self.delta_coef: Callable = getattr(deltacoef, activation)
        self.weights = weights
        self.value = 0
        self.delta_err = 0
        self.delta_weights = [0 for _ in range(len(weights))]

    def __call__(self, x: list[float]):
        # feed forward
        val = np.dot(x, self.weights)
        self.value = self.activation(val)
        return self.value

    def __repr__(self):
        return f'Neuron({self.activation.__name__}, {self.weights})'

    def reset_value(self):
        self.value = 0

    def reset_delta_err(self):
        self.delta_err = 0

    def reset_delta_weights(self):
        self.delta_weights = [0 for _ in range(len(self.weights))]
    
    def update_weights(self, batch_size: int):
        for i in range(len(self.delta_weights)):
            self.weights[i] += self.delta_weights[i] / batch_size

class LayerType(Enum):
    OUTPUT = 1
    HIDDEN = 2

class Layer(object):
    def __init__(
        self,
        neurons: list[Neuron] | int,
        name: str = '',
        activation: Callable | str = '',
        weights: list[list[float]] = None,
        bias: float = 1,
        input_shape=0,
    ) -> None:
        self.name = name
        self.activation = activation
        if isinstance(activation, str):
            self.activation: Callable = getattr(activations, activation)
            self.delta_func: Callable = getattr(deltafuncs, activation)
            self.delta_coef: Callable = getattr(deltacoef, activation)
        self.neurons = neurons
        if isinstance(neurons, int):
            self.neurons: list[Neuron] = [
                Neuron(activation, weights[i] if weights else 0)
                for i in range(neurons)
            ]
        self.bias = bias
        self.input_shape = input_shape

    def get_output_shape(self):
        return len(self.neurons)
    
    def get_values(self):
        return [neuron.value for neuron in self.neurons]

    def get_params_count(self):
        return (self.input_shape + 1) * len(self.neurons) 

    def get_weights(self):
        return np.array([neuron.weights for neuron in self.neurons])

    def __call__(self, inputs: list[float]) -> list[float]:
        # feed forward
        out = [neuron(inputs) for neuron in self.neurons]
        if self.activation is activations.softmax: # TODO: RECHECK
            out = (out / sum(out)).tolist()
        return out

    def __repr__(self):
        activation_name = self.activation.__name__
        weights = self.get_weights()
        param_count = self.get_params_count()

        return ''.join([
            'Layer(',
            f'activation={activation_name},',
            f'weights={weights},',
            f'bias={self.bias},',
            f'param_count={param_count}',
            ')',
        ])
    
    def reset_value(self):
        for neuron in self.neurons:
            neuron.reset_value()

    def reset_delta_err(self):
        for neuron in self.neurons:
            neuron.reset_delta_err()
        
    def reset_delta_weights(self):
        for neuron in self.neurons:
            neuron.reset_delta_weights()

    def calc(self, type: LayerType, prev_values: list[float], learning_rate: float, expected: list[float] = [], next_neurons: list[Neuron] = None):
        if (type == LayerType.OUTPUT):
            for j in range(len(self.neurons)):
                neuron = self.neurons[j]
                neuron.delta_err = self.delta_func(expected[j], neuron.value)
                for k, _ in enumerate(neuron.delta_weights): # TODO: RECHECK
                    neuron.delta_weights[k] += -learning_rate * neuron.delta_err * prev_values[k]
        elif (type == LayerType.HIDDEN):
            for j in range(len(self.neurons)):
                neuron = self.neurons[j]
                sum = 0
                for k in range(len(next_neurons)):
                    next_neuron = next_neurons[k]
                    sum += next_neuron.delta_err * next_neuron.weights[j]
                neuron.delta_err = self.delta_coef(neuron.value) * sum
                for k in range(len(neuron.delta_weights)):
                    neuron.delta_weights[k] += -learning_rate * neuron.delta_err * prev_values[k]

    def update_weights(self, batch_size: int):
        for i in range(len(self.neurons)):
            self.neurons[i].update_weights(batch_size)

class Model(object):
    def __init__(self, layers: list[Layer] = None,
        learning_rate: float = 0.1,
        batch_size: int = 10,
        max_iterations: int = 100,
        error_threshold: float = 0.1,
    ) -> None:
        self.layers = layers
        if layers is None:
            self.layers: list[Layer] = []
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.max_iteration = max_iterations
        self.error_threshold = error_threshold

    def add(self, layer: Layer) -> None:
        if self.layers:
            layer.input_shape = self.layers[-1].get_output_shape()
        self.layers.append(layer)

    def get_params_count(self):
        return sum([layer.get_params_count() for layer in self.layers])

    def summary(self):
        print(f'Model with {self.get_params_count()} parameters')
        print(f'Learning rate={self.learning_rate}')
        print(f'Batch size={self.batch_size}')
        print(f'Max iteration={self.max_iteration}')
        print(f'Error threshold={self.error_threshold}')
        for layer in self.layers:
            print(layer)

    def draw(self):
        graph = nx.DiGraph()

        # draw input layer
        num_inputs = self.layers[0].input_shape
        for i in range(num_inputs):
            graph.add_node(f'i_{i}', color='green', pos=(0,-i))

        # draw hidden layers
        for i, layer in enumerate(self.layers):
            graph.add_node(f'b_{i}', color='black', pos=(i + 0.25, -layer.input_shape))
            for j, neuron in enumerate(layer.neurons):
                color = 'blue' if i < len(self.layers) - 1 else 'red'
                cur_node = f'h_{i}_{j}' if i < len(self.layers) - 1 else f'o_{j}'
                graph.add_node(cur_node, color=color, pos=(i+1, -j + random.randrange(-3, 3) * 0.1))

                for k, weight in enumerate(neuron.weights):
                    src = f'b_{i}' if k == len(neuron.weights) - 1 else (f'i_{k}' if i == 0 else f'h_{i-1}_{k}')
                    graph.add_edge(src, cur_node, weight=weight)
            
        # draw graph
        pos = nx.get_node_attributes(graph, 'pos')
        edge_labels = nx.get_edge_attributes(graph, 'weight')

        # make plot bigger
        plot = plt.gca()
        plot.figure.set_size_inches(10, 10)
        plot.set_title('Feed Forward Neural Network Model')

        nx.draw(graph, pos, with_labels=True, node_color=[graph.nodes[node].get('color') for node in graph.nodes], node_size=1000, font_size=8, font_color='white', ax=plot)
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=8, ax=plot)


    def single_predict(self, input: list[float]):
        out = list(input)
        for layer in self.layers:
            out.append(1)
            out = layer(out)
        return out

    def __call__(self, inputs: list[list[float]]):
        # feed forward
        outputs: list[list[float]] = []
        for input in inputs:
            out = list(input)
            for layer in self.layers:
                out.append(1)
                out = layer(out)
            outputs.append(out)

        return outputs

    def get_prev_values(self, idx: int, inputs: list[float]):
        bias = 1
        if idx == 0:
            return list(inputs.copy()) + [bias]
        else:
            return self.layers[idx-1].get_values() + [bias]

    def propagate(self, inputs: list[float], expected: list[float], learning_rate: float):
        _ = self.single_predict(inputs)

        num = len(self.layers)
        for i in range(num-1, -1, -1):
            layer = self.layers[i]
            prev_layer_values = self.get_prev_values(i, inputs)
            if (i == (num-1)): # output layer
                layer.calc(LayerType.OUTPUT, prev_layer_values, learning_rate, expected)
            else:
                next_layer = self.layers[i+1]
                layer.calc(LayerType.HIDDEN, prev_layer_values, learning_rate, None, next_layer.neurons)

    def reset_value(self):
        for layer in self.layers:
            layer.reset_value()
    
    def reset_delta_err(self):
        for layer in self.layers:
            layer.reset_delta_err()

    def reset_delta_weights(self):
        for layer in self.layers:
            layer.reset_delta_weights()

    def multi_propagates(self, inputs: list[list[float]], expected: list[list[float]], learning_rate: float):
        num = len(inputs)
        for i in range(num):
            self.propagate(inputs[i], expected[i], learning_rate)
            self.reset_value()
            self.reset_delta_err()

    def update_weights(self, batch_size: int):
        for i in range(len(self.layers)):
            layer = self.layers[i]
            layer.update_weights(batch_size)

    def calc_total_err(self, inputs: list[list[float]], expected: list[list[float]]):
        res = self(inputs)
        # print(res)
        total_err = 0
        for i in range(len(res)):
            for j in range(len(res[i])):
                total_err += (res[i][j] - expected[i][j]) ** 2
        return total_err

    def fit(
        self, 
        inputs: list[list[float]], 
        expected: list[list[float]],
    ):
        num = len(inputs)
        for i in range(self.max_iteration):
            permut = np.random.permutation(num)
            for j in range(0, num, self.batch_size):
                bound = min(j + self.batch_size, num)
                batch_indices = permut[j:bound]

                cur_inputs = [inputs[i] for i in batch_indices]
                cur_expected = [expected[i] for i in batch_indices]

                self.multi_propagates(cur_inputs, cur_expected, self.learning_rate)
                self.update_weights(self.batch_size)
                self.reset_delta_weights()
            total_err = self.calc_total_err(inputs, expected)
            print(f'Iteration {i+1}: {total_err}')
            if total_err < self.error_threshold:
                return StopReason.CONVERGENCE
        return StopReason.MAX_ITERATIONS


    # def fit(
    #     self, 
    #     inputs: list[list[float]], 
    #     expected: list[list[float]],
    #     learning_rate: float = 0.1,
    #     batch_size: int = 10,
    #     max_iterations: int = 100,
    #     error_threshold: float = 0.1,
    # ):
    #     num = len(inputs)
    #     for i in range(max_iterations):
    #         # pick random batch
    #         batch_indices = random.sample(range(num), batch_size)
    #         batch_inputs = [inputs[i] for i in batch_indices]
    #         batch_expected = [expected[i] for i in batch_indices]

    #         # feed forward
    #         outputs = self(batch_inputs)

    #         # calculate error
    #         errors = []
    #         for j, output in enumerate(outputs):
    #             error = np.array(output) - np.array(batch_expected[j])
    #             errors.append(error)

    #         # backpropagation
    #         for j, layer in enumerate(self.layers[::-1]):
    #             # calculate gradient
    #             gradient = np.array([np.array(error) * np.array(layer.neurons[i].value) for i, error in enumerate(errors)]).T

    #             # calculate delta
    #             delta = np.array([learning_rate * np.array(error) * np.array(layer.neurons[i].value) for i, error in enumerate(errors)]).T

    #             # update weights
    #             layer.neurons = [
    #                 Neuron(
    #                     layer.activation,
    #                     layer.neurons[i].weights - delta[i],
    #                 )
    #                 for i in range(len(layer.neurons))
    #             ]

    #             # calculate error for next layer
    #             if j < len(self.layers) - 1:
    #                 errors = np.array([np.dot(layer.get_weights(), error) for error in errors]).T

    #         # calculate total error
    #         total_error = sum([sum([abs(e) for e in error]) for error in errors])
    #         if total_error < error_threshold:
    #             break

    #         if i % 100 == 0:
    #             print(f'Iteration {i}: {total_error}')


if __name__ == '__main__':
    model = Model()
    model.add(Layer(
        3,
        input_shape=4,
        activation='relu',
        weights=[0.5, 0.5, 1],
        bias=1,
    ))
    model.add(Layer(
        2,
        activation='sigmoid',
        weights=[0.5, 0.5],
        bias=1,
    ))
    model.summary()
