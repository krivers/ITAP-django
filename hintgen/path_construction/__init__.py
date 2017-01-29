from ..generate_message import formatHints
from .generateNextStates import getNextState

def generatePaths(states):
	"""Generate all the paths within this solution space"""
	i = 0
	while i < len(states):
		state = states[i]
		if state.score != 1:
			getNextState(state, states) # can add more states
		if state.edit != None:
			state.hint = formatHints(state)
		if state.goal == None: # Fix these for logging purposes
			state.goal = ""
			state.goalDist = ""
		i += 1
