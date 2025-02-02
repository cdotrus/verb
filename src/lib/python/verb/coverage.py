# Project: Verb
# Module: coverage
#
# This module handles coverage implementations to track coverage nets: 
# CoverPoints, CoverRanges, CoverGroups, and CoverCrosses.

from abc import ABC as _ABC
from enum import Enum as _Enum


class Status(_Enum):
    PASSED = 0
    SKIPPED = 1
    FAILED = 2

    def to_json(self):
        if self == Status.PASSED:
            return True
        elif self == Status.FAILED:
            return False
        elif self == Status.SKIPPED:
            return None
    pass

class Coverage:
    
    _total_coverages = 0
    _passed_coverages = 0
    _point_count = 0
    _total_points = 0
    _coverage_report = 'coverage.txt'

    @staticmethod
    def get_nets():
        '''
        Returns the list of all coverage nets being tracked.
        '''
        return CoverageNet._group

    @staticmethod
    def get_failing_nets():
        '''
        Returns a list of coverage nets that have not met their coverage goal.

        This function excludes coverage nets that are bypassed.
        '''
        net: CoverageNet
        result = []
        for net in CoverageNet._group:
            # only append nets that are not bypassed and are not completed
            if net.skipped() == False and net.passed() == False:
                result += [net]
            pass
        return result

    @staticmethod
    def report(verbose: bool=True) -> str:
        '''
        Compiles a report of the coverage statistics and details. Setting `verbose`
        to `False` will only provide minimal details to serve as a quick summary.
        '''
        contents = ''
        cov: CoverageNet
        for cov in CoverageNet._group:
            contents += cov.log(verbose) + '\n'
        return contents

    @staticmethod
    def count() -> int:
        '''
        Returns the number of times the Coverage class has called the 'all_passed'
        function. If 'all_passed' is called once every transaction, then it gives
        a sense of how many test cases were required in order to achieve full
        coverage.
        '''
        return CoverageNet._counter
    
    @staticmethod
    def tally_score():
        '''
        Iterates through all CoverageNets to compute the ratio of pass/fail.
        '''
        Coverage._total_coverages = 0
        Coverage._passed_coverages = 0
        Coverage._point_count = 0
        Coverage._total_points = 0
        net: CoverageNet
        for net in CoverageNet._group:
            if net.status() == Status.SKIPPED:
                continue
            Coverage._total_coverages += 1
            Coverage._point_count += net.get_points_met()
            if type(net) == CoverPoint:
                Coverage._total_points += 1
            else:
                Coverage._total_points += net.get_partition_count()
            if net.status() == Status.PASSED:
                Coverage._passed_coverages += 1
            pass

    @staticmethod
    def percent() -> float:
        '''
        Return the percent of all coverages that met their goal. Each covergroup's bin
        is tallied individually instead of tallying the covergroup as a whole.

        Coverages that have a status of `SKIPPED` are not included in the tally.

        Returns `None` if there are no coverages to tally. The percent value is
        from 0.00 to 100.00 percent, with rounding to 2 decimal places.
        '''
        Coverage.tally_score()
        passed = Coverage._point_count
        total = Coverage._total_points
        return round((passed/total) * 100.0, 2) if total > 0 else None

    @staticmethod
    def save() -> str:
        '''
        Saves the report if not already saved, and then returns the absolute path to the file.
        '''
        import os
        from . import context

        path = Coverage._coverage_report
        Coverage.tally_score()
        # write to .json
        Coverage.to_json()
        # write to .txt
        header = 'File: Coverage Report' + '\n'
        header += "Seed: " + str(context.Context.current()._context._seed) + '\n'
        header += "Iterations: " + str(Coverage.count()) + '\n'
        header += "Score: "   + str(Coverage.percent()) + '\n'
        header += "Met: " + ('None' if Coverage._total_points == 0 else str(Coverage._point_count >= Coverage._total_points)) + '\n'
        header += "Count: " + str(Coverage._point_count) + '\n'
        header += "Points: " + str(Coverage._total_points) + '\n'

        with open(path, 'w') as f:
            # header
            f.write(header)
            f.write('\n')  
            # summary
            f.write(Coverage.report(False))
            f.write('\n')  
            # details
            f.write(Coverage.report(True))
            pass
        return os.path.abspath(path)
    
    pass

    @staticmethod
    def get_overall_status() -> Status:
        if Coverage._total_points == 0:
            return Status.SKIPPED
        elif Coverage._point_count >= Coverage._total_points:
            return Status.PASSED
        else:
            return Status.FAILED

    @staticmethod
    def to_json() -> str:
        '''
        Writes the coverage report as a json encoded string.
        '''
        import json
        from . import context

        net: CoverageNet
        report = {
            'seed': context.Context.current()._context._seed,
            'iterations': int(Coverage.count()),
            'score': Coverage.percent(),
            'met': Coverage.get_overall_status().to_json(),
            'count': int(Coverage._point_count),
            'points': int(Coverage._total_points),
            'nets': [net.to_json() for net in CoverageNet._group]
        }

        with open('coverage.json', 'w') as f:
            json.dump(report, f, indent=4)
        pass


def met(timeout: int=-1) -> bool:
    '''
    Checks if each coverage specification has met its goal.

    If a coverage specification is bypassed, it counts as meeting its
    goal. If the timeout is set to -1, it will be disabled and only return
    `True` once all cases are covered.
    '''
    from .context import Context
    if timeout == -1:
        timeout = Context.current()._context._max_test_count
    # force the simulation to pass if enough checks are evaluated
    if timeout > 0 and CoverageNet._counter >= timeout:
        # save the coverage report
        Coverage.save()
        return True        
    # check every cover-node
    cov: CoverageNet
    for cov in CoverageNet._group:
        if cov.skipped() == False and cov.passed() == False:
            # increment the counter
            CoverageNet._counter += 1
            return False
    Coverage.save()
    return True


def summary() -> str:
    '''
    Returns a high-level overview of the most recent coverage trial.
    '''
    return Coverage.report(False)


def report_path() -> str:
    '''
    Returns the coverage report's filesystem path.
    '''
    return Coverage._coverage_report


def report_score() -> str:
    '''
    Formats the score as a `str`.
    '''
    Coverage.tally_score()
    return (str(Coverage.percent()) + ' % ' if Coverage.percent() != None else 'N/A ') + '(' + str(Coverage._point_count) + '/' + str(Coverage._total_points) + ' goals)'


def check(threshold: float=1.0) -> bool:
    '''
    Determines if coverage was met based on meeting or exceeding the threshold value.

    ### Parameters
    - `threshold` expects a floating point value [0, 1.0]
    '''
    Coverage.tally_score()
    passed = Coverage._point_count
    total = Coverage._total_points
    if total <= 0:
        return True
    return float(passed/total) >= threshold


class CoverageNet(_ABC):
    '''
    A CoverageNet is a generic base class for any converage type.
    '''
    from abc import abstractmethod as _abstractmethod
    from .model import Signal, Mode
    from typing import List, Union

    _group = []
    _counter = 0

    @_abstractmethod
    def get_goal(self) -> int:
        '''
        Returns the goal count.
        '''
        pass

    @_abstractmethod
    def get_count(self) -> int:
        '''
        Returns the current count toward the goal.
        '''
        pass

    def get_type(self) -> str:
        if type(self) == CoverCross:
            return 'cross'
        elif type(self) == CoverGroup:
            return 'group'
        elif type(self) == CoverRange:
            return 'range'
        elif type(self) == CoverPoint:
            return 'point'
        else:
            return 'net'

    def to_json(self) -> dict:
        '''
        Formats the coverage net into json-friendly data structure.
        '''
        data = {
            'name': self._name,
            'type': self.get_type(),
            'met': None if self._bypass == True else self.passed()
        }
        data.update(self.to_json_internal())
        return data
    
    @_abstractmethod
    def to_json_internal(self) -> dict:
        '''
        Returns the particular coverage net into json-friendly data structure with
        specifics of that net.
        '''
        pass

    def bypass(self, bypass: bool):
        '''
        Skips this net when trying to meet coverage if `bypass` is true.
        '''
        self._bypass = bypass
        return self
    
    def target(self, *target: Signal):
        '''
        The signal(s) involved in advancing and checking this net's coverage.

        The `target` can be a single Signal or an iterable number of Signals. It
        is considered the `source` and `sink` (both read and written).
        '''
        if len(target) == 1:
            self._target = target[0]
        else:
            self._target = tuple(target)
        return self
    
    def source(self, *source: Signal):
        '''
        The signal(s) involved in advancing the net's coverage.

        The `source` acts as inputs that can be written to when to when trying to advance coverage to a
        scenario that would help approach its goal.
        '''
        if len(source) == 1:
            self._source = source[0]
        else:
            self._source = tuple(source)
        return self
    
    def sink(self, *sink: Signal):
        '''
        The signal(s) involved in checking the net's coverage.

        The `sink` acts as the outputs that are read when checking if this net covered.
        '''
        if len(sink) == 1:
            self._sink = sink[0]
        else:
            self._sink = tuple(sink)
        return self

    def apply(self):
        '''
        Build the coverage net and add it the list of tracking coverages.
        '''
        self._built = True
        self._source = self._target if self._source == None else self._source
        self._sink = self._target if self._sink == None else self._sink
        CoverageNet._group += [self]
        return self

    def __init__(self, name: str):
        '''
        Create a new CoverageNet object.

        To finish building this object and allow its coverage to be tracked, use
        the `.apply()` function.
        '''
        self._name = name
        self._built = False
        self._bypass = False
        self._target = None
        self._source = None
        self._sink = None
        pass

    def has_sink(self) -> bool:
        '''
        Checks if the net is configured with a set of signal(s) to read from
        to check coverage.
        '''
        return self._sink != None
    
    def has_source(self) -> bool:
        '''
        Checks if the net is configured with a set of signal(s) to write to
        to advance coverage.
        '''
        return self._source != None

    def get_sink_list(self):
        '''
        Returns an iterable object of the signals to be read for checking coverage.
        '''
        from .model import Signal 

        if hasattr(self, '_sink_list') == True:
            return self._sink_list
        
        self._sink_list = []
        if self.has_sink() == True:
            # transform single signal into a list
            if type(self._sink) == Signal:
                self._sink_list = [self._sink]
            else:
                self._sink_list = list(self._sink)
            pass

        return self._sink_list

    def get_source_list(self):
        '''
        Returns an iterable object of the signals to be written for advancing coverage.
        '''
        from .model import Signal 

        if hasattr(self, '_source_list') == True:
            return self._source_list
        
        self._source_list = []
        if self.has_source() == True:
            # transform single signal into a list
            if type(self._source) == Signal:
                self._source_list = [self._source]
            else:
                self._source_list = list(self._source)
            pass
        return self._source_list

    def get_sink(self):
        '''
        Returns the object that has reading permissions to check coverage.
        '''
        return self._sink

    def get_source(self):
        '''
        Returns the object that has writing permissions to advance coverage.
        '''
        return self._source

    @_abstractmethod
    def get_range(self) -> range:
        '''
        Returns a range object of the sample space and the size of each partitioning.
        '''
        pass
    
    @_abstractmethod
    def get_partition_count(self) -> int:
        '''
        Returns the number of unique partitions required to cover the entire sample space.
        '''
        pass

    @_abstractmethod
    def get_total_goal_count(self) -> int:
        '''
        Returns the number of total goals that must be reached by this net.
        '''
        pass

    @_abstractmethod
    def get_total_points_met(self) -> int:
        '''
        Returns the number of total points collected by this net.
        '''
        pass

    @_abstractmethod
    def is_in_sample_space(self, item) -> bool:
        '''
        Checks if the `item` is in the defined sample space.
        '''
        pass
    
    @_abstractmethod
    def _map_onto_range(self, item) -> int:
        '''
        Converts the `item` into a valid number within the defined range of possible values.
        
        If there is no possible mapping, return None.
        '''
        pass

    @_abstractmethod
    def check(self, item) -> bool:
        '''
        This function accepts either a single object or an interable object that is
        required to read to see if coverage proceeds toward its goal.

        It can be thought of as the inverse function to `advance(...)`.
        '''
        pass

    @_abstractmethod
    def advance(self, rand=False):
        '''
        This function returns either a single object or an iterable object that is
        required to be written to make the coverage proceed toward its goal.

        It can be thought of as the inverse function to `check(...)`.
        '''
        pass

    @_abstractmethod
    def get_points_met(self) -> int:
        '''
        Returns the number of points that have met their goal.
        '''
        pass

    @_abstractmethod
    def passed(self) -> bool:
        '''
        Returns `True` if the coverage met its goal.
        '''
        pass

    def log(self, verbose: bool=True) -> str:
        '''
        Convert the coverage into a string for user logging purposes. Setting `verbose` to `True`
        will provide more details in the string contents.
        '''
        label = 'CoverPoint' 
        if issubclass(type(self), CoverGroup):
            label = 'CoverGroup'
        elif issubclass(type(self), CoverRange):
            label = 'CoverRange'
        elif issubclass(type(self), CoverCross):
            label = 'CoverCross'
        elif issubclass(type(self), CoverPoint):
            label = 'CoverPoint'
        else:
            raise Exception("Unsupported CoverageNet "+str(type(self)))
        if verbose == False:
            return label + ": " + self._name + ': ' + self.to_string(verbose) + ' ...'+str(self.status().name)
        else:
            return label + ": " + self._name + ':' + ' ...'+str(self.status().name) + '\n    ' + self.to_string(verbose)

    def skipped(self) -> bool:
        '''
        Checks if this coverage is allowed to be bypassed during simulation due
        to an external factor making it impossible to pass.
        '''
        return self._bypass 

    def status(self) -> Status:
        '''
        Determine the status of the Coverage node.
        '''
        if self.skipped() == True:
            return Status.SKIPPED
        elif self.passed() == True:
            return Status.PASSED
        else:
            return Status.FAILED  

    @_abstractmethod
    def to_string(self, verbose: bool) -> str:
        '''
        Converts the coverage into a string for readibility to the end-user.
        '''
        pass
        
    pass


class CoverPoint(CoverageNet):
    '''
    CoverPoints are designed to track when a single particular event occurs.
    '''
    from .model import Signal

    def to_json_internal(self) -> dict:
        data = {
            'count': int(self.get_total_points_met()),
            'goal': int(self.get_total_goal_count()),
        }
        return data

    def get_total_goal_count(self) -> int:
        return self._goal

    def goal(self, goal: int):
        '''
        Sets the coverage goal for this net.
        '''
        self._goal = goal
        return self
    
    def advancer(self, fn): 
        '''
        Set the function or lambda expression that provides the implementation for how to write the values to the source
        to advance this net's coverage closer to its goal.
        '''
        self._fn_advance = fn
        return self
    
    def checker(self, fn):
        '''
        Sets the function or lambda expression that provides the implementation for how to read the values from the sink
        to check this net's coverage.
        '''
        self._fn_cover = fn
        return self

    def __init__(self, name: str):
        '''
        Create a new CoverPoint object.

        To finish building this object and allow its coverage to be tracked, use
        the `.apply()` function.
        '''
        self._count = 0
        self._goal = 1
        # define a custom function that should return a boolean to define the targeted point
        self._fn_cover = None
        self._fn_advance = None

        super().__init__(name=name)
        pass

    def _transform(self, item):
        # unpack the list if one was given
        if self._fn_cover == None:
            return item
        if isinstance(item, (list, tuple)) == True:
            return self._fn_cover(*item)
        else:
            return self._fn_cover(item)

    def is_in_sample_space(self, item) -> bool:
        mapped_item = int(self._transform(item))
        return mapped_item >= 0 and mapped_item < 2

    def _map_onto_range(self, item) -> int:
        if self.is_in_sample_space(item) == False:
            return None
        return int(self._transform(item))

    def get_goal(self) -> int:
        return self._goal

    def get_count(self) -> int:
        return self._count

    def get_range(self) -> range:
        return range(0, 2, 1)
    
    def get_partition_count(self) -> int:
        return 2
    
    def get_points_met(self) -> int:
        '''
        Returns the number of points that have met their goal.
        '''
        return 1 if self._count >= self._goal else 0
    
    def get_total_points_met(self) -> int:
        return self._count

    def check(self, item):
        '''
        Returns `True` if the `cond` was satisfied and updates the internal count
        as the coverpoint tries to met or exceed its goal.
        '''
        if self.is_in_sample_space(item) == False:
            return False
        cond = bool(self._map_onto_range(item))
        if cond == True:
            self._count += 1
        return cond
    
    def advance(self, rand=False):
        if self._fn_advance == None:
            return int(True)
        else:
            if isinstance(self._source, (list, tuple)) == True:
                return self._fn_advance(*self._source)
            else:
                return self._fn_advance(self._source)

    def passed(self):
        return self._count >= self._goal

    def to_string(self, verbose: bool):
        return str(self._count) + '/' + str(self._goal)
    
    pass


class CoverGroup(CoverageNet):
    from typing import List as _List
    from .model import Signal

    def to_json_internal(self) -> dict:
        bins_reached = 0
        # compute the number of bins that reached their goal
        for c in self._macro_bins_count:
            if c >= self._goal:
                bins_reached += 1
            pass
        data = {
            'count': self.get_points_met(),
            'goal': len(self._macro_bins_count),
        }

        bins = []
        for i, macro in enumerate(self._macro_bins):
            cur_bin = {
                'name': self._macro_to_string(i),
                'met': None if self._bypass == True else int(self._macro_bins_count[i]) >= int(self._goal),
                'count': int(self._macro_bins_count[i]),
                'goal': int(self._goal),
            }
            hits = []
            for hit in macro:
                if hit in self._item_counts.keys():
                    hit = {
                        'value': str(hit),
                        'count': int(self._item_counts[hit])
                    }
                    hits += [hit]
                pass
            cur_bin['hits'] = hits
            bins += [cur_bin]
            pass

        data['bins'] = bins
        return data

    def get_total_goal_count(self) -> int:
        return self._goal * len(self._macro_bins_count)

    def goal(self, goal: int):
        '''
        Sets the coverage goal for this net.
        '''
        self._goal = goal
        return self

    def advancer(self, fn): 
        '''
        Set the function or lambda expression that provides the implementation for how to write the values to the source
        to advance this net's coverage closer to its goal.
        '''
        self._fn_advance = fn
        return self
    
    def checker(self, fn):
        '''
        Sets the function or lambda expression that provides the implementation for how to read the values from the sink
        to check this net's coverage.
        '''
        self._fn_cover = fn
        return self
    
    def max_bins(self, limit: int):
        '''
        Sets the maximum number of bins.
        '''
        self._max_bins = limit
        return self
    
    def bins(self, bins):
        '''
        Defines the explicit grouping of bins.
        '''
        self._bins = bins
        return self
    
    def apply(self):
        # will need to provide a division operation step before inserting into
        if len(self._bins) > self._max_bins:
            self._items_per_bin = int(len(self._bins) / self._max_bins)
        else:
            self._items_per_bin = 1

        # initialize the bins
        for i, item in enumerate(set(self._bins)):
            # items are already in their 'true' from from given input
            self._bins_lookup[int(item)] = i
            # group the items together based on a common index that divides them into groups
            i_macro = int(i / self._items_per_bin)
            if len(self._macro_bins) <= i_macro:
                self._macro_bins.append([])
                self._macro_bins_count.append(0)
                pass
            self._macro_bins[i_macro] += [int(item)]
            pass
        return super().apply()

    def __init__(self, name: str):
        '''
        Create a new CoverGroup object.

        To finish building this object and allow its coverage to be tracked, use
        the `.apply()` function.
        '''
        # stores the items per index for each bin group
        self._macro_bins = []
        # stores the count for each bin
        self._macro_bins_count = []
        # store a hash to the index in the set of bins list
        self._bins_lookup = dict()

        # store the counts of individual items
        self._item_counts = dict()

        # defining a bin range is more flexible for defining a large space

        # store the actual values when mapped items cover toward the goal
        self._mapped_items = dict()
        self._max_bins = 64
        self._goal = 1

        # initialize the total count of all covers
        self._total_count = 0

        # store the function to map items into the coverage space
        self._fn_cover = None
        # store the function to generate the proper values to advance coverage
        self._fn_advance = None

        super().__init__(name=name)
        pass

    def get_goal(self) -> int:
        return self._goal * len(self._macro_bins_count)

    def get_count(self) -> int:
        points_met = 0
        for count in self._macro_bins_count:
            if count >= self._goal:
                points_met += 1
        return points_met

    def _transform(self, item):
        return int(item if self._fn_cover == None else self._fn_cover(item))

    def is_in_sample_space(self, item) -> bool:
        return self._bins_lookup.get(self._transform(item)) != None
    
    def _map_onto_range(self, item) -> int:
        if self.is_in_sample_space(item) == False:
            return None
        return int(self._bins_lookup[self._transform(item)])

    def get_range(self) -> range:
        return range(0, len(self._bins_lookup.keys()), self._items_per_bin)
    
    def get_partition_count(self) -> int:
        # the real number of partitions of the sample space
        return len(self._macro_bins)
    
    def _get_macro_bin_index(self, item) -> int:
        '''
        Returns the macro index for the `item` according to the bin division.
        '''
        return int(self._bins_lookup[item] / self._items_per_bin)
    
    def check(self, item):
        '''
        Return's true if it got the entire group closer to meeting coverage.

        This means that the item covered is under the goal.
        '''
        if self.is_in_sample_space(item) == False:
            return False
        # use special mapping function if defined
        mapped_item = self._transform(item)
        # got the item, but check its relative items under the same goal
        i_macro = self._get_macro_bin_index(mapped_item)
        # make the item exists as a possible entry and its macro goal is not met
        is_progress = self._macro_bins_count[i_macro] < self._goal
        # update the map with the value
        self._macro_bins_count[i_macro] += 1
        # update the total count
        self._total_count += 1
        # record the actual value that initiated this coverage
        if self._fn_cover != None:
            if i_macro not in self._mapped_items.keys():
                self._mapped_items[i_macro] = dict()
            if mapped_item not in self._mapped_items[i_macro].keys():
                self._mapped_items[i_macro][mapped_item] = 0 
            # increment the count of this item being detected
            self._mapped_items[i_macro][mapped_item] += 1
            pass
        # track individual count for this item
        if mapped_item not in self._item_counts.keys():
            self._item_counts[mapped_item] = 0
        self._item_counts[mapped_item] += 1

        return is_progress
    
    def get_total_points_met(self) -> int:
        points_met = 0
        for count in self._macro_bins_count:
            points_met += count
        return points_met
    
    def get_points_met(self) -> int:
        points_met = 0
        for count in self._macro_bins_count:
            if count >= self._goal:
                points_met += 1
        return points_met
    
    def advance(self, rand=False):
        '''
        Returns the next item currently not meeting the coverage goal.

        Enabling `rand` will allow for a random item to be picked, rather than
        sequentially.

        Returns `None` if no item is left (all goals are reached and coverage is
        passing).
        '''
        import random as _random

        # can only map 1-way (as of now)
        if self._fn_cover != None and self._fn_advance == None:
            raise Exception("Cannot map back to original values")

        if self._fn_advance != None:
            raise Exception("Implement inverse mapping")
        
        available = []
        # filter out the elements who have not yet met the goal
        for i, count in enumerate(self._macro_bins_count):
            if count < self._goal:
                available += [i]
            pass
        if len(available) == 0:
            return None
        if rand == True:
            # pick a random macro bin
            i_macro = _random.choice(available)
            # select a random item from the bin
            return _random.choice(self._macro_bins[i_macro])

        # provide 1st available if random is disabled
        i_macro = available[0]
        return self._macro_bins[i_macro][0]

    def passed(self) -> bool:
        '''
        Checks if each bin within the `CoverGroup` has met or exceeded its goal. 
        If any of the bins has not, then whole function fails and returns `False`.
        '''
        for val in self._macro_bins_count:
            # fail on first failure
            if val < self._goal:
                return False
        return True
    
    def _macro_to_string(self, i) -> str:
        '''
        Write a macro_bin as a string.
        '''
        LIMITER = 7
        items = self._macro_bins[i]
        result = '['
        for i in range(0, 8):
            if i >= len(items):
                break
            result += str(items[i])
            if i < len(items)-1:
                result += ', '
            if i >= LIMITER:
                result += '...'
                break
            pass
        result += ']'
        return result

    def to_string(self, verbose: bool=False) -> str:
        from .primitives import _find_longest_str_len
        result = ''
        # print each individual bin and its goal status
        if verbose == True:
            # determine the string formatting by identifying longest string
            longest_len = _find_longest_str_len([self._macro_to_string(i) for i, _ in enumerate(self._macro_bins)])
            is_first = True
            # print the coverage analysis
            for i, _ in enumerate(self._macro_bins):
                if is_first == False:
                    result += '\n    '
                phrase = str(self._macro_to_string(i))
                count = self._macro_bins_count[i]
                result += str(phrase) + ': ' + (' ' * (longest_len - len(str(phrase)))) + str(count) + '/' + str(self._goal)
                # enumerate on all mapped values that were detected for this bin
                if self._fn_cover != None and i in self._mapped_items.keys() and self.get_range().step > 1:
                    # determine the string formatting by identifying longest string
                    sub_longest_len = _find_longest_str_len(self._mapped_items[i].keys())
                    seq = [(key, val) for key, val in self._mapped_items[i].items()]
                    seq.sort()
                    for j, (key, val) in enumerate(seq):
                        result += '\n        '
                        result += str(key) + ': ' + (' ' * (sub_longest_len - len(str(key)))) + str(val)

                        pass
                is_first = False
        # print the number of bins that reached their goal
        else:
            bins_reached = 0
            for count in self._macro_bins_count:
                if count >= self._goal:
                    bins_reached += 1
                pass
            result += str(bins_reached) + '/' + str(len(self._macro_bins_count))
        return result
    pass


class CoverRange(CoverageNet):
    '''
    CoverRanges are designed to track a span of integer numbers, which can divided up among steps.
    This structure is similar to a CoverGroup, however, the bins defined in a CoverRange are implicitly defined
    along the set of integers.
    '''
    from .model import Signal

    def to_json_internal(self) -> dict:
        data = {
            'count': int(self.get_points_met()),
            'goal': int(self.get_total_goal_count()),
        }

        bins = []

        # print the coverage analysis
        for i, _ in enumerate(self._table):
            # collect a single bin
            if self._step_size > 1:
                step = str(i * self._step_size) + '..=' + str(((i+1) * self._step_size)-1)
            else:
                step = i
                pass
            count = int(self._table_counts[i])

            cur_bin = {
                'name': str(step),
                'met': None if self._bypass == True else count >= self._goal,
                'count': int(count),
                'goal': int(self._goal),
            }
            # get each hit that helped toward the current bin's goal
            hits = []
            if self._step_size > 1 and i in self._mapped_items.keys():
                seq = [(key, val) for key, val in self._mapped_items[i].items()]
                seq.sort()
                for (key, val) in seq:
                    cur_hit = {
                        'value': str(key),
                        'count': int(val)
                    }
                    hits += [cur_hit]
                    pass
            # update the current bin's account for its hits
            cur_bin['hits'] = hits
            # add to the bin list
            bins += [cur_bin]
            pass

        data['bins'] = bins
        return data

    def get_total_goal_count(self) -> int:
        return self._goal * int(len(self._table_counts))

    def goal(self, goal: int):
        '''
        Sets the coverage goal for this net.
        '''
        self._goal = goal
        return self

    def advancer(self, fn): 
        '''
        Set the function or lambda expression that provides the implementation for how to write the values to the source
        to advance this net's coverage closer to its goal.
        '''
        self._fn_advance = fn
        return self
    
    def checker(self, fn):
        '''
        Sets the function or lambda expression that provides the implementation for how to read the values from the sink
        to check this net's coverage.
        '''
        self._fn_cover = fn
        return self
    
    def span(self, span: range):
        '''
        Specify the range of values to cover.
        '''
        self._domain = span
        return self

    def max_steps(self, limit: int):
        '''
        Specify the maximum number of steps to cover the entire range.
        '''
        self._max_steps = limit
        return self
    
    def apply(self):
        import math, sys
        # domain = range
        # determine the step size
        self._step_size = self._domain.step
        num_steps_needed = int(abs(self._domain.stop - self._domain.start) / self._domain.step)
        self._step_size = self._domain.step
        # limit by computing a new step size
        # self._step_size = self._domain.step
        self._num_of_steps = num_steps_needed

        if self._max_steps != None and num_steps_needed > self._max_steps:
            # update instance attributes
            self._step_size = int(math.ceil(abs(self._domain.stop - self._domain.start) / self._max_steps))
            self._num_of_steps = self._max_steps
            pass

        self._table = [[]] * self._num_of_steps

        self._table_counts = [0] * self._num_of_steps
        # print('len', len(self._table_counts))
        # print(self._step_size)
        self._start = self._domain.start
        self._stop = self._domain.stop
        return super().apply()

    def __init__(self, name: str):
        '''
        Create a new CoverRange object.

        To finish building this object and allow its coverage to be tracked, use
        the `.apply()` function.
        '''

        self._domain = None
        self._goal = 1
        self._max_steps = 64
   
        # store a potential custom mapping function
        self._fn_advance = None
        self._fn_cover = None
        
        # initialize the total count of all covers
        self._total_count = 0

        # store the actual values when mapped items cover toward the goal
        self._mapped_items = dict()

        super().__init__(name)
        pass

    def get_goal(self) -> int:
        return self._goal * len(self._table_counts)

    def get_count(self) -> int:
        points_met = 0
        for entry in self._table_counts:
            if entry >= self._goal:
                points_met += 1
        return points_met

    def get_range(self) -> range:
        return range(self._start, self._stop, self._step_size)
    
    def get_partition_count(self) -> int:
        return self._num_of_steps
    
    def get_points_met(self) -> int:
        points_met = 0
        for entry in self._table_counts:
            if entry >= self._goal:
                points_met += 1
        return points_met

    def get_total_points_met(self) -> int:
        points_met = 0
        for entry in self._table_counts:
            points_met += entry
        return points_met
    
    def passed(self) -> bool:
        '''
        Checks if each bin within the `CoverGroup` has met or exceeded its goal. 
        If any of the bins has not, then whole function fails and returns `False`.
        '''
        for entry in self._table_counts:
            # exit early on first failure for not meeting coverage goal
            if entry < self._goal:
                return False
        return True

    def _transform(self, item):
        return int(item) if self._fn_cover == None else int(self._fn_cover(item))

    def is_in_sample_space(self, item) -> bool:
        mapped_item = self._transform(item)
        return mapped_item >= self._start and mapped_item < self._stop

    def _map_onto_range(self, item) -> int:
        if self.is_in_sample_space(item) == False:
            return None
        return self._transform(item)

    def check(self, item) -> bool:
        '''
        Return's true if it got the entire group closer to meeting coverage.

        This means that the item covered is under the goal.
        '''
        # print(item)
        # print(self._stop)
        if self.is_in_sample_space(item) == False:
            return False
        # convert item to int
        mapped_item = self._transform(item)
        # print('mapped', mapped_item)
        # print(self._step_size)
        # transform into coverage domain
        index = int(mapped_item / self._step_size)
        # print('index', index, mapped_item/self._step_size)
        # caution: use this line when trying to handle very big ints that were mapped (fp inprecision?)
        if index >= len(self._table_counts):
            return False
        # check if it improves progessing by adding to a mapping that has not met the goal yet
        is_progress = self._table_counts[index] < self._goal
        # update the coverage for this value
        self._table[index] += [mapped_item]
        self._table_counts[index] += 1
        self._total_count += 1
        # track original items that count toward their space of the domain
        if index not in self._mapped_items.keys():
            self._mapped_items[index] = dict()
        # store the count of the integer value of the number for encounters tracking/stats
        if mapped_item not in self._mapped_items[index].keys():
            self._mapped_items[index][mapped_item] = 0 
        # increment the count of this item being detected
        self._mapped_items[index][mapped_item] += 1
        return is_progress
    
    def advance(self, rand: bool=False):
        '''
        Returns the next item currently not meeting the coverage goal.

        Enabling `rand` will allow for a random item to be picked, rather than
        sequentially.

        Returns `None` if no item is left (all goals are reached and coverage is
        passing).
        '''
        import random as _random

        # can only map 1-way (as of now)
        if self._fn_cover != None and self._fn_advance == None:
            raise Exception("Cannot map back to original values")

        if self._fn_advance != None:
            raise Exception("Implement")
        
        available = []
        # filter out the elements who have not yet met the goal
        for i, count in enumerate(self._table_counts):
            if count < self._goal:
                available += [i]
            pass
        if len(available) == 0:
            return None

        if rand == True:
            j = _random.choice(available)
            # transform back to the selection of the expanded domain space
            return _random.randint(j * self._step_size, ((j+1) * self._step_size) - 1)
        # provide 1st available if random is disabled
        j = available[0]
        return _random.randint(j * self._step_size, ((j+1) * self._step_size) - 1)
    
    def to_string(self, verbose: bool) -> str:
        from .primitives import _find_longest_str_len
        result = ''
        # print each individual bin and its goal status
        if verbose == True:
            # determine the string formatting by identifying longest string
            if self._step_size > 1:
                longest_len = len(str((len(self._table)-2) * self._step_size) + '..=' + str((len(self._table)-1) * self._step_size))
            else:
                longest_len = len(str(self._stop-1))
            is_first = True
            # print the coverage analysis
            for i, _ in enumerate(self._table):
                if is_first == False:
                    result += '\n    '
                if self._step_size > 1:
                    step = str(i * self._step_size) + '..=' + str(((i+1) * self._step_size)-1)
                else:
                    step = i
                count = self._table_counts[i]
                result += str(step) + ': ' + (' ' * (longest_len - len(str(step)))) + str(count) + '/' + str(self._goal)
                # determine the string formatting by identifying longest string
                if self._step_size > 1 and i in self._mapped_items.keys():
                    sub_longest_len = _find_longest_str_len(self._mapped_items[i].keys())
                    seq = [(key, val) for key, val in self._mapped_items[i].items()]
                    seq.sort()
                    for i, (key, val) in enumerate(seq):
                        result += '\n        '
                        result += str(key) + ': ' + (' ' * (sub_longest_len - len(str(key)))) + str(val)
                        pass
                is_first = False
            pass
        # print the number of bins that reached their goal
        else:
            goals_reached = 0
            for count in self._table_counts:
                if count >= self._goal:
                    goals_reached += 1
                pass
            result += str(goals_reached) + '/' + str(len(self._table_counts))
        return result


class CoverCross(CoverageNet):
    '''
    CoverCrosses are designed to track cross products between two or more coverage nets.

    Internally, a CoverCross stores a CoverRange for the 1-dimensional flatten version of
    the N-dimensional cross product across the different coverage nets.
    '''
    from typing import List as List

    def to_json_internal(self) -> dict:
        data = self._inner.to_json_internal()
        return data

    def get_total_goal_count(self) -> int:
        return self._inner.get_total_goal_count()

    def nets(self, *net: CoverageNet):
        '''
        Specifies the coverage nets to cross.
        '''
        self._nets = list(net)[::-1]
        return self
    
    def goal(self, goal: int):
        self._goal = goal
        return self

    def max_steps(self, limit: int=64):
        '''
        Specify the maximum number of steps to cover the entire range.
        '''
        self._max_steps = limit
        return self

    def apply(self):
        self._crosses = len(self._nets)
        
        combinations = 1
        for n in self._nets:
            combinations *= n.get_partition_count()
            pass

        self._inner = CoverRange(self._name) \
            .span(range(combinations)) \
            .goal(self._goal) \
            .bypass(self._bypass) \
            .max_steps(self._max_steps) \
            .apply()

        sink = []
        net: CoverageNet
        for net in self._nets:
            # cannot auto-check coverage if a sink is not defined
            if net.has_sink() == False:
                sink = None
                break
            sink += [net.get_sink()]
            pass

        source = []
        for net in self._nets:
            # cannot auto-advance coverage if a source is not defined
            if net.has_source() == False:
                source = None
                break
            source += [net.get_source()]
            pass
        # remove the interior range net and only track this outer net
        CoverageNet._group.pop()

        self._source = source
        self._sink = sink
        return super().apply()

    def __init__(self, name: str):
        '''
        Create a new CoverCross object.

        To finish building this object and allow its coverage to be tracked, use
        the `.apply()` function.
        '''
        self._nets = []
        self._goal = 1
        self._max_steps = 64
        self._crosses = 0
        # overwrite the entry with this instance in the class-wide data structure
        super().__init__(name=name)
        pass
    
    def get_sink_list(self):
        if hasattr(self, "_sink_list") == True:
            return self._sink_list
        
        self._sink_list = []
        net: CoverageNet
        for net in self._nets:
            self._sink_list += net.get_sink_list()
        return self._sink_list

    def get_source_list(self):
        if hasattr(self, "_source_list") == True:
            return self._source_list
        
        self._source_list = []
        net: CoverageNet
        for net in self._nets:
            self._source_list += net.get_source_list()

        return self._source_list

    def advance(self, rand=False):
        index = self._inner.advance(rand)
        # convert the 1-dimensional value into its n-dimensional value
        item = self._pack(index)
        # print(index, '->', item)
        # print('----', self._inner.get_partition_count())

        j = self._flatten(item)
        # print(item, '->', j)

        n = self.get_cross_count()

        final = []
        # expand to the entire parition space for each element
        for i, net in enumerate(self._nets):
            # print(net.advance(rand))
            # print(net, net.get_range().step)
            # print(self._nets[n-i-1].get_range().step)
            final += [item[i] * self._nets[n-i-1].get_range().step]

        # print(index, '-->', item, final)
        # exit('implement!')
        return final[::-1]

    def get_range(self) -> range:
        return self._inner.get_range()
    
    def get_partition_count(self) -> int:
        return self._inner.get_partition_count()

    def is_in_sample_space(self, item) -> bool:
        for i, x in enumerate(item):
            if self._nets[i].is_in_sample_space(x) == False:
                return False
        return True
    
    def get_cross_count(self) -> int:
        '''
        Returns the number of elements are involved in the cartesian cross product.
        '''
        return self._crosses
    
    def _pack(self, index):
        '''
        Packs a 1-dimensional index into a N-dimensional item.
        '''
        # print('to3D!')
        # initialize the set of values to store in the item
        item = [0] * self.get_cross_count()

        subgroup_sizes = [1] * self.get_cross_count()
        # print(subgroup_sizes)
        for i in range(self.get_cross_count()):
            subgroup_sizes[i] = self._nets[i].get_partition_count()
            # for j in range(i+1, self.get_cross_count()):
            #     subgroup_sizes[i] *= self._nets[i].get_partition_count()
        #     pass
        # print(index)
        subgroup_sizes = subgroup_sizes[::-1]
        #  print('sub', subgroup_sizes)
        # perform counting sequence and perform propery overflow/handling of the carry
        for i in range(0, index):
            item[0] += 1
            carry = True
            if item[0] >= subgroup_sizes[0]:
                item[0] = 0
            else:
                carry = False
            j = 1
            while carry == True and j < self.get_cross_count():
                item[j] += 1
                if item[j] >= subgroup_sizes[j]:
                    item[j] = 0
                else:
                    carry = False
                j += 1
                pass

        return item

    def _flatten(self, item):
        '''
        Flattens an N-dimensional item into a 1-dimensional index.

        Reference: 
        - https://stackoverflow.com/questions/7367770/how-to-flatten-or-index-3d-array-in-1d-array
        '''
        # print('to 1d!')
        if len(item) != self.get_cross_count():
            raise Exception("Expects "+str(self._crosses)+" values in pair")
        index = 0
        #  print('3d:', item)
        # dimensions go: x, y, z... so reverse the tuple/list
        weights = [1]
        n = self.get_cross_count()
        for i, d in enumerate(item):
            index += int(d) * weights[-1]
            weights += [weights[-1] * self._nets[n-i-1].get_partition_count()]
            pass
        # print(weights)
        # print('NOW:', index)
        return index

    def _map_onto_range(self, item):
        return self._flatten(item)
    
    def get_points_met(self) -> int:
        '''
        Returns the number of points that have met their goal.
        '''
        return self._inner.get_points_met()

    def get_goal(self) -> int:
        return self._inner.get_goal()

    def get_count(self) -> int:
        return self._inner.get_count()
    
    def get_total_points_met(self) -> int:
        return self._inner.get_total_points_met()

    def check(self, item):
        if self.is_in_sample_space(item) == False:
            return None
        rev = []
        for i, it in enumerate(item):
            rev += [int(int(it) / self._nets[i].get_range().step)]
        rev = rev[::-1]
        # divide by the steps
        index = self._flatten(rev)
        return self._inner.check(index)

    def passed(self):
        return self._inner.passed()
    
    def to_string(self, verbose: bool):
        return self._inner.to_string(verbose)

    pass
