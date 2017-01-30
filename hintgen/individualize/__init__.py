import ast, copy
from ..path_construction import diffAsts, generateNextStates
from ..ChangeVector import *
from ..astTools import negate, isAnonVariable, removePropertyFromAll, transferMetaData
from ..path_construction import generateNextStates
from ..tools import log
from ..namesets import astNames
from ..display import printFunction

def generatePathToId(a, id, globalId=None):
	if not isinstance(a, ast.AST):
		return None
	if hasattr(a, "global_id") and a.global_id == id:
		if globalId == None or (hasattr(a, "variableGlobalId") and a.variableGlobalId == globalId):
			return []

	for field in a._fields:
		attr = getattr(a, field)
		if type(attr) == list:
			for i in range(len(attr)):
				path = generatePathToId(attr[i], id, globalId)
				if path != None:
					path.append(i)
					path.append((field, astNames[type(a)]))
					return path
		else:
			path = generatePathToId(attr, id, globalId)
			if path != None:
				path.append((field, astNames[type(a)]))
				return path
	return None

def childHasTag(a, tag):
	if type(a) == list:
		for child in a:
			if childHasTag(child, tag):
				return True
		return False
	elif not isinstance(a, ast.AST):
		return False
	for node in ast.walk(a):
		if hasattr(node, tag):
			return True
	return False

def undoReverse(a):
	tmp = None
	if type(a) == ast.Lt:
		tmp = ast.Gt()
	elif type(a) == ast.LtE:
		tmp = ast.GtE()
	elif type(a) == ast.Gt:
		tmp = ast.Lt()
	elif type(a) == ast.GtE:
		tmp = ast.LtE()
	else:
		return a
	transferMetaData(a, tmp)
	return tmp

# Applies special functions if they're included as metadata OR if they're specified by ID
def specialFunctions(old, new):
	if type(old) == type(new) == list:
		for i in range(min(len(old), len(new))):
			(old[i], new[i]) = specialFunctions(old[i], new[i])
		return (old, new)
	rev = neg = False
	if (hasattr(old, "reversed") and old.reversed and (not hasattr(old, "multCompFixed"))):
		rev = True

	if (hasattr(old, "negated") and old.negated):
		neg = True

	if rev and neg:
		(old, new) = (negate(undoReverse(old)), negate(undoReverse(new)))
	elif rev:
		(old, new) = (undoReverse(old), undoReverse(new))
	elif neg:
		(old, new) = (negate(old), negate(new))
		if type(old) == ast.UnaryOp and type(old.op) == ast.Not and \
			type(new) == ast.UnaryOp and type(new.op) == ast.Not:
			# Just get rid of them
			old = old.operand
			new = new.operand

	#if (hasattr(old, "inverted") and old.inverted):
	#	(old, new) = (invert(old), invert(new))

	return (old, new)

def countNewVarsInD(d):
	max = 0
	for var in d.values():
		if var[:len("new_var_")] == "new_var_":
			num = int(var[len("new_var_"):]) + 1
			if num > max:
				max = num
	return max

def mapNames(a, d):
	if type(a) == str and a in d:
		return d[a]
	if type(a) == list:
		for item in a:
			mapNames(item, d)
		return a
	if not isinstance(a, ast.AST):
		return a
	if type(a) == ast.FunctionDef:
		if a.name in d:
			a.name = d[a.name]
	elif type(a) == ast.Name:
		if not hasattr(a, "alreadyMapped"):
			if a.id in d:
				a.id = d[a.id]
				a.alreadyMapped = True
			else:
				if isAnonVariable(a.id): # if it's a variable that won't be getting mapped
					# How many new vars are there already?
					num = countNewVarsInD(d)
					d[a.id] = "new_var_" + str(num)
					a.id = d[a.id]
					a.alreadyMapped = True
		return a
	for child in ast.iter_child_nodes(a):
		child = mapNames(child, d)
	return a

def createNameMap(a, d=None):
	if d == None:
		d = { }
	if not isinstance(a, ast.AST):
		return d
	if type(a) in [ast.FunctionDef, ast.ClassDef]:
		if hasattr(a, "originalId") and a.name not in d:
			d[a.name] = a.originalId
	elif type(a) == ast.Name:
		if hasattr(a, "originalId") and a.id not in d:
			d[a.id] = a.originalId
		return d
	for child in ast.iter_child_nodes(a):
		createNameMap(child, d)
	return d

def findId(a, id):
	if hasattr(a, "global_id") and a.global_id == id:
		return a
	if not isinstance(a, ast.AST):
		return None
	for child in ast.iter_child_nodes(a):
		tmp = findId(child, id)
		if tmp != None:
			return tmp
	return None

def findListId(a, id):
	# We want to go one level up to get the list this belongs to
	if type(a) == list and len(a) > 0 and hasattr(a[0], "global_id") and a[0].global_id == id:
		return a
	if type(a) == list:
		for item in a:
			tmp = findListId(item, id)
			if tmp != None:
				return tmp
	elif isinstance(a, ast.AST):
		for (field, val) in ast.iter_fields(a):
			tmp = findListId(val, id)
			if tmp != None:
				return tmp
	return None

def getSubtreeContext(super, sub):
	if not isinstance(super, ast.AST):
		return None

	for field in super._fields:
		attr = getattr(super, field)
		if type(attr) == list:
			for i in range(len(attr)):
				if compareASTs(attr[i], sub, checkEquality=True) == 0:
					return (attr, i, attr[i])
				else:
					tmp = getSubtreeContext(attr[i], sub)
					if tmp != None:
						return tmp
		else:
			if compareASTs(attr, sub, checkEquality=True) == 0:
				return (super, field, attr)
			else:
				tmp = getSubtreeContext(attr, sub)
				if tmp != None:
					return tmp
	return None

def basicTypeSpecialFunction(cv):
	"""If you're in a number or string (which has no metadata), move up to the AST to make the special functions work."""
	if isinstance(cv, SwapVector) or isinstance(cv, MoveVector):
		return cv
	if type(cv.oldSubtree) == type(cv.newSubtree) and \
			(cv.path[0] in [('n', 'Number'), ('s', 'String'), ('id', 'Name'), ('value', 'Name Constant'), ('s', 'Bytes')]):
		cvCopy = cv.deepcopy()
		cv.oldSubtree = cvCopy.traverseTree(deepcopy(cv.start))
		if cv.path[0] == ('n', 'Number'):
			cv.newSubtree = ast.Num(cv.newSubtree)
		elif cv.path[0] == ('s', 'String'):
			cv.newSubtree = ast.Str(cv.newSubtree)
		elif cv.path[0] == ('id', 'Name'):
			cv.newSubtree = ast.Name(cv.newSubtree, cv.oldSubtree.ctx)
		elif cv.path[0] == ('value', 'Name Constant'):
			cv.newSubtree = ast.NameConstant(cv.newSubtree)
		elif cv.path[0] == ('s', 'Bytes'):
			cv.newSubtree = ast.Bytes(cv.newSubtree)
		cv.path = cv.path[1:]
	return cv

def propagatedVariableSpecialFunction(cv, replacedVariables):
	if hasattr(cv.oldSubtree, "propagatedVariable"):
		# need to move up in the tree until we hit the initial variable assigned
		cvCopy = cv.deepcopy()
		newTree = cvCopy.applyChange()
		oldSpot = cvCopy.oldSubtree
		newSpot = cvCopy.newSubtree
		cvCopy.path = [-1] + cvCopy.path
		while type(oldSpot) == list or (not hasattr(oldSpot, "loadedVariable") and hasattr(oldSpot, "propagatedVariable")):
			cvCopy = cvCopy.deepcopy()
			cvCopy.path = cvCopy.path[1:]
			oldSpot = cvCopy.traverseTree(deepcopy(cvCopy.start))
			newSpot = cvCopy.traverseTree(deepcopy(newTree))
		if hasattr(oldSpot, "loadedVariable") and oldSpot.variableGlobalId not in replacedVariables:
			return ChangeVector(cvCopy.path[1:], oldSpot, newSpot, start=cvCopy.start)
		elif hasattr(oldSpot, "loadedVariable"):
			pass
		else:
			log("Individualize\tCouldn't move up to a ChangeVector: " + printFunction(oldSpot, 0) + " - " + printFunction(newSpot, 0), "bug")
	return cv

def helperFoldingSpecialFunction(cv, orig):
	if hasattr(cv.oldSubtree, "helperVar") or hasattr(cv.oldSubtree, "helperReturnVal") or \
		hasattr(cv.oldSubtree, "helperParamAssign") or hasattr(cv.oldSubtree, "helperReturnAssn"):
		log("Oh no! helper function!" + "\n" + str(cv) + "\n" + \
					printFunction(cv.start, 0) + "\n" + \
					printFunction(orig, 0), "bug")
		raise Exception("See above")
	return cv

def noneSpecialFunction(cv):
	"""If the old type is 'None' (which won't show up in the original), move up in the AST to get the metadata"""
	if (not isinstance(cv, AddVector)) and cv.oldSubtree == None:
		cvCopy = cv.deepcopy()
		if cv.path[0] == ('value', 'Return'):
			cv.oldSubtree = cvCopy.traverseTree(deepcopy(cv.start))
			cv.newSubtree = ast.Return(cv.newSubtree)
			cv.path = cv.path[1:]
		elif cv.path[0] in [('lower', 'Slice'), ('upper', 'Slice'), ('step', 'Slice')]:
			tmpNew = cv.newSubtree
			cvCopy = cv.deepcopy()
			cv.oldSubtree = cvCopy.traverseTree(deepcopy(cv.start))
			cv.newSubtree = deepcopy(cv.oldSubtree) # use the same slice
			if cv.path[0][0] == 'lower':
				cv.newSubtree.lower = tmpNew
			elif cv.path[0][0] == 'upper':
				cv.newSubtree.upper = tmpNew
			else:
				cv.newSubtree.step = tmpNew
			cv.path = cv.path[1:] # get rid of None and the val
		else:
			log("Individualize\tmapEdit\tMissing option in None special case: " + str(cv.path[0]), "bug")
	elif cv.oldSubtree == "None":
		cv.path = cv.path[1:] # get rid of None and the id
		cvCopy = cv.deepcopy()
		cv.oldSubtree = cvCopy.traverseTree(deepcopy(cv.start))
		if cv.path[0] == ('value', 'Return'):
			cv.newSubtree = ast.Return(ast.Name(cv.newSubtree, ast.Load()))
		else:
			log("Individualize\tmapEdit\tMissing option in None special case: " + str(cv.path[0]), "bug")
		cv.path = cv.path[1:]
	return cv

def hasMultiComp(a):
	if not isinstance(a, ast.AST):
		return False
	for node in ast.walk(a):
		if hasattr(node, "multiComp") and node.multiComp:
			return True
	return False

def multiCompSpecialFunction(cv, orig, canon):
	"""Check if this is the special multi-comparison case. If it is, modify the expression appropriately."""
	# If we're adding a comp/op to a comparison
	if isinstance(cv, AddVector) and cv.path[1] in [('ops', 'Compare'), ('comparators', 'Compare')]:
		if hasattr(cv.newSubtree, "multiCompFixed"):
			return cv
		spot = None
		i = 0
		pathLength = len(cv.path)
		cvCopy = cv.deepcopy()
		cvCopy.path = cvCopy.path[1:]
		oldSpot = cvCopy.traverseTree(deepcopy(cv.start))
		cvCopy = cv.deepcopy()
		cvCopy.path = generatePathToId(orig, oldSpot.global_id)
		if cvCopy.path != None:
			cvCopy.path = [(None,None)] + cvCopy.path # The None,None is to force the traversal to go all the way to the node we want, instead of its parent
			newSpot = cvCopy.traverseTree(deepcopy(orig))
			cvCopy.path = cvCopy.path[1:] # then get rid of the None, None
			if type(newSpot) == ast.Compare and type(oldSpot) == ast.Compare:
				# We can insert the new thing normally, it'll automatically get paired with the next edit anyway
				if (not hasattr(oldSpot.ops[0], "reversed")):
					return cv # If it isn't reversed, we're good!
				elif cv.path[1] == ('ops', 'Compare'): # for a reversed op, just do the reverse
					cv.path[0] = len(oldSpot.ops) - cv.path[0]
					cv.newSubtree = undoReverse(cv.newSubtree)
					return cv
				elif cv.path[1] == ('comparators', 'Compare'):
					if cv.path[0] == len(oldSpot.comparators): # reversed, so insert into front
						# This means we need to do some swaps
						changes = []
						# First, replace left with the new value
						newPath = [('left', 'Compare')] + cv.path[2:]
						changes.append(ChangeVector(newPath, newSpot.left, cv.newSubtree, cv.start))
						# Then insert the old left into the front
						cv.path[0] = 0
						newSpot.left.multiCompFixed = True
						changes.append(AddVector(cv.path, None, newSpot.left, cv.start))
						return changes
					else: # otherwise, just change the position
						cv.path[0] = len(oldSpot.comparators) - 1 - cv.path[0]
						return cv
			else:
				log("individualize\tmultiComp\tUnexpected type: " + str(type(oldSpot)) + "," +
						  str(type(newSpot)), "bug")
			# Otherwise, we need to put back in the boolean operation
			cv = SubVector(cvCopy.path, newSpot, ast.BoolOp(ast.And(), [newSpot, cv.newSubtree]), cv.start)
			return cv
	# Catch other multi-comp problems
	if (cv.oldSubtree == None or not hasattr(cv.oldSubtree, "global_id")) and hasMultiComp(canon):
		spot = None
		i = 0
		pathLength = len(cv.path)
		while i < pathLength:
			cvCopy = cv.deepcopy()
			cvCopy.path = cvCopy.path[i:]
			oldSpot = cvCopy.traverseTree(deepcopy(cv.start))
			if hasattr(oldSpot, "multiComp") and oldSpot.multiComp == True:
				break
			i += 1
		if i < pathLength:
			cvCopy = cv.deepcopy()
			cvCopy.path = [(None,None)] + generatePathToId(orig, oldSpot.global_id) # The None,None is to force the traversal to go all the way to the node we want, instead of its parent
			newSpot = cvCopy.traverseTree(deepcopy(orig))
			cvCopy.path = cvCopy.path[1:] # then get rid of the None, None
			if type(newSpot) == ast.Compare: # DON'T CHANGE IT OTHERWISE
				# Otherwise, we need to put back in the boolean operation
				cv = SubVector(cvCopy.path, newSpot, ast.BoolOp(ast.And(), [newSpot, cv.newSubtree]), cv.start)
				return cv
	if hasattr(cv.oldSubtree, "multiCompOp") and cv.oldSubtree.multiCompOp:
		cvCopy = cv.deepcopy()
		oldSpot = cvCopy.traverseTree(deepcopy(canon))
		newSpot = cvCopy.traverseTree(deepcopy(cv.start))
		cv = ChangeVector(cvCopy.path, oldSpot, ast.BoolOp(cv.newSubtree, [newSpot]), cv.start)
		return cv
	if (hasattr(cv.oldSubtree, "multiCompMiddle") and cv.oldSubtree.multiCompMiddle) or \
		(hasattr(cv.oldSubtree, "multiCompPart") and cv.oldSubtree.multiCompPart):
		spot = None
		i = 0
		pathLength = len(cv.path)
		while i < pathLength:
			cvCopy = cv.deepcopy()
			cvCopy.path = cvCopy.path[i:]
			spot = cvCopy.traverseTree(deepcopy(cv.start))
			if hasattr(spot, "multiComp") and spot.multiComp == True:
				break
			i += 1
		# Double check to make sure this is actually still an multicomp
		if i < pathLength and hasattr(spot, "global_id") and \
			type(findId(orig, spot.global_id)) == ast.Compare and \
			len(findId(orig, spot.global_id).ops) > 1:
			oldCvCopy = cv.deepcopy()
			oldCvCopy.path = generatePathToId(orig, spot.global_id)
			oldSpot = oldCvCopy.traverseTree(deepcopy(orig))
			if type(oldCvCopy.path[0]) == int:
				oldSpot = oldSpot[oldCvCopy.path[0]]
			else:
				oldSpot = getattr(oldSpot, oldCvCopy.path[0][0])

			newCvCopy = cv.deepcopy()
			newTree = newCvCopy.applyChange()
			newCvCopy.path = newCvCopy.path[i:]
			newSpot = newCvCopy.traverseTree(newTree)

			cv = ChangeVector(oldCvCopy.path, oldSpot, newSpot, cv.start)
			cv.wasMoveVector = True
			return cv
	return cv

def multiCompAfterSpecialFunction(cv, startingTree, startingPath):
	"""Sometimes, with Move Vectors, items that got combined are no longer combined. Fix this by moving up the tree."""
	if isinstance(cv, MoveVector):
		cvCopy = cv.deepcopy()
		origSpot = cvCopy.traverseTree(deepcopy(cv.start))
		if len(origSpot) <= cv.oldSubtree or len(origSpot) <= cv.newSubtree:
			# Change this to a ChangeVector
			cvCopy.path = startingPath[1:]
			canonSpot = cvCopy.traverseTree(deepcopy(startingTree))
			newSpot = deepcopy(canonSpot)
			if type(canonSpot) == ast.BoolOp:
				newSpot.values.insert(cv.newSubtree, newSpot.values[cv.oldSubtree])
				newSpot.values.pop(cv.oldSubtree + (0 if cv.oldSubtree < cv.newSubtree else 1)) # adjust for length change
			else:
				log("Individualize\tmapEdit\tMissing option in Move Vector special case: " + str(type(canonSpot)), "bug")
			cv = ChangeVector(cv.path[2:], canonSpot, newSpot, cv.start)
			cv.wasMoveVector = True
	return cv

def augAssignSpecialFunction(cv, orig):
	if childHasTag(cv.oldSubtree, "augAssignVal") or childHasTag(cv.oldSubtree, "augAssignBinOp"):
		# First, create the oldTree and newTree in full
		cvCopy = cv.deepcopy()
		cvCopy.start = deepcopy(cv.start)
		newTree = cvCopy.applyChange()

		# This should be in an augassign, move up in the tree until we reach it.
		spot = cv.oldSubtree
		cvCopy = cv
		i = 0
		while type(spot) != ast.Assign and len(cvCopy.path) > i:
			i += 1
			cvCopy = cv.deepcopy()
			cvCopy.path = cv.path[i:]
			spot = cvCopy.traverseTree(deepcopy(cv.start))

		# Double check to make sure this is actually still an augassign
		if hasattr(spot, "global_id") and \
			type(findId(newTree, spot.global_id)) == ast.AugAssign:
			newCv = cv.deepcopy()
			newCv.path = cv.path[i+1:]
			newCv.oldSubtree = spot
			# find the new spot
			cvCopy = cv.deepcopy()
			cvCopy.path = cv.path[i:]
			newSpot = cvCopy.traverseTree(newTree)
			newCv.newSubtree = newSpot
			return newCv
	return cv

def conditionalSpecialFunction(cv, orig):
	if isinstance(cv, MoveVector):
		# check to see if you're moving values that used to be in conditionals
		cvCopy = cv.deepcopy()
		cvCopy.path = cvCopy.path[1:]
		oldSpot = cvCopy.traverseTree(deepcopy(cv.start))
		if hasattr(oldSpot, "combinedConditional"):
			# replace the move with a change that just changes the whole conditional tree
			cvCopy2 = cv.deepcopy()
			newTree = cvCopy2.applyChange()
			newSpot = cvCopy.traverseTree(newTree)
			newCv = ChangeVector(cvCopy.path[1:], oldSpot, newSpot, start=cv.start)
			return newCv
	if hasattr(cv.oldSubtree, "combinedConditionalOp"):
		# We need to move up higher in the tree
		if (type(cv.oldSubtree) == ast.Or and type(cv.newSubtree) == ast.And) or \
		   (type(cv.oldSubtree) == ast.And and type(cv.newSubtree) == ast.Or):
			cv.path = cv.path[1:]
			origCopy = cv.deepcopy()
			oldSpot = origCopy.traverseTree(deepcopy(orig))
			cvCopy = cv.deepcopy()
			newSpot = cvCopy.traverseTree(deepcopy(cv.start))
			if type(newSpot) == ast.BoolOp:
				newSpot.op = cv.newSubtree
			elif type(newSpot) == ast.If: # well, it is a combined conditional
				if type(newSpot.test) == ast.BoolOp:
					newSpot.test.op = cv.newSubtree
				else:
					log("Individualize\tconditionalSpecialFunction\tUnexpected Conditional Spot: " + repr(newSpot.test), filename="bug")		
			else:
				log("Individualize\tconditionalSpecialFunction\tUnexpected Spot: " + repr(newSpot), filename="bug")
			cv.oldSubtree, cv.newSubtree = oldSpot, newSpot
		else:
			log("Individualize\tconditionalSpecialFunction\tUnexpected types: " + str(type(cv.oldSubtree)) + "," + str(type(cv.newSubtree)), "bug")
	elif hasattr(cv.oldSubtree, "combinedConditional"):
		# tree must be a boolean operation combining multiple conditionals
		treeTests = cv.oldSubtree.values
		treeStmts = []
		for test in treeTests:
			tmpCv = ChangeVector(generatePathToId(orig, test.global_id), 0, 1)
			treeStmts.append(tmpCv.traverseTree(orig))
		iToKeep = -1
		for i in range(len(treeStmts)):
			if compareASTs(treeStmts[i], cv.newSubtree, checkEquality=True) == 0:
				iToKeep = i
				break
		newCV = []
		if iToKeep != -1:
			# if possible, just delete unwanted conditionals while keeping the one we want
			for i in range(len(treeStmts)):
				if i != iToKeep:
					tmp = DeleteVector(generatePathToId(orig, treeStmts[i].global_id), treeStmts[i], None, start=orig)
					newCV.append(tmp)
		else:
			# otherwise, edit the topmost conditional's test and delete the others
			newCV.append(ChangeVector(generatePathToId(orig, treeStmts[0].test.global_id), treeStmts[i].test, cv.newSubtree, start=orig))
			for i in range(1, len(treeStmts)):
				tmp = DeleteVector(generatePathToId(orig, treeStmts[i].global_id), treeStmts[i], None, start=orig)
				newCV.append(tmp)
		if len(newCV) == 1:
			return newCV[0]
		else:
			return newCV
	return cv

def mapEdit(canon, orig, edit, nameMap=None):
	if edit == None:
		return
	if nameMap == None:
		nameMap = createNameMap(canon)
	count = 0
	updatedOrig = deepcopy(orig)
	replacedVariables = []
	alreadyEdited = []
	while count < len(edit):
		cv = edit[count]
		startingTree = cv.start
		startingPath = cv.path

		cv = basicTypeSpecialFunction(cv)
		cv.oldSubtree = mapNames(cv.oldSubtree, nameMap)
		cv.newSubtree = mapNames(cv.newSubtree, nameMap)

		# First, apply the complex special functions
		# Sometimes we've already edited the given old subtree (like with multi-conditionals). If so, skip this step.
		if hasattr(cv.oldSubtree, "global_id") and cv.oldSubtree.global_id in alreadyEdited:
			del edit[count]
			continue
		cv = propagatedVariableSpecialFunction(cv, replacedVariables)
		cv = helperFoldingSpecialFunction(cv, updatedOrig)
		cv = noneSpecialFunction(cv)
		cv = augAssignSpecialFunction(cv, updatedOrig)
		cv = multiCompSpecialFunction(cv, updatedOrig, canon)
		if type(cv) == list:
			edit = edit[:count] + cv + edit[count+1:]
			continue
		cv = conditionalSpecialFunction(cv, updatedOrig)
		if type(cv) == list:
			edit = edit[:count] + cv + edit[count+1:]
			continue
		# Apply other special functions that need less data
		if isinstance(cv, SubVector): # for subvectors, we can grab the new tree from the old
			(parent, pos, partialNew) = getSubtreeContext(cv.newSubtree, cv.oldSubtree)
			# Since they're exactly equal, see if we can do a clean copy
			if hasattr(cv.oldSubtree, "global_id"):
				cv.oldSubtree = findId(updatedOrig, cv.oldSubtree.global_id)
				if type(pos) == int:
					parent[pos] = deepcopy(cv.oldSubtree)
				else:
					setattr(parent, pos, deepcopy(cv.oldSubtree))
			# Otherwise, apply special functions by hand
			else:
				(cv.oldSubtree, partialNew) = specialFunctions(cv.oldSubtree, partialNew)
				if type(pos) == int:
					parent[pos] = partialNew
				else:
					setattr(parent, pos, partialNew)
		else:
			(cv.oldSubtree, cv.newSubtree) = specialFunctions(cv.oldSubtree, cv.newSubtree)

		if hasattr(cv.oldSubtree, "variableGlobalId") and cv.oldSubtree.variableGlobalId not in replacedVariables:
			# replace with the original variable
			newOldTree = findId(updatedOrig, cv.oldSubtree.variableGlobalId)
			if newOldTree != None:
				replacedVariables.append(cv.oldSubtree.variableGlobalId)
				cv.oldSubtree = newOldTree
				cv.newSubtree.global_id = cv.oldSubtree.global_id # remap the location for future changes
				if hasattr(cv.newSubtree, "loadedVariable"):
					delattr(cv.newSubtree, "loadedVariable")
				if hasattr(cv.newSubtree, "variableGlobalId"):
					delattr(cv.newSubtree, "variableGlobalId")
			else:
				log("Individualize\tcouldn't find variable in original: " + printFunction(cv.oldSubtree, 0) + \
						  "\t" + printFunction(cv.start, 0) + "\t" + printFunction(updatedOrig, 0), "bug")

		# Next, update the starting tree
		if isinstance(cv, SwapVector):
			(oldSwap, newSwap) = cv.getSwapees()
			cv.start = updatedOrig
			cv.oldPath = generatePathToId(updatedOrig, oldSwap.global_id)
			cv.newPath = generatePathToId(updatedOrig, newSwap.global_id)
			cv.oldSubtree = oldSwap
			cv.newSubtree = newSwap
		elif hasattr(cv.oldSubtree, "global_id") and cv.oldSubtree.global_id != None:
			# If you can, just use the original tree and update the path
			oldStart = cv.start
			cv.start = updatedOrig
			if hasattr(cv.oldSubtree, "variableGlobalId"):
				tmpPath = generatePathToId(cv.start, cv.oldSubtree.global_id, cv.oldSubtree.variableGlobalId)
			else:
				tmpPath = generatePathToId(cv.start, cv.oldSubtree.global_id)
			if tmpPath != None:
				cv.path = tmpPath
			else:
				log("Individualize\tno path 1\t" + str(cv) + "\n" + str(edit) + "\n" + \
							printFunction(cv.start, 0) + "\n" + \
							printFunction(oldStart, 0), "bug")
		else:
			# Otherwise, move up the path 'til you find a global id to use
			origPath = cv.path[:]
			spot = cv.traverseTree(cv.start)
			startPath = [cv.path[0]]
			while not hasattr(spot, "global_id") or spot.global_id == None:
				if len(cv.path) == 1:
					cv.path = origPath
					break
				cv.path = cv.path[1:]
				startPath.append(cv.path[0])
				spot = cv.traverseTree(cv.start)
			if hasattr(spot, "global_id") and spot.global_id != None:
				if hasattr(spot, "variableGlobalId"):
					# find the right variable spot
					path = generatePathToId(updatedOrig, spot.global_id, spot.variableGlobalId)
				else:
					path = generatePathToId(updatedOrig, spot.global_id) # get the REAL path to this point
				if path == None:
					log("Individualize\tno path 1.5\t" + str(cv) + "\t" + str(origPath) + "\n" + printFunction(spot) + "\n" + printFunction(cv.start), "bug")
				# Don't change addvectors!
				if (not isinstance(cv, AddVector)): # need to do a changevector at this location
					cvCopy = cv.deepcopy()
					cvCopy.path = [0] + path
					newSpot = cvCopy.traverseTree(updatedOrig) # wait, how does this work?!
					if type(spot) != type(newSpot):
						cv = ChangeVector(path, spot, newSpot, start=updatedOrig)
					else:
						cv.start = updatedOrig
						cv.path = startPath + path
				else:
					cv.start = updatedOrig
					cv.path = startPath + path
			else:
				log("Individualize\tno path 2\t" + str(cv) + "\t" + printFunction(cv.start, 0), "bug")

		if isinstance(cv, DeleteVector):
			while len(cv.path) > 0 and type(cv.path[0]) != int: # we can only remove things from lists
				cvCopy = cv.deepcopy()
				cv.path = cvCopy.path = cvCopy.path[1:]
				spot = cvCopy.traverseTree(deepcopy(updatedOrig))
				cv.oldSubtree = spot
			if len(cv.path) == 0:
				log("Individualize\tdelete vector couldn't find path" + str(cv), "bug")

		# Catch any ordering changes that won't need to be propogated to the edit in the old tree
		if hasattr(cv.oldSubtree, "global_id"):
			cv.oldSubtree = findId(updatedOrig, cv.oldSubtree.global_id)

		# Finally, check some things that may get broken by inidividualization
		cv = multiCompAfterSpecialFunction(cv, startingTree, startingPath)
		cv.oldSubtree = mapNames(cv.oldSubtree, nameMap) #remap the names, just in case
		cv.newSubtree = mapNames(cv.newSubtree, nameMap)
		# Sometimes these simplifications result in an opportunity for better change vectors
		if cv.isReplaceVector() and type(cv.oldSubtree) == type(cv.newSubtree):
			# But we don't want to undo the work from before! That will lead to infinite loops.
			if type(cv.oldSubtree) in [ast.NameConstant, ast.Bytes, ast.Str, ast.Num, ast.Name, int, str]:
				pass
			elif type(cv.oldSubtree) == ast.Return and (cv.oldSubtree.value == None or type(cv.oldSubtree.value) == ast.Name):
				pass
			elif type(cv.oldSubtree) == ast.Compare and len(cv.oldSubtree.ops) != len(cv.newSubtree.ops):
				pass
			elif type(cv.oldSubtree) == ast.Slice:
				pass
			else:
				removePropertyFromAll(cv.oldSubtree, "treeWeight")
				removePropertyFromAll(cv.newSubtree, "treeWeight")
				newChanges = diffAsts.getChanges(cv.oldSubtree, cv.newSubtree) # update the changes, then individualize again
				if len(newChanges) > 1 and type(cv.oldSubtree) == ast.If:
					pass # just in case this is a combined conditional, we don't want to mess it up!
				else:
					for change in newChanges:
						change.path = change.path + cv.path
					newChanges, _ = generateNextStates.updateChangeVectors(newChanges, cv.start, cv.start)
					edit[count:count+1] = newChanges
					continue # don't increment count
		edit[count] = cv
		if not (isinstance(cv, AddVector) or isinstance(cv, DeleteVector) or isinstance(cv, SubVector) or isinstance(cv, SuperVector) or isinstance(cv, SwapVector) or isinstance(cv, MoveVector)) and hasattr(cv.oldSubtree, "global_id"):
			alreadyEdited.append(cv.oldSubtree.global_id)
		updatedOrig = edit[count].applyChange()
		count += 1

	# In case any of our edits have gotten cancelled out, delete them.
	i = 0
	while i < len(edit):
		if compareASTs(edit[i].oldSubtree, edit[i].newSubtree, checkEquality=True) == 0:
			edit.pop(i)
		else:
			i += 1
	return edit
