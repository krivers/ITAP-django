import ast
from ..tools import log
from ..astTools import *
from ..namesets import astNames
from ..ChangeVector import *
from ..State import *

def getWeight(a, countTokens=True):
	"""Get the size of the given tree"""
	if a == None:
		return 0
	elif type(a) == list:
		return sum(map(lambda x : getWeight(x, countTokens), a))
	elif not isinstance(a, ast.AST):
		return 1
	else: # Otherwise, it's an AST node
		if hasattr(a, "treeWeight"):
			return a.treeWeight
		weight = 0
		if type(a) in [ast.Module, ast.Interactive, ast.Suite]:
			weight = getWeight(a.body, countTokens=countTokens)
		elif type(a) == ast.Expression:
			weight = getWeight(a.body, countTokens=countTokens)
		elif type(a) == ast.FunctionDef:
			# add 1 for function name
			weight = 1 + getWeight(a.args, countTokens=countTokens) + \
					getWeight(a.body, countTokens=countTokens) + \
					getWeight(a.decorator_list, countTokens=countTokens) + \
					getWeight(a.returns, countTokens=countTokens)
		elif type(a) == ast.ClassDef:
			# add 1 for class name
			weight = 1 + sumWeight(a.bases, countTokens=countTokens) + \
					sumWeight(a.keywords, countTokens=countTokens) + \
					getWeight(a.body, countTokens=countTokens) + \
					getWeight(a.decorator_list, countTokens=countTokens)
		elif type(a) in [ast.Return, ast.Yield, ast.Attribute]:
			# add 1 for action name
			weight = 1 + getWeight(a.value, countTokens=countTokens)
		elif type(a) == ast.Delete: # add 1 for del
			weight = 1 + getWeight(a.targets, countTokens=countTokens)
		elif type(a) == ast.Assign: # add 1 for =
			weight = 1 + getWeight(a.targets, countTokens=countTokens) + \
					getWeight(a.value, countTokens=countTokens)
		elif type(a) == ast.AugAssign:
			weight = getWeight(a.target, countTokens=countTokens) + \
					getWeight(a.op, countTokens=countTokens) + \
					getWeight(a.value, countTokens=countTokens)
		elif type(a) == ast.For: # add 1 for 'for' and 1 for 'in'
			weight = 2 + getWeight(a.target, countTokens=countTokens) + \
					getWeight(a.iter, countTokens=countTokens) + \
					getWeight(a.body, countTokens=countTokens) + \
					getWeight(a.orelse, countTokens=countTokens)
		elif type(a) in [ast.While, ast.If]:
			# add 1 for while/if
			weight = 1 + getWeight(a.test, countTokens=countTokens) + \
					getWeight(a.body, countTokens=countTokens)
			if len(a.orelse) > 0: # add 1 for else
				weight += 1 + getWeight(a.orelse, countTokens=countTokens)
		elif type(a) == ast.With: # add 1 for with
			weight = 1 + getWeight(a.items, countTokens=countTokens) + \
					getWeight(a.body, countTokens=countTokens)
		elif type(a) == ast.Raise: # add 1 for raise
			weight = 1 + getWeight(a.exc, countTokens=countTokens) + \
					getWeight(a.cause, countTokens=countTokens)
		elif type(a) == ast.Try: # add 1 for try
			weight = 1 + getWeight(a.body, countTokens=countTokens) + \
					getWeight(a.handlers, countTokens=countTokens)
			if len(a.orelse) > 0: # add 1 for else
				weight += 1 + getWeight(a.orelse, countTokens=countTokens)
			if len(a.finalbody) > 0: # add 1 for finally
				weight += 1 + getWeight(a.finalbody, countTokens=countTokens)
		elif type(a) == ast.Assert: # add 1 for assert
			weight = 1 + getWeight(a.test, countTokens=countTokens) + \
					getWeight(a.msg, countTokens=countTokens)
		elif type(a) in [ast.Import, ast.Global]: # add 1 for function name
			weight = 1 + getWeight(a.names, countTokens=countTokens)
		elif type(a) == ast.ImportFrom: # add 3 for from module import
			weight = 3 + getWeight(a.names, countTokens=countTokens)
		elif type(a) in [ast.Expr, ast.Index]:
			weight = getWeight(a.value, countTokens=countTokens)
			if weight == 0:
				weight = 1
		elif type(a) == ast.BoolOp: # add 1 for each op
			weight = (len(a.values) - 1) + \
					getWeight(a.values, countTokens=countTokens)
		elif type(a) == ast.BinOp: # add 1 for op
			weight = 1 + getWeight(a.left, countTokens=countTokens) + \
					getWeight(a.right, countTokens=countTokens)
		elif type(a) == ast.UnaryOp: # add 1 for operator
			weight = 1 + getWeight(a.operand, countTokens=countTokens)
		elif type(a) == ast.Lambda: # add 1 for lambda
			weight = 1 + getWeight(a.args, countTokens=countTokens) + \
					getWeight(a.body, countTokens=countTokens)
		elif type(a) == ast.IfExp: # add 2 for if and else
			weight = 2 + getWeight(a.test, countTokens=countTokens) + \
					getWeight(a.body, countTokens=countTokens) + \
					getWeight(a.orelse, countTokens=countTokens)
		elif type(a) == ast.Dict: # return 1 if empty dictionary
			weight = 1 + getWeight(a.keys, countTokens=countTokens) + \
					getWeight(a.values, countTokens=countTokens)
		elif type(a) in [ast.Set, ast.List, ast.Tuple]:
			weight = 1 + getWeight(a.elts, countTokens=countTokens)
		elif type(a) in [ast.ListComp, ast.SetComp, ast.GeneratorExp]:
			weight = 1 + getWeight(a.elt, countTokens=countTokens) + \
					getWeight(a.generators, countTokens=countTokens)
		elif type(a) == ast.DictComp:
			weight = 1 + getWeight(a.key, countTokens=countTokens) + \
					getWeight(a.value, countTokens=countTokens) + \
					getWeight(a.generators, countTokens=countTokens)
		elif type(a) == ast.Compare:
			weight = len(a.ops) + getWeight(a.left, countTokens=countTokens) + \
					getWeight(a.comparators, countTokens=countTokens)
		elif type(a) == ast.Call:
			functionWeight = getWeight(a.func, countTokens=countTokens)
			functionWeight = functionWeight if functionWeight > 0 else 1
			argsWeight = getWeight(a.args, countTokens=countTokens) + \
					getWeight(a.keywords, countTokens=countTokens)
			argsWeight = argsWeight if argsWeight > 0 else 1
			weight = functionWeight + argsWeight
		elif type(a) == ast.Subscript:
			valueWeight = getWeight(a.value, countTokens=countTokens)
			valueWeight = valueWeight if valueWeight > 0 else 1
			sliceWeight = getWeight(a.slice, countTokens=countTokens)
			sliceWeight = sliceWeight if sliceWeight > 0 else 1
			weight = valueWeight + sliceWeight

		elif type(a) == ast.Slice:
			weight = getWeight(a.lower, countTokens=countTokens) + \
					getWeight(a.upper, countTokens=countTokens) + \
					getWeight(a.step, countTokens=countTokens)
			if weight == 0:
				weight = 1
		elif type(a) == ast.ExtSlice:
			weight = getWeight(a.dims, countTokens=countTokens)

		elif type(a) == ast.comprehension: # add 2 for for and in
			# and each of the if tokens
			weight = 2 + len(a.ifs) + \
					getWeight(a.target, countTokens=countTokens) + \
					getWeight(a.iter, countTokens=countTokens) + \
					getWeight(a.ifs, countTokens=countTokens)
		elif type(a) == ast.ExceptHandler: # add 1 for except
			weight = 1 + getWeight(a.type, countTokens=countTokens)
			# add 1 for as (if needed)
			weight += (1 if a.name != None else 0) + \
					getWeight(a.name, countTokens=countTokens)
			weight += getWeight(a.body, countTokens=countTokens)
		elif type(a) == ast.arguments:
			weight = getWeight(a.args, countTokens=countTokens) + \
					getWeight(a.vararg, countTokens=countTokens) + \
					getWeight(a.kwonlyargs, countTokens=countTokens) + \
					getWeight(a.kw_defaults, countTokens=countTokens) + \
					getWeight(a.kwarg, countTokens=countTokens) + \
					getWeight(a.defaults, countTokens=countTokens)
		elif type(a) == ast.arg:
			weight = 1 + getWeight(a.annotation, countTokens=countTokens)
		elif type(a) == ast.keyword: # add 1 for identifier
			weight = 1 + getWeight(a.value, countTokens=countTokens)
		elif type(a) == ast.alias: # 1 for name, 1 for as, 1 for asname
			weight = 1 + (2 if a.asname != None else 0)
		elif type(a) == ast.withitem:
			weight = getWeight(a.context_expr, countTokens=countTokens) + \
					 getWeight(a.optional_vars, countTokens=countTokens)
		elif type(a) == ast.Str:
			if countTokens:
				weight = 1
			elif len(a.s) >= 2 and a.s[0] == "~" and a.s[-1] == "~":
				weight = 0
			else:
				weight = 1

		elif type(a) in [ast.Pass, ast.Break, ast.Continue, ast.Num, ast.Bytes, 
						 ast.NameConstant, ast.Name,
						 ast.Ellipsis]:
			weight = 1
		elif type(a) in [ast.And, ast.Or, 
						 ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
						 ast.LShift, ast.RShift, ast.BitOr, ast.BitXor,
						 ast.BitAnd, ast.FloorDiv,
						 ast.Invert, ast.Not, ast.UAdd, ast.USub,
						 ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
						 ast.Is, ast.IsNot, ast.In, ast.NotIn,
						 ast.Load, ast.Store, ast.Del, ast.AugLoad,
						 ast.AugStore, ast.Param ]:
			weight = 1
		else:
			log("diffAsts\tgetWeight\tMissing type in diffAsts: " + str(type(a)), "bug")
			return 1
		setattr(a, "treeWeight", weight)
		return weight

def matchLists(x, y):
	"""For each line in x, determine which line it best maps to in y"""
	x = [ (x[i], i) for i in range(len(x)) ]
	y = [ (y[i], i) for i in range(len(y)) ]
	# First, separate out all the lines based on their types, as we only match between types
	typeMap = { }
	for i in range(len(x)):
		t = type(x[i][0])
		if (t in typeMap):
			pass
		xSubset = list(filter(lambda tmp : type(tmp[0]) == t, x))
		ySubset = list(filter(lambda tmp : type(tmp[0]) == t, y))
		typeMap[t] = (xSubset, ySubset)
	for j in range(len(y)):
		t = type(y[j][0])
		if t in typeMap:
			pass
		xSubset = list(filter(lambda tmp : type(tmp[0]) == t, x))
		ySubset = list(filter(lambda tmp : type(tmp[0]) == t, y))
		typeMap[t] = (xSubset, ySubset)

	mapSet = {}
	for t in typeMap:
		# For each type, find the optimal matching
		(xSubset, ySubset) = typeMap[t]
		# First, find exact matches and remove them
		# Give preference to items on the same line- then we won't need to do an edit
		i = 0
		while i < len(xSubset):
			j = 0
			while j < len(ySubset):
				if xSubset[i][1] == ySubset[j][1]:
					if compareASTs(xSubset[i][0], ySubset[j][0], checkEquality=True) == 0:
						mapSet[ySubset[j][1]] = xSubset[i][1]
						xSubset.pop(i)
						ySubset.pop(j)
						break
				j += 1
			else:
				i += 1
		# Then look for matches anywhere
		i = 0
		while i < len(xSubset):
			j = 0
			while j < len(ySubset):
				if compareASTs(xSubset[i][0], ySubset[j][0], checkEquality=True) == 0:
					mapSet[ySubset[j][1]] = xSubset[i][1]
					xSubset.pop(i)
					ySubset.pop(j)
					break
				j += 1
			else:
				i += 1 # if we break, don't increment!
		# TODO - check for subsets/supersets in here?
		# Then, look for the 'best we can do' matches
		distanceList = [ ]
		for i in range(len(xSubset)): # Ientify the best matches across all pairs
			st1 = State()
			st1.tree = xSubset[i][0]
			for j in range(len(ySubset)):
				st2 = State()
				st2.tree = ySubset[j][0]
				d, _ = distance(st1, st2)
				d = int(d * 1000)
				distanceList.append((d, xSubset[i][1], ySubset[j][1]))
		# Compare first based on distance, then based on how close the lines are to each other
		distanceList.sort(key=lambda x : (x[0], x[1] - x[2]))
		l = min(len(xSubset), len(ySubset))
		# Now pick the best pairs 'til we run out of them
		while l > 0:
			(d, xLine, yLine) = distanceList[0]
			mapSet[yLine] = xLine
			distanceList = list(filter(lambda x : x[1] != xLine and x[2] != yLine, distanceList))
			l -= 1
	# Now, look for matches across different types
	leftoverY = list(filter(lambda tmp : tmp not in mapSet, range(len(y))))
	leftoverX = list(filter(lambda tmp : tmp not in mapSet.values(), range(len(x))))
	# First, look for exact line matches
	i = 0
	while i < len(leftoverX):
		line = leftoverX[i]
		if line in leftoverY:
			mapSet[line] = line
			leftoverX.remove(line)
			leftoverY.remove(line)
		else:
			i += 1
	# Then, just put the rest in place
	for i in range(min(len(leftoverY), len(leftoverX))): # map together all equal parts
		mapSet[leftoverY[i]] = leftoverX[i]
	if len(leftoverX) > len(leftoverY): # if X greater, map all leftover x's to -1
		mapSet[-1] = leftoverX[len(leftoverY):]
	elif len(leftoverY) > len(leftoverX): # if Y greater, map all leftover y's to -1
		for i in range(len(leftoverX), len(leftoverY)):
			mapSet[leftoverY[i]] = -1
	# if equal, there are none left to map!
	return mapSet

def findKey(d, val):
	for k in d:
		if d[k] == val:
			return k
	return None

def xOffset(line, deletedLines):
	offset = 0
	for l in deletedLines:
		if l <= line:
			offset += 1
	return offset

def yOffset(line, addedLines):
	offset = 0
	for l in addedLines:
		if l <= line:
			offset += 1
	return offset

def findSwap(startList, endList):
	for i in range(len(startList)):
		if startList[i] == endList[i]:
			pass
		for j in range(i+1, len(startList)):
			if startList[i] == endList[j] and endList[i] == startList[j]:
				return SwapVector([-1], startList[i], startList[j])
	return None

# Recursively generate all moves by working from the outside of the list inwards.
# This should be optimal for lists of up to size four, and once you get to size five, your program is too
# large and I don't care anymore.
def generateMovePairs(startList, endList):
	if len(startList) <= 1:
		return []
	elif startList[0] == endList[0]:
		return generateMovePairs(startList[1:], endList[1:])
	elif startList[-1] == endList[-1]:
		return generateMovePairs(startList[:-1], endList[:-1])
	elif startList[0] == endList[-1] and startList[-1] == endList[0]:
		# swap the two ends
		return [("swap", startList[0], startList[-1])] + generateMovePairs(startList[1:-1], endList[1:-1])
	elif startList[0] == endList[-1]:
		# move the smallest element from back to front
		return [("move", startList[0])] + generateMovePairs(startList[1:], endList[:-1])
	elif startList[-1] == endList[0]:
		# move the largest element from front to back
		return [("move", startList[-1])] + generateMovePairs(startList[:-1], endList[1:])
	else:
		i = endList.index(startList[0]) # find the position in endList
		return [("move", startList[0])] + generateMovePairs(startList[1:], endList[:i] + endList[i+1:])

def findMoveVectors(mapSet, x, y, add, delete):
	"""We'll find all the moved lines by recreating the mapSet from a tmpSet using actions"""
	startList = list(range(len(x)))
	endList = [mapSet[i] for i in range(len(y))]
	# Remove deletes from startList and adds from endList
	for line in delete:
		startList.remove(line)
	while -1 in endList:
		endList.remove(-1)
	if len(startList) != len(endList):
		log("diffAsts\tfindMovedLines\tUnequal lists: " + str(len(startList)) + "," + str(len(endList)), "bug")
		return []
	moveActions = []
	if startList != endList:
		movePairs = generateMovePairs(startList, endList)
		for pair in movePairs:
			if pair[0] == "move":
				moveActions.append(MoveVector([-1], pair[1], endList.index(pair[1])))
			elif pair[0] == "swap":
				moveActions.append(SwapVector([-1], pair[1], pair[2]))
			else:
				log("Missing movePair type: " + str(pair[0]), "bug")
	return moveActions

def diffLists(x, y, ignoreVariables=False):
	mapSet = matchLists(x, y)
	changeVectors = []

	# First, get all the added and deleted lines
	deletedLines = mapSet[-1] if -1 in mapSet else []
	for line in sorted(deletedLines):
		changeVectors.append(DeleteVector([line], x[line], None))

	addedLines = list(filter(lambda tmp : mapSet[tmp] == -1, mapSet.keys()))
	addedOffset = 0 # Because added lines don't start in the list, we need
					# to offset their positions for each new one that's added
	for line in sorted(addedLines):
		changeVectors.append(AddVector([line - addedOffset], None, y[line]))
		addedOffset += 1

	# Now, find all the required moves
	changeVectors += findMoveVectors(mapSet, x, y, addedLines, deletedLines)

	# Finally, for each pair of lines (which have already been moved appropriately,
	# find if they need a normal ChangeVector
	for j in mapSet:
		i = mapSet[j]
		# Not a delete or an add
		if j != -1 and i != -1:
			tempVectors = diffAsts(x[i], y[j], ignoreVariables=ignoreVariables)
			for change in tempVectors:
				change.path.append(i)
			changeVectors += tempVectors
	return changeVectors

def diffAsts(x, y, ignoreVariables=False):
	"""Find all change vectors between x and y"""
	xAST = isinstance(x, ast.AST)
	yAST = isinstance(y, ast.AST)
	if xAST and yAST:
		if type(x) != type(y): # different node types
			if occursIn(x, y):
				return [SubVector([], x, y)]
			elif occursIn(y, x):
				return [SuperVector([], x, y)]
			else:
				return [ChangeVector([], x, y)]
		elif ignoreVariables and type(x) == type(y) == ast.Name:
			if not builtInName(x.id) and not builtInName(y.id):
				return [] # ignore the actual IDs

		result = []
		for field in x._fields:
			currentDiffs = diffAsts(getattr(x, field), getattr(y, field), ignoreVariables=ignoreVariables)
			if currentDiffs != []: # add the next step in the path
				for change in currentDiffs:
					change.path.append((field, astNames[type(x)]))
				result += currentDiffs
		return result
	elif (not xAST) and (not yAST):
		if type(x) == list and type(y) == list:
			return diffLists(x, y, ignoreVariables=ignoreVariables)
		elif x != y or type(x) != type(y): # need the type check to distinguish ints from floats
			return [ChangeVector([], x, y)] # they're primitive, so just switch them
		else: # equal values
			return []
	else: # Two mismatched types
		return [ChangeVector([], x, y)]

def getChanges(s, t, ignoreVariables=False):
	changes = diffAsts(s, t, ignoreVariables=ignoreVariables)
	for change in changes:
		change.start = s # WARNING: should maybe have a deepcopy here? It will alias s
	return changes

def getChangesWeight(changes, countTokens=True):
	weight = 0
	for change in changes:
		if isinstance(change, AddVector):
			weight += getWeight(change.newSubtree, countTokens=countTokens)
		elif isinstance(change, DeleteVector):
			weight += getWeight(change.oldSubtree, countTokens=countTokens)
		elif isinstance(change, SwapVector):
			weight += 2 # only changing the positions
		elif isinstance(change, MoveVector):
			weight += 1 # only moving one item
		elif isinstance(change, SubVector):
			weight += abs(getWeight(change.newSubtree, countTokens=countTokens) - \
						  getWeight(change.oldSubtree, countTokens=countTokens))
		elif isinstance(change, SuperVector):
			weight += abs(getWeight(change.oldSubtree, countTokens=countTokens) - \
						  getWeight(change.newSubtree, countTokens=countTokens))
		else:
			weight += max(getWeight(change.oldSubtree, countTokens=countTokens), 
						  getWeight(change.newSubtree, countTokens=countTokens))
	return weight

def distance(s, t, givenChanges=None, forceReweight=False, ignoreVariables=False):
	"""A method for comparing solution states, which returns a number between
		0 (identical solutions) and 1 (completely different)"""
	# First weigh the trees, to propogate metadata
	if s == None or t == None:
		return 1 # can't compare to a None state
	if forceReweight:
		baseWeight = max(getWeight(s.tree), getWeight(t.tree))
	else:
		if not hasattr(s, "treeWeight"):
			s.treeWeight = getWeight(s.tree)
		if not hasattr(t, "treeWeight"):
			t.treeWeight = getWeight(t.tree)
		baseWeight = max(s.treeWeight, t.treeWeight)

	if givenChanges != None:
		changes = givenChanges
	else:
		changes = getChanges(s.tree, t.tree, ignoreVariables=ignoreVariables)

	changeWeight = getChangesWeight(changes)
	return (1.0 * changeWeight / baseWeight, changes)