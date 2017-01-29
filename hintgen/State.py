from .astTools import deepcopy

# The State class holds all the relevent information for a solution state
class State:
	id = None
	name = None
	score = None
	feedback = None

	fun = None 
	loadedFun = None
	tree = None

	def __cmp__(this, other):
		if not isinstance(other, State):
			return -1
		c1 = cmp(this.fun, other.fun)
		c2 = cmp(this.name, other.name)
		c3 = cmp(this.id, other.id)
		return c1 if c1 != 0 else c2 if c2 != 0 else c3

	def deepcopy(this):
		s = State()
		s.id = this.id
		s.name = this.name
		s.score = this.score
		s.fun = this.fun
		s.tree = deepcopy(this.tree)

		properties = ["count", "goal", "goal_id", "goalDist",
						"next", "next_id", "edit", "hint", "treeWeight"]
		for prop in properties:
			if hasattr(this, prop):
				setattr(s, prop, getattr(this, prop))
		return s

class OriginalState(State):
	canonicalId = None

	def deepcopy(this):
		s = OriginalState()
		s.id = this.id
		s.canonicalId = this.canonicalId
		s.name = this.name
		s.score = this.score
		s.fun = this.fun
		s.tree = deepcopy(this.tree)

		properties = ["count", "goal", "goal_id", "goalDist",
						"next", "next_id", "edit", "hint", "treeWeight"]
		for prop in properties:
			if hasattr(this, prop):
				setattr(s, prop, getattr(this, prop))
		return s

class CanonicalState(State):
	count = 0 # how many students have submitted this state before?

	goal = None # the eventual goal state for this student
	goalDist = -1
	goal_id = None

	next = None # the next state in the solution space
	next_id = None
	edit = None # the changes on the edge to the next state

	def deepcopy(this):
		s = CanonicalState()
		s.id = this.id
		s.name = this.name
		s.score = this.score
		s.fun = this.fun
		s.tree = deepcopy(this.tree)

		s.count = this.count
		s.goal = this.goal
		s.goal_id = this.goal_id
		s.goalDist = this.goalDist
		s.next = this.next
		s.next_id = this.next_id
		s.edit = this.edit

		if hasattr(this, "hint"):
			s.hint = this.hint
		if hasattr(this, "treeWeight"):
			s.treeWeight = this.treeWeight
		return s