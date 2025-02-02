#!/usr/bin/env python3

# Project: Verb
# Model: add
#
# This script generates the I/O test vector files to be used with the 
# add_tb.vhd testbench.
#
# Generates a coverage report as well to indicate the robust of the test.

import random
from verb import context, coverage, pow2m1
from verb.model import *
from verb.coverage import *

# Define the functional model
class Add:

    def __init__(self, width: int):
        '''
        Create a new design unit model.
        '''
        # parameters
        self.width = width
        # inputs
        self.in0 = Signal(width, distribution=Distribution(space=[0, pow2m1(width), range(1, pow2m1(width))], weights=[0.1, 0.1, 0.8]))
        self.in1 = Signal(width, distribution=Distribution(space=[0, pow2m1(width), range(1, pow2m1(width))], weights=[0.1, 0.1, 0.8]))
        self.cin = Signal()
        # outputs
        self.sum = Signal(width)
        self.cout = Signal()
        pass

    def compute(self):
        '''
        Model the functional behavior of the design unit.
        '''
        temp = Signal(self.width+1)
        temp.assign(int(self.in0) + int(self.in1) + int(self.cin))
        
        # update the output port values
        self.sum.assign(temp[self.width-1::-1])
        self.cout.assign(temp[self.width])
        return self
    
    def force_carry_out(in0: Signal, in1: Signal):
        '''
        Generate a test case when the carry out signal should be triggered.
        '''
        in0 = random.randint(1, in0.max())
        return (in0, in1.max() + 1 - in0)
    
    pass


def cover(add: Add):
    """
    Define coverage areas.
    """

    # Cover the entire range for in0 into at most 16 bins and make sure
    # each bin is tested at least once.
    cg_in0_full = CoverRange("in0 full") \
        .span(add.in0.span()) \
        .goal(1) \
        .max_steps(16) \
        .target(add.in0) \
        .apply()

    # Cover the entire range for in1 into at most 16 bins and make sure 
    # each bin is tested at least once.
    cg_in1_full = CoverRange("in1 full") \
        .span(add.in1.span()) \
        .goal(1) \
        .max_steps(16) \
        .target(add.in1) \
        .apply()

    # Make sure all combinations of input bins are tested at least once. It is possible
    # to define this cross coverage as a CoverRange.
    CoverCross("in0 cross in1") \
        .nets(cg_in0_full, cg_in1_full) \
        .apply()

    # Cover the case that cin is asserted at least 100 times.
    CoverPoint("cin asserted") \
        .goal(100) \
        .target(add.cin) \
        .checker(lambda x: int(x) == 1) \
        .apply()

    # Cover the extreme edge cases for in0 (min and max) at least 10 times.
    CoverGroup("in0 extremes") \
        .goal(10) \
        .target(add.in0) \
        .bins([add.in0.min(), add.in0.max()]) \
        .apply()

    # Cover the extreme edge cases for in1 (min and max) at least 10 times.
    CoverGroup("in1 extremes") \
        .goal(10) \
        .target(add.in1) \
        .bins([add.in1.min(), add.in1.max()]) \
        .apply()

    # Check to make sure both inputs are 0 at the same time at least once.
    CoverPoint("in0 and in1 equal 0") \
        .goal(1) \
        .target(add.in0, add.in1) \
        .advancer(lambda in0, in1: (in0.min(), in1.min())) \
        .checker(lambda in0, in1: int(in0) == 0 and int(in1) == 0) \
        .apply()

    # Check to make sure both inputs are the maximum value at the same time at least once.
    CoverPoint("in0 and in1 equal max") \
        .goal(1) \
        .target(add.in0, add.in1) \
        .advancer(lambda in0, in1: (in0.max(), in1.max())) \
        .checker(lambda in0, in1: int(in0) == in0.max() and int(in1) == in1.max()) \
        .apply()

    # Cover the case that the carry out is generated at least 10 times.
    CoverPoint("cout generated") \
        .goal(10) \
        .source(add.in0, add.in1) \
        .advancer(Add.force_carry_out) \
        .sink(add.cout) \
        .checker(lambda x: int(x) == 1) \
        .apply()


def main():
    add = Add(
        width=context.generic('WORD_SIZE', type=int)
    )

    # enable our coverages for the adder
    cover(add)

    # Run the model!
    with vectors('inputs.txt', 'i') as inputs, vectors('outputs.txt', 'o') as outputs:
        while coverage.met(10_000) == False:
            randomize(add)
            inputs.push(add)

            add.compute()
            outputs.push(add)
            pass
        pass


if __name__ == '__main__':
    main()