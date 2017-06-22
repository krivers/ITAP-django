import ast, copy
from ..path_construction import diffAsts, generateNextStates
from ..ChangeVector import *
from ..astTools import negate, num_negate, isAnonVariable, removePropertyFromAll, transferMetaData, isStatement, compareASTs
from ..path_construction import generateNextStates
from ..canonicalize import simplify_multicomp
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
	""" Includes the AST itself"""
	if hasattr(a, tag):
		return True
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
def specialFunctions(cv, old, new):
	if type(old) == type(new) == list:
		log("individualize\tspecialFunctions\tWhy are we comparing lists?: " + str(cv) + ";" + printFunction(old) + ";" + printFunction(new), "bug")
		return cv
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

	if hasattr(old, "num_negated") and old.num_negated:
		origNew = deepcopy(new)
		(old, new) = (num_negate(old), num_negate(new))
		if new == None: # couldn't reverse the new operator
			# To get here, we must have a binary operator. Go up a level and negate the right side
			cvCopy = cv.deepcopy()
			parentSpot = deepcopy(cvCopy.traverseTree(cvCopy.start))
			if type(parentSpot) == ast.BinOp:
				cvCopy.path = cvCopy.path[1:]
				cvCopy.oldSubtree = parentSpot
				cvCopy.newSubtree = deepcopy(parentSpot)
				cvCopy.newSubtree.op = origNew
				cvCopy.newSubtree.right = num_negate(cvCopy.newSubtree.right)
				cvCopy = orderedBinOpSpecialFunction(cvCopy) # just in case
				return cvCopy
			else:
				log("individualize\tspecialFunctions\tWhere are we? " + str(type(parentSpot)), "bug")

	#if (hasattr(old, "inverted") and old.inverted):
	#	(old, new) = (invert(old), invert(new))
	cv.oldSubtree = old
	cv.newSubtree = new
	return cv

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
		else:
			if isAnonVariable(a.name): # if it's a variable that won't be getting mapped
				# How many new vars are there already?
				num = countNewVarsInD(d)
				d[a.name] = "new_var_" + str(num)
				a.name = d[a.name]
				a.alreadyMapped = True
	elif type(a) == ast.arg:
		if not hasattr(a, "alreadyMapped"):
			if a.arg in d:
				a.arg = d[a.arg]
				a.alreadyMapped = True
			else:
				if isAnonVariable(a.arg): # if it's a variable that won't be getting mapped
					# How many new vars are there already?
					num = countNewVarsInD(d)
					d[a.arg] = "new_var_" + str(num)
					a.arg = d[a.arg]
					a.alreadyMapped = True
		return a
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
	if type(a) == ast.Module: # Need to go through the functions backwards to make this right
		for i in range(len(a.body) - 1, -1, -1):
			createNameMap(a.body[i], d)
		return d
	if type(a) in [ast.FunctionDef, ast.ClassDef]:
		if hasattr(a, "originalId") and a.name not in d:
			d[a.name] = a.originalId
	elif type(a) == ast.arg:
		if hasattr(a, "originalId") and a.arg not in d:
			d[a.arg] = a.originalId
		return d
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
	if type(a) == list:
		for child in a:
			tmp = findId(child, id)
			if tmp != None:
				return tmp
		return None
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
	if (cv.path[0] in [('n', 'Number'), ('s', 'String'), ('id', 'Name'), ('arg', 'Argument'), 
						('value', 'Name Constant'), ('s', 'Bytes'), ('name', 'Alias')]):
		cvCopy = cv.deepcopy()
		cv.oldSubtree = deepcopy(cvCopy.traverseTree(cv.start))
		if cv.path[0] == ('n', 'Number'):
			cv.newSubtree = ast.Num(cv.newSubtree)
		elif cv.path[0] == ('s', 'String'):
			cv.newSubtree = ast.Str(cv.newSubtree)
		elif cv.path[0] == ('id', 'Name'):
			cv.newSubtree = ast.Name(cv.newSubtree, cv.oldSubtree.ctx)
		elif cv.path[0] == ('arg', 'Argument'):
			cv.newSubtree = ast.arg(cv.newSubtree, cv.oldSubtree.annotation)
		elif cv.path[0] == ('value', 'Name Constant'):
			cv.newSubtree = ast.NameConstant(cv.newSubtree)
		elif cv.path[0] == ('s', 'Bytes'):
			cv.newSubtree = ast.Bytes(cv.newSubtree)
		elif cv.path[0] == ('name', 'Alias'):
			cv.newSubtree = ast.alias(cv.newSubtree, cv.oldSubtree.asname)
		cv.path = cv.path[1:]
	return cv

def propagatedVariableSpecialFunction(cv, replacedVariables):
	if hasattr(cv.oldSubtree, "propagatedVariable"):
		# need to move up in the tree until we hit the initial variable assigned
		cvCopy = cv.deepcopy()
		newTree = cvCopy.applyChange(caller="propagatedVariableSpecialFunction")
		oldSpot = cvCopy.oldSubtree
		newSpot = cvCopy.newSubtree
		cvCopy.path = [-1] + cvCopy.path
		while type(oldSpot) == list or (not hasattr(oldSpot, "loadedVariable") and hasattr(oldSpot, "propagatedVariable")):
			cvCopy = cvCopy.deepcopy()
			cvCopy.path = cvCopy.path[1:]
			oldSpot = deepcopy(cvCopy.traverseTree(cvCopy.start))
			newSpot = deepcopy(cvCopy.traverseTree(newTree))
		if hasattr(oldSpot, "loadedVariable") and oldSpot.variableGlobalId not in replacedVariables:
			return ChangeVector(cvCopy.path[1:], oldSpot, newSpot, start=cvCopy.start)
		elif hasattr(oldSpot, "loadedVariable"):
			pass
		else:
			log("Individualize\tCouldn't move up to a ChangeVector: " + printFunction(oldSpot, 0) + " - " + printFunction(newSpot, 0), "bug")
	return cv

def helperFoldingSpecialFunction(cv, edit, orig):
	if hasattr(cv.oldSubtree, "helperVar") or hasattr(cv.oldSubtree, "helperReturnVal") or \
		hasattr(cv.oldSubtree, "helperParamAssign") or hasattr(cv.oldSubtree, "helperReturnAssn"):
		log("Oh no! helper function!" + "\n" + str(cv) + "\n" + str(edit) + "\n" + \
					printFunction(cv.start, 0) + "\n" + \
					printFunction(orig, 0), "bug")
	return cv

def noneSpecialFunction(cv):
	"""If the old type is 'None' (which won't show up in the original), move up in the AST to get the metadata"""
	if (not isinstance(cv, AddVector)) and cv.oldSubtree == None:
		cvCopy = cv.deepcopy()
		if cv.path[0] == ('value', 'Return'):
			cv.oldSubtree = deepcopy(cvCopy.traverseTree(cv.start))
			cv.newSubtree = ast.Return(cv.newSubtree)
			cv.path = cv.path[1:]
		elif cv.path[0] == ('value', 'Name Constant'):
			cv.oldSubtree = deepcopy(cvCopy.traverseTree(cv.start))
			cv.newSubtree = ast.NameConstant(cv.newSubtree)
			cv.path = cv.path[1:]
		elif cv.path[0] in [('lower', 'Slice'), ('upper', 'Slice'), ('step', 'Slice')]:
			tmpNew = cv.newSubtree
			cvCopy = cv.deepcopy()
			cv.oldSubtree = deepcopy(cvCopy.traverseTree(cv.start))
			cv.newSubtree = deepcopy(cv.oldSubtree) # use the same slice
			if cv.path[0][0] == 'lower':
				cv.newSubtree.lower = tmpNew
			elif cv.path[0][0] == 'upper':
				cv.newSubtree.upper = tmpNew
			else:
				cv.newSubtree.step = tmpNew
			cv.path = cv.path[1:] # get rid of None and the val
		else:
			log("Individualize\tmapEdit\tMissing option in None special case 1: " + str(cv.path[0]), "bug")
	elif cv.oldSubtree == "None":
		cv.path = cv.path[1:] # get rid of None and the id
		cvCopy = cv.deepcopy()
		cv.oldSubtree = deepcopy(cvCopy.traverseTree(cv.start))
		if cv.path[0] == ('value', 'Return'):
			cv.newSubtree = ast.Return(ast.Name(cv.newSubtree, ast.Load()))
		else:
			log("Individualize\tmapEdit\tMissing option in None special case 2: " + str(cv.path[0]), "bug")
		cv.path = cv.path[1:]
	return cv

def hasMultiComp(a):
	if not isinstance(a, ast.AST):
		return False
	for node in ast.walk(a):
		if hasattr(node, "multiComp") and node.multiComp:
			return True
	return False

def multiCompSpecialFunction(cv, orig, canon, edit):
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
		oldSpot = deepcopy(cvCopy.traverseTree(cv.start))
		cvCopy = cv.deepcopy()
		if hasattr(oldSpot, "global_id"):
			cvCopy.path = generatePathToId(orig, oldSpot.global_id)
		else:
			# We need to split up the multicomp
			while not hasattr(oldSpot, "global_id"):
				cvCopy.path = cvCopy.path[1:]
				oldSpot = deepcopy(cvCopy.traverseTree(cv.start))
			treeResult = cv.applyChange(caller="multiCompSpecialFunction 0")
			newSpot = deepcopy(cvCopy.traverseTree(treeResult))
			newCv = ChangeVector(cvCopy.path[1:], oldSpot, newSpot, start=orig)
			newCv.path = generatePathToId(orig, oldSpot.global_id)[1:]
			newCv.oldSubtree = deepcopy(newCv.traverseTree(orig))
			newCv.path = newCv.path[1:]
			log("individualize\tmultiCompSpecialFunction\tUpdated CV: " + \
				str(cv) + "\n" + str(newCv) + "\n" + printFunction(cv.start) + "\n" + printFunction(orig), "bug")
			return newCv
		if cvCopy.path != None:
			cvCopy.path = [-1] + cvCopy.path # The None,None is to force the traversal to go all the way to the node we want, instead of its parent
			newSpot = deepcopy(cvCopy.traverseTree(orig))
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
			cv = SubVector(cvCopy.path, newSpot, ast.BoolOp(ast.And(), [newSpot, cv.newSubtree], newly_added=True), cv.start)
			return cv
	elif isinstance(cv, DeleteVector) and hasattr(cv.oldSubtree, "multiCompPart") and type(cv.oldSubtree) == ast.Compare:
		# We can't just delete this, but we can take out this link in the operation by splitting the multi-comp in two
		cvCopy = cv.deepcopy()
		cvCopy.path = cvCopy.path[1:]
		oldSpot = deepcopy(cvCopy.traverseTree(cv.start))
		cvCopy = cv.deepcopy()
		parentPath = generatePathToId(orig, oldSpot.global_id)
		if parentPath != None:
			cvCopy.path = [-1] + parentPath # The None,None is to force the traversal to go all the way to the node we want, instead of its parent
			origSpot = deepcopy(cvCopy.traverseTree(orig))
			# find which op we need to cut
			if type(origSpot) != ast.BoolOp:
				newPath = generatePathToId(orig, cv.oldSubtree.ops[0].global_id)
				if newPath != None:
					deletedPos = newPath[0] # the index into the list of ops
					leftOps = origSpot.ops[:deletedPos]
					leftValues = [origSpot.left] + origSpot.comparators[:deletedPos]
					rightOps = origSpot.ops[deletedPos+1:]
					rightValues = origSpot.comparators[deletedPos:]
					if len(leftOps) == 0:
						newCompare = ast.Compare(rightValues[0], rightOps, rightValues[1:], newly_added=True)
						return ChangeVector(parentPath, origSpot, newCompare, start=orig)
					elif len(rightOps) == 0:
						newCompare = ast.Compare(leftValues[0], leftOps, leftValues[1:], newly_added=True)
						return ChangeVector(parentPath, origSpot, newCompare, start=orig)
					else:
						# combine the two with And
						leftCompare = ast.Compare(leftValues[0], leftOps, leftValues[1:])
						rightCompare = ast.Compare(rightValues[0], rightOps, rightValues[1:])
						newResult = ast.BoolOp(ast.And(), [leftCompare, rightCompare], newly_added=True)
						return ChangeVector(parentPath, origSpot, newResult, start=orig)
				else:
					log("individualize\tmultiComp\tWhere's the op path: " + str(newPath), "bug")
			else:
				log("individualize\tmultiComp\tNon-bool op: \n" + printFunction(cv.start) + "\n" + str(type(origSpot)) + ": " + printFunction(origSpot), "bug")
		else:
			log("individualize\tmultiComp\tWhere's the parent path: " + str(parentPath), "bug")
	# Catch other multi-comp problems
	if hasattr(cv.oldSubtree, "multiCompOp") and cv.oldSubtree.multiCompOp:
		# Changing the operator
		cvCopy = cv.deepcopy()
		oldSpot = deepcopy(cv.traverseTree(canon))
		treeResult = cvCopy.applyChange(caller="multiCompSpecialFunction 1")
		newSpot = deepcopy(cvCopy.traverseTree(treeResult))
		cv = ChangeVector(cvCopy.path, oldSpot, ast.BoolOp(cv.newSubtree, [newSpot], newly_added=True), cv.start)
		return cv
	if (cv.oldSubtree == None or not hasattr(cv.oldSubtree, "global_id")) and hasMultiComp(canon):
		spot = None
		i = 0
		pathLength = len(cv.path)
		while i < pathLength:
			cvCopy = cv.deepcopy()
			cvCopy.path = cvCopy.path[i:]
			oldSpot = deepcopy(cvCopy.traverseTree(cv.start))
			if hasattr(oldSpot, "multiComp") and oldSpot.multiComp == True:
				break
			i += 1
		if i < pathLength:
			cvCopy = cv.deepcopy()
			cvCopy.path = [(None,None)] + generatePathToId(orig, oldSpot.global_id) # The None,None is to force the traversal to go all the way to the node we want, instead of its parent
			newSpot = deepcopy(cvCopy.traverseTree(orig))
			cvCopy.path = cvCopy.path[1:] # then get rid of the None, None
			if type(newSpot) == ast.Compare: # DON'T CHANGE IT OTHERWISE
				# Otherwise, we need to put back in the boolean operation
				cv = SubVector(cvCopy.path, newSpot, ast.BoolOp(ast.And(), [newSpot, cv.newSubtree], newly_added=True), cv.start)
				return cv
	if (hasattr(cv.oldSubtree, "multiCompMiddle") and cv.oldSubtree.multiCompMiddle) or \
		(hasattr(cv.oldSubtree, "multiCompPart") and cv.oldSubtree.multiCompPart):
		spot = None
		i = 0
		pathLength = len(cv.path)
		while i < pathLength:
			cvCopy = cv.deepcopy()
			cvCopy.path = cvCopy.path[i:]
			spot = deepcopy(cvCopy.traverseTree(cv.start))
			if hasattr(spot, "multiComp") and spot.multiComp == True:
				break
			i += 1
		# Double check to make sure this is actually still an multicomp
		if i < pathLength and hasattr(spot, "global_id") and \
			type(findId(orig, spot.global_id)) == ast.Compare and \
			len(findId(orig, spot.global_id).ops) > 1:
			oldCvCopy = cv.deepcopy()
			oldCvCopy.path = generatePathToId(orig, spot.global_id)
			oldSpot = deepcopy(oldCvCopy.traverseTree(orig))
			if type(oldCvCopy.path[0]) == int:
				oldSpot = oldSpot[oldCvCopy.path[0]]
			else:
				oldSpot = getattr(oldSpot, oldCvCopy.path[0][0])

			newCvCopy = cv.deepcopy()
			newTree = newCvCopy.applyChange(caller="multiCompSpecialFunction 2")
			newCvCopy.path = newCvCopy.path[i:]
			newSpot = newCvCopy.traverseTree(newTree)

			# Make a new CV that changes the whole thing
			cv = ChangeVector(oldCvCopy.path, oldSpot, newSpot, cv.start)
			cv.wasMoveVector = True
			return cv
	return cv

def movedLineAfterSpecialFunction(cv, startingTree, startingPath, orig):
	"""Sometimes, with Move Vectors, items that got combined are no longer combined. Fix this by moving up the tree."""
	if isinstance(cv, MoveVector):
		cvCopy = cv.deepcopy()
		origSpot = deepcopy(cvCopy.traverseTree(cv.start))
		if len(origSpot) <= cv.oldSubtree or len(origSpot) <= cv.newSubtree:
			cvCopy.path = startingPath[1:]
			parentSpot = deepcopy(cvCopy.traverseTree(startingTree))
			if type(parentSpot) == ast.BoolOp:
				# Change this to a ChangeVector at the parent's level
				newSpot = deepcopy(parentSpot)
				newSpot.values.insert(cv.newSubtree, newSpot.values[cv.oldSubtree])
				newSpot.values.pop(cv.oldSubtree + (0 if cv.oldSubtree < cv.newSubtree else 1)) # adjust for length change
				cv = ChangeVector(cv.path[2:], parentSpot, newSpot, cv.start)
				cv.wasMoveVector = True
				return cv
			elif cv.path[1][0] == 'body': # If we're in a set of statements
				lineToMove = parentSpot.body[cv.oldSubtree]
				# First, just delete this line
				if hasattr(lineToMove, "global_id"):
					path = generatePathToId(orig, lineToMove.global_id)
				else:
					log("Individualize\tmovedLineAfterSpecialFunction\tWhere is the global id? " + printFunction(lineToMove), "bug")
				firstEdit = DeleteVector(path, lineToMove, None, start=orig)
				# Then, add the line back in, but in the correct position
				newPath = [cv.newSubtree] + cv.path[1:]
				secondEdit = AddVector(newPath, None, lineToMove, start=cv.start)
				return [firstEdit, secondEdit]
			else:
				log("Individualize\tmapEdit\tMissing option in Move Vector special case: " + str(type(parentSpot)), "bug")
	return cv

def augAssignSpecialFunction(cv, orig):
	if (not isinstance(cv, DeleteVector)) and (not isStatement(cv.oldSubtree)) and \
		(childHasTag(cv.oldSubtree, "augAssignVal") or childHasTag(cv.oldSubtree, "augAssignBinOp")):
		# First, create the oldTree and newTree in full
		cvCopy = cv.deepcopy()
		cvCopy.start = deepcopy(cv.start)
		newTree = cvCopy.applyChange(caller="augAssignSpecialFunction")

		# This should be in an augassign, move up in the tree until we reach it.
		spot = cv.oldSubtree
		cvCopy = cv
		i = 0
		while type(spot) not in [ast.Assign, ast.AugAssign] and len(cvCopy.path) > i:
			i += 1
			cvCopy = cv.deepcopy()
			cvCopy.path = cv.path[i:]
			spot = deepcopy(cvCopy.traverseTree(cv.start))

		# Double check to make sure this is actually still an augassign
		if type(spot) in [ast.Assign, ast.AugAssign] and hasattr(spot, "global_id"):
			newCv = cv.deepcopy()
			newCv.path = cv.path[i+1:]
			newCv.oldSubtree = spot
			# find the new spot
			cvCopy = cv.deepcopy()
			cvCopy.path = cv.path[i:]
			newSpot = cvCopy.traverseTree(newTree)
			if type(newSpot) == type(spot):
				# Don't do special things when they aren't needed
				if type(newSpot) == ast.Assign:
					if compareASTs(newSpot.targets, spot.targets, checkEquality=True) == 0:
						# If the two have the same targets and are both binary operations with the target as the left value... 
						# just change the value
						if type(newSpot.value) == type(spot.value) == ast.BinOp:
							if compareASTs(spot.targets[0], spot.value.left, checkEquality=True) == 0 and \
								compareASTs(newSpot.targets[0], newSpot.value.left, checkEquality=True) == 0:
								# we just want to change the values
								return ChangeVector([("right", "Binary Operation"), ("value", "Assign")] + newCv.path, 
													spot.value.right, newSpot.value.right, newCv.start)
					elif compareASTs(newSpot.value, spot.value, checkEquality=True) == 0:
						return cv
					else:
						log("Assign", "bug")
				elif type(newSpot) == ast.AugAssign:
					diffCount = 0
					if compareASTs(newSpot.op, spot.op, checkEquality=True) != 0:
						diffCount += 1
					if compareASTs(newSpot.target, spot.target, checkEquality=True) != 0:
						diffCount += 1
					if compareASTs(newSpot.value, spot.value, checkEquality=True) != 0:
						diffCount += 1
					if diffCount == 1:
						return cv
					else:
						log("AugAssign: " + str(diffCount), "bug")
			else:
				log("Mismatched types: " + str(type(newSpot)) + "," + str(type(spot)), "bug")
			return ChangeVector(newCv.path, spot, newSpot, start=newCv.start)
	return cv

def conditionalSpecialFunction(cv, orig):
	if isinstance(cv, MoveVector):
		# check to see if you're moving values that used to be in conditionals
		cvCopy = cv.deepcopy()
		cvCopy.path = cvCopy.path[1:]
		combinedSpot = deepcopy(cvCopy.traverseTree(cv.start))
		if hasattr(combinedSpot, "combinedConditional"):
			# First, see if we can just find a single tree that corresponds to this in the original code
			cvCopy2 = cv.deepcopy()
			newTree = cvCopy2.applyChange(caller="conditionalSpecialFunction")
			if hasattr(combinedSpot, "global_id"): # we can find this in the original tree
				newSpot = cvCopy.traverseTree(newTree)
				newCv = ChangeVector(cvCopy.path[1:], combinedSpot, newSpot, start=cv.start)
				return newCv
			else:
				# replace the move with a change that just changes the whole conditional tree
				cvCopy.path = cvCopy.path[1:]
				oldSpot = deepcopy(cvCopy.traverseTree(cv.start))
				while type(oldSpot) != ast.If and len(cvCopy.path) > 0: # get up to the If level...
					cvCopy.path = cvCopy.path[1:]
					oldSpot = deepcopy(cvCopy.traverseTree(cv.start))
				if len(cvCopy.path) > 0:
					newSpot = cvCopy.traverseTree(newTree)
					newCv = ChangeVector(cvCopy.path[1:], oldSpot, newSpot, start=cv.start)
					newCv.wasMoveVector = True
					return newCv
				else:
					log("Individualize\tconditionalSpecialFunction\tCouldn't find Ifs in move: " + str(cv), "bug")
	elif isinstance(cv, DeleteVector):
		# check to see if you're deleting values that used to be in conditionals on their own
		cvCopy = cv.deepcopy()
		cvCopy.path = cvCopy.path[1:]
		oldSpot = deepcopy(cvCopy.traverseTree(cv.start))
		if hasattr(oldSpot, "combinedConditional"):
			origCv = cv.deepcopy()
			origCv.path = generatePathToId(orig, cv.oldSubtree.global_id)
			origParentSpot = deepcopy(origCv.traverseTree(orig))
			if type(origParentSpot) == ast.If:
				# We need to replace this if statement with its body
				if len(origParentSpot.orelse) == 0:
					if len(origParentSpot.body) == 1:
						newCv = ChangeVector(cv.path[1:], origParentSpot, origParentSpot.body[0], start=orig)
						return newCv
					else:
						log("Individualize\tconditionalSpecialFunction\tUnexpected multiline: " + str(cv), "bug")
				else:
					log("Individualize\tconditionalSpecialFunction\tUnexpected else: " + str(cv), "bug")
	elif isinstance(cv, AddVector):
		# check to see if you're adding a new value to a comparison operation that doesn't exist yet
		cvCopy = cv.deepcopy()
		cvCopy.path = cvCopy.path[1:]
		oldSpot = deepcopy(cvCopy.traverseTree(cv.start))
		if hasattr(oldSpot, "combinedConditional"):
			# replace the original value with a combined value. It's a Subvector!
			# Go up to the if statement, then grab its test in the orig
			origCv = cv.deepcopy()
			origCv.path = cv.path[2:] # I think...
			testSpot = deepcopy(origCv.traverseTree(orig))
			origSpot = testSpot.test
			if cv.path[0] == 0:
				values = [cv.newSubtree, origSpot]
			else:
				values = [origSpot, cv.newSubtree]
			if type(oldSpot) == ast.BoolOp:
				newOp = deepcopy(oldSpot.op)
				newCv = SubVector(cv.path[2:], origSpot, ast.BoolOp(newOp, values, newly_added=True), start=orig)
				return newCv
			else:
				log("combinedConditional\tOLD SPOT: " + str(printFunction(oldSpot)), "bug")
				return cv
	if hasattr(cv.oldSubtree, "combinedConditionalOp"):
		# We need to move up higher in the tree
		if (type(cv.oldSubtree) == ast.Or and type(cv.newSubtree) == ast.And) or \
		   (type(cv.oldSubtree) == ast.And and type(cv.newSubtree) == ast.Or):
			cv.path = cv.path[1:]
			origCopy = cv.deepcopy()
			oldSpot = deepcopy(origCopy.traverseTree(cv.start))
			cvCopy = cv.deepcopy()
			newSpot = deepcopy(cvCopy.traverseTree(cv.start))
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
	elif hasattr(cv.oldSubtree, "moved_line") and not hasattr(cv.oldSubtree, "already_moved"):
		if isinstance(cv, DeleteVector):
			# replace this with a ChangeVector, replacing the if statement with the return/assign
			oldPart = cv.oldSubtree
			cvCopy = cv.deepcopy()
			cvCopy.path = [-1] + generatePathToId(orig, cv.oldSubtree.moved_line)
			newPart = deepcopy(cvCopy.traverseTree(orig))
			newCv = ChangeVector(cv.path, oldPart, newPart, start=cv.start)
			return newCv
		# if it's a ChangeVector
		elif not (isinstance(cv, MoveVector) or isinstance(cv, SwapVector) or isinstance(cv, SubVector) or isinstance(cv, SuperVector)):
			# Add an AddVector for the moved line after the change
			cvCopy = cv.deepcopy()
			cvCopy.path = [-1] + generatePathToId(orig, cv.oldSubtree.moved_line)
			movedLine = deepcopy(cvCopy.traverseTree(orig))
			newPath = copy.deepcopy(cv.path)
			newPath[0] += 1 # move to the next line
			newCv = AddVector(newPath, None, movedLine, start=cv.start)
			cv.oldSubtree.already_moved = True
			return [cv, newCv]
		else:
			log("individualize\tconditionalSpecialFunctions\tMoved return line: " + str(cv), "bug")
	elif hasattr(cv.oldSubtree, "combinedConditional"):
		# First - can we just change the whole conditional?
		if cv.path[0] == ('test', 'If'):
			cvCopy = cv.deepcopy()
			cvCopy.path = cvCopy.path
			newWholeConditional = deepcopy(cvCopy.traverseTree(cvCopy.start))
			if type(newWholeConditional) == ast.If:
				oldWholeConditional = deepcopy(newWholeConditional)
				newWholeConditional.test = cv.newSubtree # change the test to be the new version
				newCv = ChangeVector(cv.path[1:], oldWholeConditional, newWholeConditional, start=cv.start)
				return newCv
			else:
				log("individualize\tcombinedConditional\tWeird type?\t" + str(type(newWholeConditional)), "bug")

		# tree must be a boolean operation combining multiple conditionals
		treeTests = cv.oldSubtree.values
		treeStmts = []
		for i in range(len(treeTests)):
			test = treeTests[i]
			tmpCv = ChangeVector(generatePathToId(orig, test.global_id)[1:], 0, 1)
			newTest = tmpCv.traverseTree(orig)
			treeStmts.append(newTest)
		iToKeep = -1
		for i in range(len(treeStmts)):
			if compareASTs(treeStmts[i], cv.newSubtree, checkEquality=True) == 0:
				iToKeep = i
				break
		newCV = []
		if iToKeep != -1:
			# if possible, just delete unwanted conditionals while keeping the one we want
			# TODO shouldn't this just be a replace or a super vector?
			for i in range(len(treeStmts)):
				if i != iToKeep:
					tmp = DeleteVector(generatePathToId(orig, treeStmts[i].global_id), treeStmts[i], None, start=orig)
					newCV.append(tmp)
		elif hasattr(treeStmts[0], "test"):
			# otherwise, edit the topmost conditional's test and delete the others
			newCV.append(ChangeVector(generatePathToId(orig, treeStmts[0].test.global_id), treeStmts[i].test, cv.newSubtree, start=orig))
			for i in range(1, len(treeStmts)):
				tmp = DeleteVector(generatePathToId(orig, treeStmts[i].global_id), treeStmts[i], None, start=orig)
				newCV.append(tmp)
		else:
			log("individualize\tconditionalSpecialFunctions\t\n" + str(cv), "bug")
			log("individualize\tconditionalSpecialFunctions\t\n" + printFunction(cv.start) + "\n" + printFunction(orig), "bug")
			for stmt in treeStmts:
				log("individualize\tconditionalSpecialFunctions\tWeird combined conditional: " + printFunction(stmt), "bug")
		if len(newCV) == 1:
			return newCV[0]
		else:
			return newCV
	return cv

def orderedBinOpSpecialFunction(cv):
	if hasattr(cv.oldSubtree, "orderedBinOp") and not hasattr(cv.oldSubtree, "global_id"):
		# Move up in the tree until we reach a binop that has a global id. We'll get there eventuall because the parent has one.
		cvCopy = cv.deepcopy()
		newTree = cvCopy.applyChange(caller="orderedBinOpSpecialFunction")
		cvCopy = cv.deepcopy()
		oldSpot = cvCopy.traverseTree(cv.start)
		while not hasattr(oldSpot, "global_id") and hasattr(oldSpot, "orderedBinOp"):
			cvCopy.path = cvCopy.path[1:]
			oldSpot = cvCopy.traverseTree(cv.start)
		if not hasattr(oldSpot, "global_id"):
			log("individualize\torderedBinOpSpecialFunction\tCan't find the global id: " + str(cv), "bug")
		else:
			newSpot = cvCopy.traverseTree(newTree)
			return ChangeVector(cvCopy.path, oldSpot, newSpot, start=cv.start)
	return cv

def mapEdit(canon, orig, edit, nameMap=None):
	if edit == None:
		return
	if nameMap == None:
		nameMap = createNameMap(canon)
	count = 0
	originalEdit = edit
	edit = copy.deepcopy(edit)
	updatedOrig = deepcopy(orig)
	replacedVariables = []
	alreadyEdited = []
	while count < len(edit):
		cv = edit[count]
		orig_cv = cv.deepcopy()
		startingTree = cv.start
		startingPath = cv.path
		cv = basicTypeSpecialFunction(cv)
		cv.oldSubtree = mapNames(cv.oldSubtree, nameMap)
		cv.newSubtree = mapNames(cv.newSubtree, nameMap)
		cv.start = mapNames(cv.start, nameMap) # makes checking things easier later on

		# First, apply the complex special functions
		# Sometimes we've already edited the given old subtree (like with multi-conditionals). If so, skip this step.
		if hasattr(cv.oldSubtree, "global_id") and cv.oldSubtree.global_id in alreadyEdited:
			del edit[count]
			continue
		elif hasattr(cv, "alreadyDone"):
			# Need to update the path and start tree
			cv.start = updatedOrig
			cv.path = generatePathToId(updatedOrig, cv.oldSubtree.global_id)
			edit[count] = cv
			updatedOrig = edit[count].applyChange(caller="mapEdit 1")
			count += 1
			continue
		cv = orderedBinOpSpecialFunction(cv)
		cv = propagatedVariableSpecialFunction(cv, replacedVariables)
		cv = helperFoldingSpecialFunction(cv, edit, updatedOrig)
		cv = noneSpecialFunction(cv)
		cv = augAssignSpecialFunction(cv, updatedOrig)
		cv = multiCompSpecialFunction(cv, updatedOrig, canon, edit)
		if type(cv) == list:
			edit = edit[:count] + cv + edit[count+1:]
			continue
		cv = conditionalSpecialFunction(cv, updatedOrig)
		if type(cv) == list:
			edit = edit[:count] + cv + edit[count+1:]
			continue
		# Apply other special functions that need less data
		if isinstance(cv, SubVector): # for subvectors, we can grab the new tree from the old
			context = getSubtreeContext(cv.newSubtree, cv.oldSubtree)
			if context == None:
				log("individualize\tgetSubtreeContext\tNone context: " + str(cv) + "\n" + printFunction(cv.start), "bug")
			else:
				(parent, pos, partialNew) = context
				# Since they're exactly equal, see if we can do a clean copy
				if hasattr(cv.oldSubtree, "global_id"):
					newOldTree = findId(updatedOrig, cv.oldSubtree.global_id)
					if newOldTree != None:
						cv.oldSubtree = newOldTree
						if type(pos) == int:
							parent[pos] = deepcopy(cv.oldSubtree)
						else:
							setattr(parent, pos, deepcopy(cv.oldSubtree))
					else:
						log("individualize\tmapEdit\tMissing SubVector globalId: " + str(cv) + "\n" + \
							printFunction(updatedOrig) + "\n" + printFunction(orig), "bug")
				# Otherwise, apply special functions by hand
				else:
					prev_new_subtree = cv.newSubtree
					cv = specialFunctions(cv, cv.oldSubtree, partialNew)
					if type(pos) == int:
						parent[pos] = cv.newSubtree
					else:
						setattr(parent, pos, cv.newSubtree)
					cv.newSubtree = prev_new_subtree
		else:
			cv = specialFunctions(cv, cv.oldSubtree, cv.newSubtree)

		if hasattr(cv.oldSubtree, "variableGlobalId") and cv.oldSubtree.variableGlobalId not in replacedVariables:
			# replace with the original variable
			newOldTree = findId(updatedOrig, cv.oldSubtree.variableGlobalId)
			if newOldTree != None:
				replacedVariables.append(cv.oldSubtree.variableGlobalId)
				cv.oldSubtree = newOldTree
				if cv.newSubtree != None:
					cv.newSubtree.global_id = cv.oldSubtree.global_id # remap the location for future changes
					if hasattr(cv.newSubtree, "loadedVariable"):
						delattr(cv.newSubtree, "loadedVariable")
					if hasattr(cv.newSubtree, "variableGlobalId"):
						delattr(cv.newSubtree, "variableGlobalId")
			else:
				log("Individualize\tcouldn't find variable in original: " + str(cv) + "\n" + str(edit) + "\n" + \
						  "\n" + printFunction(cv.start) + "\n" + printFunction(updatedOrig) + "\n" + printFunction(orig), "bug")

		if hasattr(cv.oldSubtree, "second_global_id"):
			# If we're changing a boolop, delete the second conditional.
			if type(cv.oldSubtree) == ast.If:
				cvCopy = cv.deepcopy()
				cvCopy.path = [-1] + generatePathToId(orig, cv.oldSubtree.second_global_id)
				secondSpot = deepcopy(cvCopy.traverseTree(orig))
				newCv = DeleteVector(cvCopy.path[1:], secondSpot, None, start=orig)
				newCv.alreadyDone = True
				edit[count:count+1] = [edit[count]] + [newCv]

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
				extra_s = "varGlobalId" if hasattr(cv.oldSubtree, "variableGlobalId") else "globalId"
				log("Individualize\tno path 1\t" + extra_s + "\t" + str(cv) + "\n" +
							"EDIT: " + str(edit) + "\n" + \
							"ORIGINAL EDIT: " + str(originalEdit) + "\n" + \
							"CANON START: " + printFunction(oldStart) + "\n" + \
							"ORIG START: " + printFunction(cv.start) + "\n" + \
							"ORIG ORIG: " + printFunction(orig), "bug")
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
					log("Individualize\tno path 1.5\t" + str(cv) + "\n" +
								"EDIT: " + str(edit) + "\n" + \
								"ORIGINAL EDIT: " + str(originalEdit) + "\n" + \
								"CANON START: " + printFunction(cv.start) + "\n" + \
								"ORIG START: " + printFunction(updatedOrig) + "\n" + \
								"ORIG ORIG: " + printFunction(orig), "bug")
					#log("Individualize\tno path 1.5\t" + str(cv) + "\t" + str(origPath) + "\n" + printFunction(spot) + "\n" + printFunction(cv.start), "bug")
				else:
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
				spot = deepcopy(cvCopy.traverseTree(updatedOrig))
				cv.oldSubtree = spot
			if len(cv.path) == 0:
				log("Individualize\tdelete vector couldn't find path" + str(cv), "bug")
			if cv.path[1] not in [('orelse', 'If'), ('orelse', 'For'), ('orelse', 'While'), 
								  ('elts', 'List'), ('args', 'Arguments'), ('args', 'Call'),
								  ('keywords', 'Call')]:
				cvCopy = cv.deepcopy()
				parent = cvCopy.traverseTree(cvCopy.start)
				if len(parent) < 2:
					if cv.path[1] in [('body', 'If'), ('body', 'For'), ('body', 'While')]:
						cv = ChangeVector(cv.path, cv.oldSubtree, ast.Pass(), start=cv.start)
					else:
						log("individualize\tmapEdit\tDelete CV: " + str(cv), "bug")

		# Catch any ordering changes that won't need to be propogated to the edit in the old tree
		if hasattr(cv.oldSubtree, "global_id"):
			newOldTree = findId(updatedOrig, cv.oldSubtree.global_id)
			if newOldTree != None:
				cv.oldSubtree = newOldTree
			else:
				log("individualize\tmapEdit\tCouldn't find globalId: " + str(cv) + "\n" + \
					printFunction(updatedOrig) + "\n" + printFunction(orig), "bug")
		elif cv.oldSubtree != None and not isinstance(cv, MoveVector) and not isinstance(cv, SwapVector):
			if cv.path[0] in [('name', 'Function Definition'), ('attr', 'Attribute')]:
				pass
			else:
				if isinstance(cv.oldSubtree, ast.AST):
					log("individualize\tmapEdit\tDict: " + str(cv.oldSubtree.__dict__), "bug")
				log("individualize\tmapEdit\tMissing global_id\nOriginal CV: " + str(orig_cv) + "\nNew CV: " + \
					str(cv) + "\nFull Edit: " + str(edit) + "\nUpdated function:\n" + printFunction(cv.start) + \
					"\nOriginal function:\n" + printFunction(orig), "bug")
				if hasattr(orig_cv.oldSubtree, "global_id"):
					log("individualize\tmapEdit\tGlobal ID existed before", "bug")

		# Finally, check some things that may get broken by inidividualization
		cv = movedLineAfterSpecialFunction(cv, startingTree, startingPath, updatedOrig)
		if type(cv) == list:
			edit = edit[:count] + cv + edit[count+1:]
			continue
		cv.oldSubtree = mapNames(cv.oldSubtree, nameMap) #remap the names, just in case
		cv.newSubtree = mapNames(cv.newSubtree, nameMap)
		# Sometimes these simplifications result in an opportunity for better change vectors
		if cv.isReplaceVector() and type(cv.oldSubtree) == type(cv.newSubtree):
			# But we don't want to undo the work from before! That will lead to infinite loops.
			if type(cv.oldSubtree) in [ast.NameConstant, ast.Bytes, ast.Str, ast.Num, ast.Name, ast.arg, ast.alias, int, str]:
				pass
			elif type(cv.oldSubtree) == ast.Return and (cv.oldSubtree.value == None or type(cv.oldSubtree.value) == ast.Name):
				pass
			elif type(cv.oldSubtree) == ast.Compare and len(cv.oldSubtree.ops) != len(cv.newSubtree.ops):
				pass
			elif type(cv.oldSubtree) == ast.Slice:
				pass
			elif hasattr(cv, "wasMoveVector"):
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
		elif cv.isReplaceVector() and type(cv.oldSubtree) == ast.Compare and type(cv.newSubtree) == ast.BoolOp and \
			compareASTs(simplify_multicomp(cv.oldSubtree), cv.newSubtree, checkEquality=True) == 0:
			# This isn't actually changing anything! Get rid of it.
			del edit[count]
			continue
		edit[count] = cv
		if cv.isReplaceVector() and hasattr(cv.oldSubtree, "global_id"):
			alreadyEdited.append(cv.oldSubtree.global_id)
		updatedOrig = edit[count].applyChange(caller="mapEdit 2")
		if updatedOrig == None:
			log("DELETING EDIT:" + str(edit[count]), "bug")
			del edit[count]
			continue
		count += 1

	# In case any of our edits have gotten cancelled out, delete them.
	i = 0
	while i < len(edit):
		if compareASTs(edit[i].oldSubtree, edit[i].newSubtree, checkEquality=True) == 0:
			edit.pop(i)
		else:
			i += 1
	return edit
