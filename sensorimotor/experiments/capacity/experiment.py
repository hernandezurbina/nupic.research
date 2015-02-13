#!/usr/bin/env python
# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2014, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------
"""
This program tests the memorization capacity of L4+L3.

The independent variables (that we change) are:
    - # of distinct worlds (images)
    - # of unique elements (fixation points)

The dependent variables (that we monitor) are:
    - temporal pooler stability
    - temporal pooler distinctness

Each world will be composed of unique elements that are not shared between
worlds, to test the raw memorization capacity without generalization.

The output of this program is a data sheet (CSV) showing the relationship
between these variables.

Experiment setup and validation are specified here:
https://github.com/numenta/nupic.research/wiki/Capacity-experiment:-setup-and-validation
"""

import csv
import os
import sys
import time

from nupic.research.monitor_mixin.monitor_mixin_base import MonitorMixinBase


from sensorimotor.one_d_world import OneDWorld
from sensorimotor.one_d_universe import OneDUniverse
from sensorimotor.random_one_d_agent import RandomOneDAgent
from sensorimotor.exhaustive_one_d_agent import ExhaustiveOneDAgent

from sensorimotor.sensorimotor_experiment_runner import (
  SensorimotorExperimentRunner
)



# Constants
N = 128 #512
W = 5 #20
DEFAULTS = {
  "n": N,
  "w": W,
  "tmParams": {
    "columnDimensions": [N],
    "minThreshold": W * 2,
    "activationThreshold": W * 2,
    "maxNewSynapseCount": W * 2
  },
  "tpParams": {
    "columnDimensions": [N],
    "numActiveColumnsPerInhArea": W,
    "potentialPct": 0.9,
    "initConnectedPct": 0.5,

    # Ryan's additions
    "synPermActiveInc": 0.001,
    "synPermInactiveDec": 0.00,
    "synPredictedInc": 0.5,
    "synPermConnected": 0.3,
    "poolingLife": 1000,
    "poolingThreshUnpredicted": 0.0,
    "spVerbosity": 0
  }
}
VERBOSITY = 0
PLOT = 1
SHOW_PROGRESS_INTERVAL = 200
TM_TRAINING_SWEEPS = 2
TP_TRAINING_SWEEPS = 1
IS_ONLINE_LEARNING = True
DEF_ONLINE_REPS = 2

def trainTwoPass(runner, exhaustiveAgents, completeSequenceLength):
  print "Training temporal memory..."
  sequences = runner.generateSequences(completeSequenceLength *
                                       TM_TRAINING_SWEEPS,
                                       exhaustiveAgents,
                                       verbosity=VERBOSITY)
  runner.feedLayers(sequences, tmLearn=True, tpLearn=False,
                    verbosity=VERBOSITY,
                    showProgressInterval=SHOW_PROGRESS_INTERVAL)
  print
  print MonitorMixinBase.mmPrettyPrintMetrics(runner.tp.mmGetDefaultMetrics() +
                                              runner.tm.mmGetDefaultMetrics())
  print
  print "Training temporal pooler..."
  sequences = runner.generateSequences(completeSequenceLength *
                                       TP_TRAINING_SWEEPS,
                                       exhaustiveAgents,
                                       verbosity=VERBOSITY)
  runner.feedLayers(sequences, tmLearn=False, tpLearn=True,
                    verbosity=VERBOSITY,
                    showProgressInterval=SHOW_PROGRESS_INTERVAL)
  print
  print MonitorMixinBase.mmPrettyPrintMetrics(runner.tp.mmGetDefaultMetrics() +
                                              runner.tm.mmGetDefaultMetrics())
  print



def trainOnline(runner, exhaustiveAgents, completeSequenceLength, reps):
  print "Training temporal memory and temporal pooler..."
  sequences = runner.generateSequences(completeSequenceLength *
                                       reps,
                                       exhaustiveAgents,
                                       verbosity=VERBOSITY)
  runner.feedLayers(sequences, tmLearn=True, tpLearn=True,
                    verbosity=VERBOSITY,
                    showProgressInterval=SHOW_PROGRESS_INTERVAL)
  print
  print MonitorMixinBase.mmPrettyPrintMetrics(runner.tp.mmGetDefaultMetrics() +
                                              runner.tm.mmGetDefaultMetrics())
  print



def run(numWorlds, numElements, outputDir, params=DEFAULTS,
        isOnline=IS_ONLINE_LEARNING, onlineTrainingReps=DEF_ONLINE_REPS):
  # Extract params
  n = params["n"]
  w = params["w"]
  tmParams = params["tmParams"]
  tpParams = params["tpParams"]

  if "isOnline" in params:
    isOnline = params["isOnline"]
    onlineTrainingReps = params["onlineTrainingReps"]

  # Initialize output
  if not os.path.exists(outputDir):
    os.makedirs(outputDir)

  csvFilePath = os.path.join(outputDir, "{0}x{1}.csv".format(numWorlds,
                                                             numElements))

  # Initialize experiment
  start = time.time()
  universe = OneDUniverse(nSensor=n, wSensor=w,
                          nMotor=n, wMotor=w)

  # Run the experiment
  with open(csvFilePath, 'wb') as csvFile:
    csvWriter = csv.writer(csvFile)

    print ("Experiment parameters: "
           "(# worlds = {0}, # elements = {1}, n = {2}, w = {3}, "
           "online = {4}, onlineReps = {5})".format(
      numWorlds, numElements, n, w, isOnline, onlineTrainingReps))
    print "Temporal memory parameters: {0}".format(tmParams)
    print "Temporal pooler parameters: {0}".format(tpParams)
    print
    print "Setting up experiment..."
    runner = SensorimotorExperimentRunner(tmOverrides=tmParams,
                                          tpOverrides=tpParams)
    print "Done setting up experiment."
    print

    exhaustiveAgents = []
    randomAgents = []
    completeSequenceLength = numElements ** 2

    for world in xrange(numWorlds):
      elements = range(world * numElements, world * numElements + numElements)

      exhaustiveAgents.append(
        ExhaustiveOneDAgent(OneDWorld(universe, elements), 0))

      possibleMotorValues = range(-numElements, numElements + 1)
      possibleMotorValues.remove(0)
      randomAgents.append(
        RandomOneDAgent(OneDWorld(universe, elements), numElements / 2,
                        possibleMotorValues=possibleMotorValues))

    print "Training (worlds: {0}, elements: {1})...".format(numWorlds,
                                                            numElements)
    print
    if isOnline:
      trainOnline(runner, exhaustiveAgents, completeSequenceLength,
                  onlineTrainingReps)
    else:
      trainTwoPass(runner, exhaustiveAgents, completeSequenceLength)
    print "Done training."
    print

    if PLOT >= 1:
      title = "worlds: {0}, elements: {1}".format(numWorlds, numElements)
      runner.tm.mmGetCellActivityPlot(title=title, showReset=True,
                                      activityType="activeCells")
      runner.tm.mmGetCellActivityPlot(title=title, showReset=True,
                                      activityType="correctlyPredictedCells")
      runner.tm.mmGetCellActivityPlot(title=title, showReset=True,
                                      activityType="predictiveCells")
      # runner.tp.mmGetPlotConnectionsPerColumn(title=title)

    print "Testing (worlds: {0}, elements: {1})...".format(numWorlds,
                                                           numElements)
    sequences = runner.generateSequences(completeSequenceLength / 4,
                                         randomAgents,
                                         verbosity=VERBOSITY,
                                         numSequences=4)
    runner.feedLayers(sequences, tmLearn=False, tpLearn=False,
                      verbosity=VERBOSITY,
                      showProgressInterval=SHOW_PROGRESS_INTERVAL)
    print "Done testing.\n"
    if PLOT >= 1:
      title = "worlds: {0}, elements: {1}".format(numWorlds, numElements)
      # runner.tm.mmGetCellActivityPlot(title=title, showReset=True,
      #                                 resetShading=0.4)
      runner.tp.mmGetCellActivityPlot(title=title, showReset=True,
                                      resetShading=0.4)

    if VERBOSITY >= 2:
      print "Overlap:"
      print
      print runner.tp.mmPrettyPrintDataOverlap()
      print

    print MonitorMixinBase.mmPrettyPrintMetrics(
      runner.tp.mmGetDefaultMetrics() + runner.tm.mmGetDefaultMetrics())
    print

    elapsed = int(time.time() - start)
    print "Total time: {0:2} seconds.".format(elapsed)

    header = ["# worlds", "# elements", "duration"]
    row = [numWorlds, numElements, elapsed]

    for metric in (runner.tp.mmGetDefaultMetrics() +
                     runner.tm.mmGetDefaultMetrics()):
      header += ["{0} ({1})".format(metric.prettyPrintTitle(), x) for x in
                 ["min", "max", "sum", "mean", "stddev"]]
      row += [metric.min, metric.max, metric.sum,
              metric.mean, metric.standardDeviation]

    csvWriter.writerow(header)
    csvWriter.writerow(row)
    csvFile.flush()

  if PLOT >= 1:
    raw_input("Press any key to exit...")



if __name__ == "__main__":
  if len(sys.argv) < 5:
    print "Usage: ./experiment.py NUM_WORLDS NUM_ELEMENTS OUTPUT_DIR IS_ONLINE"
    sys.exit()

  run(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], isOnline=sys.argv[4])
