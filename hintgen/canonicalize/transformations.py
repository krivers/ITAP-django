import ast, copy, functools
from ..tools import log
from ..namesets import *
from ..astTools import *

### VARIABLE ANONYMIZATION ###

def updateVariableNames(a, varMap, scopeName, randomCounter):
	if not isinstance(a, ast.AST):
		return

	if type(a) in [ast.FunctionDef, ast.ClassDef]:
		if a.name in varMap:
			if not hasattr(a, "originalId"):
				a.originalId = a.name
			a.name = varMap[a.name]
		anonymizeStatementNames(a, varMap, "_" + a.name)
	elif type(a) == ast.arg:
		if a.arg not in varMap and not builtInName(a.arg):
			log("Can't assign to arg?", "bug")
		if a.arg in varMap:
			if not hasattr(a, "originalId"):
				a.originalId = a.arg
			if varMap[a.arg][0] == "r":
				a.randomVar = True # so we know it can crash
			if a.arg == varMap[a.arg]:
				# Check whether this is a given name
				if not isAnonVariable(varMap[a.arg]):
					a.dontChangeName = True
			a.arg = varMap[a.arg]
	elif type(a) == ast.Name:
		if a.id not in varMap and not builtInName(a.id):
			varMap[a.id] = "r" + str(randomCounter[0]) + scopeName
			randomCounter[0] += 1
		if a.id in varMap:
			if not hasattr(a, "originalId"):
				a.originalId = a.id
			if varMap[a.id][0] == "r":
				a.randomVar = True # so we know it can crash
			if a.id == varMap[a.id]:
				# Check whether this is a given name
				if not isAnonVariable(varMap[a.id]):
					a.dontChangeName = True
			a.id = varMap[a.id]
	else:
		for child in ast.iter_child_nodes(a):
			updateVariableNames(child, varMap, scopeName, randomCounter)

def gatherLocalScope(a, globalMap, scopeName, goBackwards=False):
	localMap = { }
	varLetter = "g" if type(a) == ast.Module else "v"
	paramCounter = 0
	localCounter = 0
	if type(a) == ast.FunctionDef:
		for param in a.args.args:
			if type(param) == ast.arg:
				if not builtInName(param.arg) and param.arg not in localMap and param.arg not in globalMap:
					localMap[param.arg] = "p" + str(paramCounter) + scopeName
					paramCounter += 1
			else:
				log("transformations\tanonymizeFunctionNames\tWeird parameter type: " + str(type(param)), "bug")
	if goBackwards:
		items = a.body[::-1] # go through this backwards to get the used function names
	else:
		items = a.body[:]
	# First, go through and create the globalMap
	while len(items) > 0:
		item = items[0]
		if type(item) in [ast.FunctionDef, ast.ClassDef]:
			if not builtInName(item.name) and item.name not in localMap and item.name not in globalMap:
				localMap[item.name] = "helper_" + varLetter + str(localCounter) + scopeName
				localCounter += 1
			else:
				item.dontChangeName = True

		# If there are any variables in this node, find and label them
		if type(item) in [	ast.Assign, ast.AugAssign, ast.For, ast.With, 
							ast.Lambda, ast.comprehension, ast.ExceptHandler]:
			assns = []
			if type(item) == ast.Assign:
				assns = item.targets
			elif type(item) == ast.AugAssign:
				assns = [item.target]
			elif type(item) == ast.For:
				assns = [item.target]
			elif type(item) == ast.With:
				if item.optional_vars != None:
					assns = [item.optional_vars]
			elif type(item) == ast.Lambda:
				assns = item.args.args
			elif type(item) == ast.comprehension:
				assns = [item.target]
			elif type(item) == ast.ExceptHandler:
				if item.name != None:
					assns = [item.name]

			for assn in assns:
				if type(assn) == ast.Name:
					if not builtInName(assn.id) and assn.id not in localMap and assn.id not in globalMap:
						localMap[assn.id] = varLetter + str(localCounter) + scopeName
						localCounter += 1

		if type(item) in [ast.For, ast.While, ast.If]:
			items += item.body + item.orelse
		elif type(item) in [ast.With, ast.ExceptHandler]:
			items += item.body
		elif type(item) == ast.Try:
			items += item.body + item.handlers + item.orelse + item.finalbody
		items = items[1:]
	return localMap

def anonymizeStatementNames(a, globalMap, scopeName, goBackwards=False):
	"""Gather the local variables, then update variable names in each line"""
	localMap = gatherLocalScope(a, globalMap, scopeName, goBackwards=goBackwards)
	varMap = { }
	varMap.update(globalMap)
	varMap.update(localMap)
	randomCounter = [0]
	functionsSeen = []
	if type(a) == ast.FunctionDef:
		for arg in a.args.args:
			updateVariableNames(arg, varMap, scopeName, randomCounter)
	for line in a.body:
		updateVariableNames(line, varMap, scopeName, randomCounter)

def anonymizeNames(a, namesToKeep):
	"""Anonymize all of variables/names that occur in the given AST"""
	"""If we run this on an anonymized AST, it will fix the names again to get rid of any gaps!"""
	if type(a) != ast.Module:
		return a
	globalMap = { }
	for var in namesToKeep:
		globalMap[var] = var
	anonymizeStatementNames(a, globalMap, "", goBackwards=True)
	return a

def propogateNameMetadata(a, namesToKeep):
	"""Propogates name metadata through a state. We assume that the names are all properly formatted"""
	if type(a) == list:
		for child in a:
			child = propogateNameMetadata(child, namesToKeep)
		return a
	elif not isinstance(a, ast.AST):
		return a
	if type(a) == ast.Name:
		if builtInName(a.id):
			pass
		elif a.id in namesToKeep:
			a.dontChangeName = True
		else:
			if not hasattr(a, "originalId"):
				a.originalId = a.id
			if not isAnonVariable(a.id):
				a.dontChangeName = True # it's a name we shouldn't mess with
	elif type(a) == ast.arg:
		if builtInName(a.arg):
			pass
		elif a.arg in namesToKeep:
			a.dontChangeName = True
		else:
			if not hasattr(a, "originalId"):
				a.originalId = a.arg
			if not isAnonVariable(a.arg):
				a.dontChangeName = True # it's a name we shouldn't mess with
	for child in ast.iter_child_nodes(a):
		child = propogateNameMetadata(child, namesToKeep)
	return a

### HELPER FOLDING ###

def findHelperFunction(a, helperId, helperCount):
	"""Finds the first helper function used in the ast"""
	if not isinstance(a, ast.AST):
		return None

	# Check all the children, so that we don't end up with a recursive problem
	for child in ast.iter_child_nodes(a):
		f = findHelperFunction(child, helperId, helperCount)
		if f != None:
			return f
	# Then check if this is the right call
	if type(a) == ast.Call:
		if type(a.func) == ast.Name and a.func.id == helperId:
			if helperCount[0] > 0:
				helperCount[0] -= 1
			else:
				return a
	return None

def individualizeVariables(a, variablePairs, idNum):
	"""Replace variable names with new individualized ones (for inlining methods)"""
	if not isinstance(a, ast.AST):
		return

	if type(a) == ast.Name:
		if a.id not in variablePairs and not builtInName(a.id):
			name = "_var_" + a.id + "_" + str(idNum[0])
			variablePairs[a.id] = name
		if a.id in variablePairs:
			a.id = variablePairs[a.id]
	# Override built-in names when they're assigned to.
	elif type(a) == ast.Assign and type(a.targets[0]) == ast.Name:
		if a.targets[0].id not in variablePairs:
			name = "_var_" + a.targets[0].id + "_" + str(idNum[0])
			variablePairs[a.targets[0].id] = name
	elif type(a) == ast.arguments:
		for arg in a.args:
			if type(arg) == ast.arg:
				name = "_arg_" + arg.arg + "_" + str(idNum[0])
				variablePairs[arg.arg] = name
				arg.arg = variablePairs[arg.arg]
		return
	elif type(a) == ast.Call:
		if type(a.func) == ast.Name:
			variablePairs[a.func.id] = a.func.id # save the function name!

	for child in ast.iter_child_nodes(a):
		individualizeVariables(child, variablePairs, idNum)

def replaceAst(a, old, new, shouldReplace):
	"""Replace the old value with the new one, but only once! That's what the shouldReplace variable is for."""
	if not isinstance(a, ast.AST) or not shouldReplace[0]:
		return a
	elif compareASTs(a, old, checkEquality=True) == 0:
		shouldReplace[0] = False
		return new
	return applyToChildren(a, lambda x: replaceAst(x, old, new, shouldReplace))

def mapHelper(a, helper, idNum):
	"""Map the helper function into this function, if it's used. idNum gives us the current id"""
	if type(a) in [ast.FunctionDef, ast.ClassDef]:
		a.body = mapHelper(a.body, helper, idNum)
	elif type(a) in [ast.For, ast.While, ast.If]:
		a.body = mapHelper(a.body, helper, idNum)
		a.orelse = mapHelper(a.orelse, helper, idNum)
	if type(a) != list:
		return a # we only deal with lists

	i = 0
	body = a
	while i < len(body):
		if type(body[i]) in [ast.FunctionDef, ast.ClassDef, ast.For, ast.While, ast.If]:
			body[i] = mapHelper(body[i], helper, idNum) # deal with blocks first
		# While we still need to replace a function being called
		helperCount = 0
		while countVariables(body[i], helper.name) > helperCount:
			callExpression = findHelperFunction(body[i], helper.name, [helperCount])
			if callExpression == None:
				break
			idNum[0] += 1
			variablePairs = {}

			# First, update the method's variables
			methodArgs = deepcopy(helper.args)
			individualizeVariables(methodArgs, variablePairs, idNum)
			methodLines = deepcopyList(helper.body)
			for j in range(len(methodLines)):
				individualizeVariables(methodLines[j], variablePairs, idNum)

			# Then, move each of the parameters into an assignment
			argLines = []
			badArgs = False
			for j in range(len(callExpression.args)):
				arg = methodArgs.args[j]
				value = callExpression.args[j]
				# If it only occurs once, and in the return statement..
				if countVariables(methodLines, arg.arg) == 1 and countVariables(methodLines[-1], arg.arg) == 1:
					var = ast.Name(arg.arg, ast.Load())
					transferMetaData(arg, var)
					methodLines[-1] = replaceAst(methodLines[-1], var, value, [True])
				elif couldCrash(value):
					badArgs = True
					break
				else:
					if type(arg) == ast.arg:
						var = ast.Name(arg.arg, ast.Store(), helperVar=True)
						transferMetaData(arg, var)
						varAssign = ast.Assign([var], value, global_id=arg.global_id, helperParamAssign=True)
						argLines.append(varAssign)
					else: # what other type would it be?
						log("transformations\tmapHelper\tWeird arg: " + str(type(arg)), "bug")
			if badArgs:
				helperCount += 1
				continue

			# Finally, carry over the final value into the correct position
			if countOccurances(helper, ast.Return) == 1:
				returnLine = [replaceAst(body[i], callExpression, methodLines[-1].value, [True])]
				methodLines.pop(-1)
			else:
				comp = compareASTs(body[i].value, callExpression, checkEquality=True) == 0
				if type(body[i]) == ast.Return and comp:
					# In the case of a return, we can return None, it's cool
					callVal = ast.NameConstant(None, helperReturnVal=True)
					transferMetaData(callExpression, callVal)
					returnVal = ast.Return(callVal, global_id=body[i].global_id, helperReturnAssign=True)
					returnLine = [returnVal]
				elif type(body[i]) == ast.Assign and comp:
					# Assigns can be assigned to None
					callVal = ast.NameConstant(None, helperReturnVal=True)
					transferMetaData(callExpression, callVal)
					assignVal = ast.Assign(body[i].targets, callVal, global_id=body[i].global_id, helperReturnAssign=True)
					returnLine = [assignVal]
				elif type(body[i]) == ast.Expr and comp:
					# Delete the line if it's by itself
					returnLine = []
				else:
					# Otherwise, what is going on?!?
					returnLine = []
					log("transformations\tmapHelper\tWeird removeCall: " + str(type(body[i])), "bug")
			#log("transformations\tmapHelper\tMapped helper function: " + helper.name, "bug")
			body[i:i+1] = argLines + methodLines + returnLine
		i += 1
	return a

def mapVariable(a, varId, assn):
	"""Map the variable assignment into the function, if it's needed"""
	if type(a) != ast.FunctionDef:
		return a

	for arg in a.args.args:
		if arg.arg == varId:
			return a # overriden by local variable
	for i in range(len(a.body)):
		line = a.body[i]
		if type(line) == ast.Assign:
			for target in line.targets:
				if type(target) == ast.Name and target.id == varId:
					break
				elif type(target) in [ast.Tuple, ast.List]:
					for elt in target.elts:
						if type(elt) == ast.Name and elt.id == varId:
							break
		if countVariables(line, varId) > 0:
			a.body[i:i+1] = [deepcopy(assn), line]
			break
	return a

def helperFolding(a, mainFun):
	"""When possible, fold the functions used in this module into their callers"""
	if type(a) != ast.Module:
		return a

	globalCounter = [0]
	body = a.body
	i = 0
	while i < len(body):
		item = body[i]
		if type(item) == ast.FunctionDef:
			if item.name != mainFun:
				# We only want non-recursive functions that have a single return which occurs at the end
				# Also, we don't want any functions with parameters that are changed during the function
				returnOccurs = countOccurances(item, ast.Return)
				if countVariables(item, item.name) == 0 and returnOccurs <= 1 and type(item.body[-1]) == ast.Return:
					allArgs = []
					for arg in item.args.args:
						allArgs.append(arg.arg)
					for tmpA in ast.walk(item):
						if type(tmpA) in [ast.Assign, ast.AugAssign]:
							allGood = True
							assignedIds = gatherAssignedVarIds(tmpA.targets if type(tmpA) == ast.Assign else [tmpA.target])
							for arg in allArgs:
								if arg in assignedIds:
									allGood = False
									break
							if not allGood:
								break
					else:
						for j in range(len(item.body)-1):
							if couldCrash(item.body[j]):
								break
						else:
							# If we satisfy these requirements, translate the body of the function into all functions that call it
							gone = True
							used = False
							for j in range(len(body)):
								if i != j and type(body[j]) == ast.FunctionDef:
									if countVariables(body[j], item.name) > 0:
										used = True
									mapHelper(body[j], item, globalCounter)
									if countVariables(body[j], item.name) > 0:
										gone = False
							if used and gone:
								body.pop(i)
								continue
		elif type(item) == ast.Assign:
			# Is it ever changed in the global area?
			if len(item.targets) == 1 and type(item.targets[0]) == ast.Name:
				if eventualType(item.value) in [int, float, bool, str]: # if it isn't mutable
					for j in range(i+1, len(body)):
						line = body[j]
						if type(line) == ast.FunctionDef:
							if countOccurances(line, ast.Global) > 0: # TODO: improve this
								break
							if item.targets[0].id in getAllAssignedVarIds(line):
								break
						else: # if in scope
							if countVariables(line, item.targets[0].id) > 0:
								break
					else:
						# Variable never appears again- we can map it!
						for j in range(i+1, len(body)):
							line = body[j]
							if type(line) == ast.FunctionDef:
								mapVariable(line, item.targets[0].id, item)
						body.pop(i)
						continue
		i += 1
	return a

### AST PREPARATION ###

def listNotEmpty(a):
	"""Determines that the iterable is NOT empty, if we can know that"""
	"""Used for For objects"""
	if not isinstance(a, ast.AST):
		return False
	if type(a) == ast.Call:
		if type(a.func) == ast.Name and a.func.id in ["range"]:
			if len(a.args) == 1: # range(x)
				return type(a.args[0]) == ast.Num and type(a.args[0].n) != complex and a.args[0].n > 0
			elif len(a.args) == 2: # range(start, x)
				if type(a.args[0]) == ast.Num and type(a.args[1]) == ast.Num and \
					type(a.args[0].n) != complex and type(a.args[1].n) != complex and \
					a.args[0].n < a.args[1].n:
					return True
				elif type(a.args[1]) == ast.BinOp and type(a.args[1].op) == ast.Add:
					if type(a.args[1].right) == ast.Num and type(a.args[1].right) != complex and a.args[1].right.n > 0 and \
						compareASTs(a.args[0], a.args[1].left, checkEquality=True) == 0:
						return True
					elif type(a.args[1].left) == ast.Num and type(a.args[1].left) != complex and a.args[1].left.n > 0 and \
						compareASTs(a.args[0], a.args[1].right, checkEquality=True) == 0:
						return True
	elif type(a) in [ast.List, ast.Tuple]:
		return len(a.elts) > 0
	elif type(a) == ast.Str:
		return len(a.s) > 0
	return False

def simplifyUpdateId(var, variableMap, idNum):
	"""Update the varID of a new variable"""
	if type(var) not in [ast.Name, ast.arg]:
		return var
	idVar = var.id if type(var) == ast.Name else var.arg
	if not hasattr(var, "varID"):
		if idVar in variableMap:
			var.varID = variableMap[idVar][1]
		else:
			var.varID = idNum[0]
			idNum[0] += 1

def simplify_multicomp(a):
	if type(a) == ast.Compare and len(a.ops) > 1:
		# Only do one comparator at a time. If we don't do this, things get messy!
		comps = [a.left] + a.comparators
		values = [ ]
		# Compare each of the pairs
		for i in range(len(a.ops)):
			if i > 0:
				# Label all nodes as middle parts so we can recognize them later
				assignPropertyToAll(comps[i], "multiCompMiddle")
			values.append(ast.Compare(comps[i], [a.ops[i]], [deepcopy(comps[i+1])], multiCompPart=True))
		# Combine comparisons with and operators
		boolOp = ast.And(multiCompOp=True)
		boolopVal = ast.BoolOp(boolOp, values, multiComp=True, global_id=a.global_id)
		return boolopVal
	return a

def simplify(a):
	"""This function simplifies the usual Python AST to make it usable by our functions."""
	if not isinstance(a, ast.AST):
		return a
	elif type(a) == ast.Assign:
		if len(a.targets) > 1:
			# Go through all targets and assign them on separate lines
			lines = [ast.Assign([a.targets[-1]], a.value, global_id=a.global_id)]
			for i in range(len(a.targets)-1, 0, -1):
				t = a.targets[i]
				if type(t) == ast.Name:
					loadedTarget = ast.Name(t.id, ast.Load())
				elif type(t) == ast.Subscript:
					loadedTarget = ast.Subscript(deepcopy(t.value), deepcopy(t.slice), ast.Load())
				elif type(t) == ast.Attribute:
					loadedTarget = ast.Attribute(deepcopy(t.value), t.attr, ast.Load())
				elif type(t) == ast.Tuple:
					loadedTarget = ast.Tuple(deepcopy(t.elts), ast.Load())
				elif type(t) == ast.List:
					loadedTarget = ast.List(deepcopy(t.elts), ast.Load())
				else:
					log("transformations\tsimplify\tOdd loadedTarget: " + str(type(t)), "bug")
				transferMetaData(t, loadedTarget)
				loadedTarget.global_id = t.global_id

				lines.append(ast.Assign([a.targets[i-1]], loadedTarget, global_id=a.global_id))
		else:
			lines = [a]

		i = 0
		while i < len(lines):
			# For each line, figure out type and varID
			lines[i].value = simplify(lines[i].value)
			t = lines[i].targets[0]
			if type(t) in [ast.Tuple, ast.List]:
				val = lines[i].value
				# If the items are being assigned separately, with no dependance on each other,
				# separate out the elements of the tuple
				if type(val) in [ast.Tuple, ast.List] and len(t.elts) == len(val.elts) and \
					allVariableNamesUsed(val) == []:
					listLines = []
					for j in range(len(t.elts)):
						assignVal = ast.Assign([t.elts[j]], val.elts[j], global_id = lines[i].global_id)
						listLines += simplify(assignVal)
					lines[i:i+1] = listLines
					i += len(listLines) - 1
			i += 1
		return lines
	elif type(a) == ast.AugAssign:
		# Turn all AugAssigns into Assigns
		a.target = simplify(a.target)
		if eventualType(a.target) not in [bool, int, str, float]:
			# Can't get rid of AugAssign, in case the += is different
			a.value = simplify(a.value)
			return a
		if type(a.target) == ast.Name:
			loadedTarget = ast.Name(a.target.id, ast.Load())
		elif type(a.target) == ast.Subscript:
			loadedTarget = ast.Subscript(deepcopy(a.target.value), deepcopy(a.target.slice), ast.Load())
		elif type(a.target) == ast.Attribute:
			loadedTarget = ast.Attribute(deepcopy(a.target.value), a.target.attr, ast.Load())
		elif type(a.target) == ast.Tuple:
			loadedTarget = ast.Tuple(deepcopy(a.target.elts), ast.Load())
		elif type(a.target) == ast.List:
			loadedTarget = ast.List(deepcopy(a.target.elts), ast.Load())
		else:
			log("transformations\tsimplify\tOdd AugAssign target: " + str(type(a.target)), "bug")
		transferMetaData(a.target, loadedTarget)
		loadedTarget.global_id = a.target.global_id
		a.target.augAssignVal = True # for later recognition
		loadedTarget.augAssignVal = True
		assignVal = ast.Assign([a.target], ast.BinOp(loadedTarget, a.op, a.value, augAssignBinOp=True), global_id=a.global_id)
		return simplify(assignVal)
	elif type(a) == ast.Compare and len(a.ops) > 1:
		return simplify(simplify_multicomp(a))
	return applyToChildren(a, lambda x : simplify(x))

def propogateMetadata(a, argTypes, variableMap, idNum):
	"""This function propogates metadata about type throughout the AST.
	argTypes lets us institute types for each function's args
	variableMap maps variable ids to their types and id numbers
	idNum gives us a global number to use for variable ids"""
	if not isinstance(a, ast.AST):
		return a
	elif type(a) == ast.FunctionDef:
		if a.name in argTypes:
			theseTypes = argTypes[a.name]
		else:
			theseTypes = []
		variableMap = copy.deepcopy(variableMap) # variables shouldn't affect variables outside
		idNum = copy.deepcopy(idNum)
		for i in range(len(a.args.args)):
			arg = a.args.args[i]
			if type(arg) == ast.arg:
				simplifyUpdateId(arg, variableMap, idNum)
				# Match the args if possible
				if len(a.args.args) == len(theseTypes) and \
					theseTypes[i] in ["int", "str", "float", "bool", "list"]:
					arg.type = eval(theseTypes[i])
					variableMap[arg.arg] = (arg.type, arg.varID)
				else:
					arg.type = None
					variableMap[arg.arg] = (None, arg.varID)
			else:
				log("transformations\tpropogateMetadata\tWeird type in args: " + str(type(arg)), "bug")

		newBody = []
		for line in a.body:
			newLine = propogateMetadata(line, argTypes, variableMap, idNum)
			if type(newLine) == list:
				newBody += newLine
			else:
				newBody.append(newLine)
		a.body = newBody
		return a
	elif type(a) == ast.Assign:
		val = a.value = propogateMetadata(a.value, argTypes, variableMap, idNum)
		if len(a.targets) == 1:
			t = a.targets[0]
			if type(t) == ast.Name:
				simplifyUpdateId(t, variableMap, idNum)
				varType = eventualType(val)
				t.type = varType
				variableMap[t.id] = (varType, t.varID) # update type
			elif type(t) in [ast.Tuple, ast.List]:
				# If the items are being assigned separately, with no dependance on each other,
				# assign the appropriate types
				getTypes = type(val) in [ast.Tuple, ast.List] and len(t.elts) == len(val.elts) and len(allVariableNamesUsed(val)) == 0
				for j in range(len(t.elts)):
					t2 = t.elts[j]
					givenType = eventualType(val.elts[j]) if getTypes else None
					if type(t2) == ast.Name:
						simplifyUpdateId(t2, variableMap, idNum)
						t2.type = givenType
						variableMap[t2.id] = (givenType, t2.varID)
					elif type(t.elts[j]) in [ast.Subscript, ast.Attribute, ast.Tuple, ast.List]:
						pass
					else:
						log("transformations\tpropogateMetadata\tOdd listTarget: " + str(type(t.elts[j])), "bug")
		return a
	elif type(a) == ast.AugAssign:
		# Turn all AugAssigns into Assigns
		t = a.target = propogateMetadata(a.target, argTypes, variableMap, idNum)
		a.value = propogateMetadata(a.value, argTypes, variableMap, idNum)
		if type(t) == ast.Name:
			if eventualType(a.target) not in [bool, int, str, float]:
				finalType = None
			else:
				if type(a.target) == ast.Name:
					loadedTarget = ast.Name(a.target.id, ast.Load())
				elif type(a.target) == ast.Subscript:
					loadedTarget = ast.Subscript(deepcopy(a.target.value), deepcopy(a.target.slice), ast.Load())
				elif type(a.target) == ast.Attribute:
					loadedTarget = ast.Attribute(deepcopy(a.target.value), a.target.attr, ast.Load())
				elif type(a.target) == ast.Tuple:
					loadedTarget = ast.Tuple(deepcopy(a.target.elts), ast.Load())
				elif type(a.target) == ast.List:
					loadedTarget = ast.List(deepcopy(a.target.elts), ast.Load())
				else:
					log("transformations\tsimplify\tOdd AugAssign target: " + str(type(a.target)), "bug")
				transferMetaData(a.target, loadedTarget)
				actualValue = ast.BinOp(loadedTarget, a.op, a.value)
				finalType = eventualType(actualValue)

			simplifyUpdateId(t, variableMap, idNum)
			varType = finalType
			t.type = varType
			variableMap[t.id] = (varType, t.varID) # update type
		return a
	elif type(a) == ast.For: # START HERE
		a.iter = propogateMetadata(a.iter, argTypes, variableMap, idNum)
		if type(a.target) == ast.Name:
			simplifyUpdateId(a.target, variableMap, idNum)
			ev = eventualType(a.iter)
			if ev == str:
				a.target.type = str
			# we know ranges are made of ints
			elif type(a.iter) == ast.Call and type(a.iter.func) == ast.Name and (a.iter.func.id) == "range":
				a.target.type = int
			else:
				a.target.type = None
			variableMap[a.target.id] = (a.target.type, a.target.varID)
		a.target = propogateMetadata(a.target, argTypes, variableMap, idNum)

		# Go through the body and orelse to map out more variables
		body = []
		bodyMap = copy.deepcopy(variableMap)
		for i in range(len(a.body)):
			result = propogateMetadata(a.body[i], argTypes, bodyMap, idNum)
			if type(result) == list:
				body += result
			else:
				body.append(result)
		a.body = body

		orelse = []
		orelseMap = copy.deepcopy(variableMap)
		for var in bodyMap:
			if var not in orelseMap:
				orelseMap[var] = (42, bodyMap[var][1])
		for i in range(len(a.orelse)):
			result = propogateMetadata(a.orelse[i], argTypes, orelseMap, idNum)
			if type(result) == list:
				orelse += result
			else:
				orelse.append(result)
		a.orelse = orelse

		keys = list(variableMap.keys())
		for key in keys: # reset types of changed keys
			if key not in bodyMap or bodyMap[key] != variableMap[key] or \
				key not in orelseMap or orelseMap[key] != variableMap[key]:
				variableMap[key] = (None, variableMap[key][1])
		if countOccurances(a.body, ast.Break) == 0: # We will definitely enter the else!
			for key in orelseMap:
				# If we KNOW it will be this type
				if key not in bodyMap or bodyMap[key] == orelseMap[key]:
					variableMap[key] = orelseMap[key]

		# If we KNOW it will run at least once
		if listNotEmpty(a.iter):
			for key in bodyMap:
				if key in variableMap:
					continue
				# type might be changed
				elif key in orelseMap and orelseMap[key] != bodyMap[key]:
					continue
				variableMap[key] = bodyMap[key]
		return a
	elif type(a) == ast.While:
		body = []
		bodyMap = copy.deepcopy(variableMap)
		for i in range(len(a.body)):
			result = propogateMetadata(a.body[i], argTypes, bodyMap, idNum)
			if type(result) == list:
				body += result
			else:
				body.append(result)
		a.body = body

		orelse = []
		orelseMap = copy.deepcopy(variableMap)
		for var in bodyMap:
			if var not in orelseMap:
				orelseMap[var] = (None, bodyMap[var][1])
		for i in range(len(a.orelse)):
			result = propogateMetadata(a.orelse[i], argTypes, orelseMap, idNum)
			if type(result) == list:
				orelse += result
			else:
				orelse.append(result)
		a.orelse = orelse

		keys = list(variableMap.keys())
		for key in keys:
			if key not in bodyMap or bodyMap[key] != variableMap[key] or \
				key not in orelseMap or orelseMap[key] != variableMap[key]:
				variableMap[key] = (None, variableMap[key][1])

		a.test = propogateMetadata(a.test, argTypes, variableMap, idNum)
		return a
	elif type(a) == ast.If:
		a.test = propogateMetadata(a.test, argTypes, variableMap, idNum)
		variableMap1 = copy.deepcopy(variableMap)
		variableMap2 = copy.deepcopy(variableMap)

		body = []
		for i in range(len(a.body)):
			result = propogateMetadata(a.body[i], argTypes, variableMap1, idNum)
			if type(result) == list:
				body += result
			else:
				body.append(result)
		a.body = body

		for var in variableMap1:
			if var not in variableMap2:
				variableMap2[var] = (42, variableMap1[var][1])

		orelse = []
		for i in range(len(a.orelse)):
			result = propogateMetadata(a.orelse[i], argTypes, variableMap2, idNum)
			if type(result) == list:
				orelse += result
			else:
				orelse.append(result)
		a.orelse = orelse

		variableMap.clear()
		for key in variableMap1:
			if key in variableMap2:
				if variableMap1[key] == variableMap2[key]:
					variableMap[key] = variableMap1[key]
				elif variableMap1[key][1] != variableMap2[key][1]:
					log("transformations\tsimplify\tvarId mismatch", "bug")
				else: # type mismatch
					if variableMap2[key][0] == 42:
						variableMap[key] = variableMap1[key]
					else:
						variableMap[key] = (None, variableMap1[key][1])
			elif len(a.orelse) > 0 and type(a.orelse[-1]) == ast.Return: # if the else exits, it doesn't matter
				variableMap[key] = variableMap1[key]
		for key in variableMap2:
			if key not in variableMap1 and len(a.body) > 0 and type(a.body[-1]) == ast.Return: # if the if exits, it doesn't matter
				variableMap[key] = variableMap2[key]
		return a
	elif type(a) == ast.Name:
		if a.id in variableMap and variableMap[a.id][0] != 42:
			a.type = variableMap[a.id][0]
			a.varID = variableMap[a.id][1]
		else:
			if a.id in variableMap:
				a.varID = variableMap[a.id][1]
		a.ctx = propogateMetadata(a.ctx, argTypes, variableMap, idNum)
		return a
	elif type(a) == ast.AugLoad:
		return ast.Load()
	elif type(a) == ast.AugStore:
		return ast.Store()
	return applyToChildren(a, lambda x : propogateMetadata(x, argTypes, variableMap, idNum))

### SIMPLIFYING FUNCTIONS ###

def applyTransferLambda(x):
	"""Simplify an expression by applying constant folding, re-formatting to an AST, and then tranferring the metadata appropriately."""
	if x == None:
		return x
	tmp = astFormat(constantFolding(x))
	if hasattr(tmp, "global_id") and hasattr(x, "global_id") and tmp.global_id != x.global_id:
		return tmp # don't do the transfer, this already has its own metadata
	else:
		transferMetaData(x, tmp)
	return tmp

def constantFolding(a):
	"""In constant folding, we evaluate all constant expressions instead of doing operations at runtime"""
	if not isinstance(a, ast.AST):
		return a
	t = type(a)
	if t in [ast.FunctionDef, ast.ClassDef]:
		for i in range(len(a.body)):
			a.body[i] = applyTransferLambda(a.body[i])
		return a
	elif t in [ast.Import, ast.ImportFrom, ast.Global]:
		return a
	elif t == ast.BoolOp:
		# Condense the boolean's values
		newValues = []
		ranks = []
		count = 0
		for val in a.values:
			# Condense the boolean operations into one line, if possible
			c = constantFolding(val)
			if type(c) == ast.BoolOp and type(c.op) == type(a.op) and not hasattr(c, "multiComp"):
				newValues += c.values
				ranks.append(range(count,count+len(c.values)))
				count += len(c.values)
			else:
				newValues.append(c)
				ranks.append(count)
				count += 1

		# Or breaks with True, And breaks with False
		breaks = (type(a.op) == ast.Or)

		# Remove the opposite values IF removing them won't mess up the type.
		i = len(newValues) - 1
		while i > 0:
			if (newValues[i] == (not breaks)) and eventualType(newValues[i-1]) == bool:
				newValues.pop(i)
			i -= 1

		if len(newValues) == 0:
			# There's nothing to evaluate
			return (not breaks)
		elif len(newValues) == 1:
			# If we're down to one value, just return it!
			return newValues[0]
		elif newValues[0] == breaks:
			# If the first value breaks it, done!
			return breaks
		elif newValues.count(breaks) >= 1:
			# We don't need any values that occur after a break
			i = newValues.index(breaks)
			newValues = newValues[:i+1]
		for i in range(len(newValues)):
			newValues[i] = astFormat(newValues[i])
			# get the corresponding value
			if i in ranks:
				transferMetaData(a.values[ranks.index(i)], newValues[i])
			else: # it's in a list
				for j in range(len(ranks)):
					if type(ranks[j]) == list and i in ranks[j]:
						transferMetaData(a.values[j].values[ranks[j].index(i)], newValues[i])
						break
		a.values = newValues
		return a
	elif t == ast.BinOp:
		l = constantFolding(a.left)
		r = constantFolding(a.right)
		# Hack to make hint chaining work- don't constant-fold filler strings!
		if containsTokenStepString(l) or containsTokenStepString(r):
			a.left = applyTransferLambda(a.left)
			a.right = applyTransferLambda(a.right)
			return a
		if type(l) in builtInTypes and type(r) in builtInTypes:
			try:
				val = doBinaryOp(a.op, l, r)
				if type(val) == float and val % 0.0001 != 0: # don't deal with trailing floats
					pass
				else:
					tmp = astFormat(val)
					transferMetaData(a, tmp)
					return tmp
			except:
				# We have some kind of divide-by-zero issue.
				# Therefore, don't calculate it!
				pass
		if type(l) in builtInTypes:
			if type(r) == bool:
				r = int(r)
			# Commutative operations
			elif type(r) == ast.BinOp and type(r.op) == type(a.op) and type(a.op) in [ast.Add, ast.Mult, ast.BitOr, ast.BitAnd, ast.BitXor]:
				rLeft = constantFolding(r.left)
				if type(rLeft) in builtInTypes:
					try:
						newLeft = astFormat(doBinaryOp(a.op, l, rLeft))
						transferMetaData(r.left, newLeft)
						return ast.BinOp(newLeft, a.op, r.right)
					except Exception as e:
						pass

			# Empty string is often unneccessary
			if type(l) == str and l == '':
				if type(a.op) == ast.Add and eventualType(r) == str:
					return r
				elif type(a.op) == ast.Mult and eventualType(r) == int:
					return ''
			elif type(l) == bool:
				l = int(l)
			# 0 is often unneccessary
			if l == 0 and eventualType(r) in [int, float]:
				if type(a.op) in [ast.Add, ast.BitOr]:
					# If it won't change the type
					if type(l) == int or eventualType(r) == float:
						return r
					elif type(l) == float: # Cast it
						return ast.Call(ast.Name("float", ast.Load(), typeCastFunction=True), [r], [])
				elif type(a.op) == ast.Sub:
					tmpR = astFormat(r)
					transferMetaData(a.right, tmpR)
					newR = ast.UnaryOp(ast.USub(addedOtherOp=True), tmpR, addedOther=True)
					if type(l) == int or eventualType(r) == float:
						return newR
					elif type(l) == float:
						return ast.Call(ast.Name("float", ast.Load(), typeCastFunction=True), [newR], [])
				elif type(a.op) in [ast.Mult, ast.LShift, ast.RShift]:
					# If either is a float, it's 0
					return 0.0 if float in [eventualType(r), type(l)] else 0
				elif type(a.op) in [ast.Div, ast.FloorDiv, ast.Mod]:
					# Check if the right might be zero
					if type(r) in builtInTypes and r != 0:
						return 0.0 if float in [eventualType(r), type(l)] else 0
			# Same for 1
			elif l == 1:
				if type(a.op) == ast.Mult and eventualType(r) in [int, float]:
					if type(l) == int or eventualType(r) == float:
						return r
					elif type(l) == float:
						return ast.Call(ast.Name("float", ast.Load(), typeCastFunction=True), [r], [])
			# No reason to make this a float if the other value has already been cast
			elif type(l) == float and l == int(l):
				if type(a.op) in [ast.Add, ast.Sub, ast.Mult, ast.Div] and eventualType(r) == float:
					l = int(l)
		# Some of the same operations are done with the right, but not all of them
		if type(r) in builtInTypes:
			if type(r) == str and r == '':
				if type(a.op) == ast.Add and eventualType(l) == str:
					return l
				elif type(a.op) == ast.Mult and eventualType(l) == int:
					return ''
			elif type(r) == bool:
				r = int(r)
			else:
				if r == 0 and eventualType(l) in [int, float]:
					if type(a.op) in [ast.Add, ast.Sub, ast.LShift, ast.RShift, ast.BitOr]:
						if type(r) == int or eventualType(l) == float:
							return l
						elif type(r) == float:
							return ast.Call(ast.Name("float", ast.Load(), typeCastFunction=True), [l], [])
					elif type(a.op) == ast.Mult:
						return 0.0 if float in [eventualType(l), type(r)] else 0
				elif r == 1:
					if type(a.op) in [ast.Mult, ast.Div, ast.Pow] and eventualType(l) in [int, float]:
						if type(r) == int or eventualType(l) == float:
							return l
						elif type(r) == float:
							return ast.Call(ast.Name("float", ast.Load(), typeCastFunction=True), [l], [])
					elif type(a.op) == ast.FloorDiv and eventualType(l) == int:
						if eventualType( r ) == int:
							return l
						elif eventualType( r ) == float:
							return ast.Call(ast.Name("float", ast.Load(), typeCastFunction=True), [l], [])
				elif type(r) == float and r == int(r):
					if type(a.op) in [ast.Add, ast.Sub, ast.Mult, ast.Div] and eventualType(l) == float:
						r = int(r)
		a.left = applyTransferLambda(a.left)
		a.right = applyTransferLambda(a.right)
		return a
	elif t == ast.IfExp:
		# Sometimes, we can simplify the statement
		test = constantFolding(a.test)
		b = constantFolding(a.body)
		o = constantFolding(a.orelse)

		aTest = astFormat(test)
		transferMetaData(a.test, aTest)
		aB = astFormat(b)
		transferMetaData(a.body, aB)
		aO = astFormat(o)
		transferMetaData(a.orelse, aO)

		if type(test) == bool:
			return aB if test else aO # evaluate the if expression now
		elif compareASTs(b, o, checkEquality=True) == 0:
			return aB # if they're the same, no reason for the expression
		a.test = aTest
		a.body = aB
		a.orelse = aO
		return a
	elif t == ast.Compare:
		if len(a.ops) == 0 or len(a.comparators) == 0:
			return True # No ops? Okay, empty case is true!
		op = a.ops[0]
		l = constantFolding(a.left)
		r = constantFolding(a.comparators[0])
		# Hack to make hint chaining work- don't constant-fold filler strings!
		if containsTokenStepString(l) or containsTokenStepString(r):
			tmpLeft = astFormat(l)
			transferMetaData(a.left, tmpLeft)
			a.left = tmpLeft
			tmpRight = astFormat(r)
			transferMetaData(a.comparators[0], tmpRight)
			a.comparators = [tmpRight]
			return a
		# Check whether the two sides are the same
		comp = compareASTs(l, r, checkEquality=True) == 0
		if comp and (not couldCrash(l)) and type(op) in [ast.Lt, ast.Gt, ast.NotEq]:
			tmp = ast.NameConstant(False)
			transferMetaData(a, tmp)
			return tmp
		elif comp and (not couldCrash(l)) and type(op) in [ast.Eq, ast.LtE, ast.GtE]:
			tmp = ast.NameConstant(True)
			transferMetaData(a, tmp)
			return tmp
		if (type(l) in builtInTypes) and (type(r) in builtInTypes):
			try:
				result = astFormat(doCompare(op, l, r))
				transferMetaData(a, result)
				return result
			except:
				pass
		# Reduce the expressions when possible!
		if type(l) == type(r) == ast.BinOp and type(l.op) == type(r.op) and not couldCrash(l) and not couldCrash(r):
			if type(l.op) == ast.Add:
				# Remove repeated values
				unchanged = False
				if compareASTs(l.left, r.left, checkEquality=True) == 0:
					l = l.right
					r = r.right
				elif compareASTs(l.right, r.right, checkEquality=True) == 0:
					l = l.left
					r = r.left
				elif compareASTs(l.left, r.right, checkEquality=True) == 0 and eventualType(l) in [int, float]:
					l = l.right
					r = r.left
				elif compareASTs(l.right, r.left, checkEquality=True) == 0 and eventualType(l) in [int, float]:
					l = l.left
					r = r.right
				else:
					unchanged = True
				if not unchanged:
					tmpLeft = astFormat(l)
					transferMetaData(a.left, tmpLeft)
					a.left = tmpLeft
					tmpRight = astFormat(r)
					transferMetaData(a.comparators[0], tmpRight)
					a.comparators = [tmpRight]
					return constantFolding(a) # Repeat this check to see if we can keep reducing it
			elif type(l.op) == ast.Sub:
				unchanged = False
				if compareASTs(l.left, r.left, checkEquality=True) == 0:
					l = l.right
					r = r.right
				elif compareASTs(l.right, r.right, checkEquality=True) == 0:
					l = l.left
					r = r.left
				else:
					unchanged = True
				if not unchanged:
					tmpLeft = astFormat(l)
					transferMetaData(a.left, tmpLeft)
					a.left = tmpLeft
					tmpRight = astFormat(r)
					transferMetaData(a.comparators[0], tmpRight)
					a.comparators = [tmpRight]
					return constantFolding(a)
		tmpLeft = astFormat(l)
		transferMetaData(a.left, tmpLeft)
		a.left = tmpLeft
		tmpRight = astFormat(r)
		transferMetaData(a.comparators[0], tmpRight)
		a.comparators = [tmpRight]
		return a
	elif t == ast.Call:
		# TODO: this can be done much better
		a.func = applyTransferLambda(a.func)

		allConstant = True
		tmpArgs = []
		for i in range(len(a.args)):
			tmpArgs.append(constantFolding(a.args[i]))
			if type(tmpArgs[i]) not in [int, float, bool, str]:
				allConstant = False
		if len(a.keywords) > 0:
			allConstant = False
		if allConstant and (type(a.func) == ast.Name) and (a.func.id in builtInFunctions.keys()) and \
							(a.func.id not in ["range", "raw_input", "input", "open", "randint", "random", "slice"]):
			try:
				result = apply(eval(a.func.id), tmpArgs)
				transferMetaData(a, astFormat(result))
				return result
			except:
				# Not gonna happen unless it crashes
				#log("transformations\tconstantFolding\tFunction crashed: " + str(a.func.id), "bug")
				pass
		for i in range(len(a.args)):
			tmpArg = astFormat(tmpArgs[i])
			transferMetaData(a.args[i], tmpArg)
			a.args[i] = tmpArg
		return a
	# This needs to be separate because the attribute is a string
	elif t == ast.Attribute:
		a.value = applyTransferLambda(a.value)
		return a
	elif t == ast.Slice:
		if a.lower != None:
			a.lower = applyTransferLambda(a.lower)
		if a.upper != None:
			a.upper = applyTransferLambda(a.upper)
		if a.step != None:
			a.step = applyTransferLambda(a.step)
		return a
	elif t == ast.Num:
		return a.n
	elif t == ast.Bytes:
		return a.s
	elif t == ast.Str:
		# Don't do things to filler strings
		if len(a.s) > 0 and isTokenStepString(a.s):
			return a
		return a.s
	elif t == ast.NameConstant:
		if a.value == True:
			return True
		elif a.value == False:
			return False
		elif a.value == None:
			return None
	elif t == ast.Name:
		return a
	else: # All statements, ast.Lambda, ast.Dict, ast.Set, ast.Repr, ast.Attribute, ast.Subscript, etc.
		return applyToChildren(a, applyTransferLambda)

def isMutatingFunction(a):
	"""Given a function call, this checks whether it might change the program state when run"""
	if type(a) != ast.Call: # Can only call this on Calls!
		log("transformations\tisMutatingFunction\tNot a Call: " + str(type(a)), "bug")
		return True

	# Map of all static namesets
	funMaps = { "math" : mathFunctions, "string" : builtInStringFunctions,
				"str" : builtInStringFunctions, "list" : staticListFunctions,
				"dict" : staticDictFunctions }
	typeMaps = { str : "string", list : "list", dict : "dict" }
	if type(a.func) == ast.Name:
		funDict = builtInFunctions
		funName = a.func.id
	elif type(a.func) == ast.Attribute:
		if type(a.func.value) == ast.Name and a.func.value.id in funMaps:
			funDict = funMaps[a.func.value.id]
			funName = a.func.attr
		# if the item is calling a function directly
		elif eventualType(a.func.value) in typeMaps:
			funDict = funMaps[typeMaps[eventualType(a.func.value)]]
			funName = a.func.attr
		else:
			return True
	else:
		return True # we don't know, so yes

	# TODO: deal with student's functions
	return funName not in funDict

def allVariablesUsed(a):
	if not isinstance(a, ast.AST):
		return []
	elif type(a) == ast.Name:
		return [a]
	variables = []
	for child in ast.iter_child_nodes(a):
		variables += allVariablesUsed(child)
	return variables

def allVariableNamesUsed(a):
	"""Gathers all the variable names used in the ast"""
	if not isinstance(a, ast.AST):
		return []
	elif type(a) == ast.Name:
		return [a.id]
	elif type(a) == ast.Assign:
		"""In assignments, ignore all pure names used- they're being assigned to, not used"""
		variables = allVariableNamesUsed(a.value)
		for target in a.targets:
			if type(target) == ast.Name:
				pass
			elif type(target) in [ast.Tuple, ast.List]:
				for elt in target.elts:
					if type(elt) != ast.Name:
						variables += allVariableNamesUsed(elt)
			else:
				variables += allVariableNamesUsed(target)
		return variables
	elif type(a) == ast.AugAssign:
		variables = allVariableNamesUsed(a.value)
		variables += allVariableNamesUsed(a.target)
		return variables
	variables = []
	for child in ast.iter_child_nodes(a):
		variables += allVariableNamesUsed(child)
	return variables

def addPropTag(a, globalId):
	if not isinstance(a, ast.AST):
		return a
	a.propagatedVariable = True
	if hasattr(a, "global_id"):
		a.variableGlobalId = globalId
	return applyToChildren(a, lambda x : addPropTag(x, globalId))

def propagateValues(a, liveVars):
	"""Propagate the given values through the AST whenever their variables occur"""
	if ((not isinstance(a, ast.AST) or len(liveVars.keys()) == 0)):
		return a

	if type(a) == ast.Name:
		# Propagate the value if we have it!
		if a.id in liveVars:
			val = copy.deepcopy(liveVars[a.id])
			val.loadedVariable = True
			if hasattr(a, "global_id"):
				val.variableGlobalId = a.global_id
			return applyToChildren(val, lambda x : addPropTag(x, a.global_id))
		else:
			return a
	elif type(a) == ast.Call:
		# If something is mutated, it cannot be propagated anymore
		if isMutatingFunction(a):
			allVars = allVariablesUsed(a)
			for var in allVars:
				if (eventualType(var) not in [int, float, bool, str]):
					if (var.id in liveVars):
						del liveVars[var.id]
					currentLiveVars = list(liveVars.keys())
					for liveVar in currentLiveVars:
						varsWithin = allVariableNamesUsed(liveVars[liveVar])
						if var.id in varsWithin:
							del liveVars[liveVar]
			return a
		elif type(a.func) == ast.Name and a.func.id in liveVars and \
				eventualType(liveVars[a.func.id]) in [int, float, complex, bytes, bool, type(None)]:
			# Special case: don't move a simple value to the front of a Call
			# because it will cause a compiler error instead of a runtime error
			a.args = propagateValues(a.args, liveVars)
			a.keywords = propagateValues(a.keywords, liveVars)
			return a
	elif type(a) == ast.Attribute:
		if type(a.value) == ast.Name and a.value.id in liveVars and \
				eventualType(liveVars[a.value.id]) in [int, float, complex, bytes, bool, type(None)]:
			# Don't move for the same reason as above
			return a
	return applyToChildren(a, lambda x: propagateValues(x, liveVars))

def hasMutatingFunction(a):
	"""Checks to see if the ast has any potentially mutating functions"""
	if not isinstance(a, ast.AST):
		return False
	for node in ast.walk(a):
		if type(a) == ast.Call:
			if isMutatingFunction(a):
				return True
	return False

def clearBlockVars(a, liveVars):
	"""Clear all the vars set in this block out of the live vars"""
	if (not isinstance(a, ast.AST)) or len(liveVars.keys()) == 0:
		return

	if type(a) in [ast.Assign, ast.AugAssign]:
		if type(a) == ast.Assign:
			targets = gatherAssignedVars(a.targets)
		else:
			targets = gatherAssignedVars([a.target])
		for target in targets:
			varId = None
			if type(target) == ast.Name:
				varId = target.id
			elif type(target.value) == ast.Name:
				varId = target.value.id
			if varId in liveVars:
				del liveVars[varId]

			liveKeys = list(liveVars.keys())
			for var in liveKeys:
				# Remove the variable and any variables in which it is used
				if varId in allVariableNamesUsed(liveVars[var]):
					del liveVars[var]
		return
	elif type(a) == ast.Call:
		if hasMutatingFunction(a):
			for v in allVariablesUsed(a):
				if eventualType(v) not in [int, float, bool, str]:
					if v.id in liveVars:
						del liveVars[v.id]
					liveKeys = list(liveVars.keys())
					for var in liveKeys:
						if v.id in allVariableNamesUsed(liveVars[var]):
							del liveVars[var]
			return
	elif type(a) == ast.For:
		names = []
		if type(a.target) == ast.Name:
			names = [a.target.id]
		elif type(a.target) in [ast.Tuple, ast.List]:
			for elt in a.target.elts:
				if type(elt) == ast.Name:
					names.append(elt.id)
				elif type(elt) == ast.Subscript:
					if type(elt.value) == ast.Name:
						names.append(elt.value.id)
					else:
						log("transformations\tclearBlockVars\tFor target subscript not a name: " + str(type(elt.value)), "bug")
				else:
					log("transformations\tclearBlockVars\tFor target not a name: " + str(type(elt)), "bug")
		elif type(a.target) == ast.Subscript:
			if type(a.target.value) == ast.Name:
				names.append(a.target.value.id)
			else:
				log("transformations\tclearBlockVars\tFor target subscript not a name: " + str(type(a.target.value)), "bug")
		else:
			log("transformations\tclearBlockVars\tFor target not a name: " + str(type(a.target)), "bug")
		for name in names:
			if name in liveVars:
				del liveVars[name]

			liveKeys = list(liveVars.keys())
			for var in liveKeys:
				# Remove the variable and any variables in which it is used
				if name in allVariableNamesUsed(liveVars[var]):
					del liveVars[var]

	for child in ast.iter_child_nodes(a):
		clearBlockVars(child, liveVars)

def copyPropagation(a, liveVars=None, inLoop=False):
	"""Propagate variables into the tree, when possible"""
	if liveVars == None:
		liveVars = { }
	if type(a) == ast.Module:
		a.body = copyPropagation(a.body)
		return a
	if type(a) == ast.FunctionDef:
		a.body = copyPropagation(a.body, liveVars=liveVars)
		return a

	if type(a) == list:
		i = 0
		while i < len(a):
			deleteLine = False
			if type(a[i]) == ast.FunctionDef:
				a[i].body = copyPropagation(a[i].body, liveVars=copy.deepcopy(liveVars))
			elif type(a[i]) == ast.ClassDef:
				# TODO: can we propagate values through everything after here?
				for j in range(len(a[i].body)):
					if type(a[i].body[j]) == ast.FunctionDef:
						a[i].body[j] = copyPropagation(a[i].body[j])
			elif type(a[i]) == ast.Assign:
				# In assignments, propagate values into the right side and move the left side into the live vars
				a[i].value = propagateValues(a[i].value, liveVars)
				target = a[i].targets[0]

				if type(target) in [ast.Name, ast.Subscript, ast.Attribute]:
					varId = None
					# In plain names, we can update the liveVars
					if type(target) == ast.Name:
						varId = target.id
						if inLoop or couldCrash(a[i].value) or eventualType(a[i].value) not in [bool, int, float, str, tuple]:
							# Remove this variable from the live vars
							if varId in liveVars:
								del liveVars[varId]
						else:
							liveVars[varId] = a[i].value
					# For other values, we can at least clear out liveVars correctly
					# TODO: can we expand this?
					elif target.value == ast.Name:
						varId = target.value.id

					# Now, update the live vars based on anything reset by the new target
					liveKeys = list(liveVars.keys())
					for var in liveKeys:
						# If the var we're replacing was used elsewhere, that value will no longer be the same
						if varId in allVariableNamesUsed(liveVars[var]):
							del liveVars[var]
				elif type(target) in [ast.Tuple, ast.List]:
					# Copy the values, if we can match them
					if type(a[i].value) in [ast.Tuple, ast.List] and len(target.elts) == len(a[i].value.elts):
						for j in range(len(target.elts)):
							if type(target.elts[j]) == ast.Name:
								if (not couldCrash(a[i].value.elts[j])):
									liveVars[target.elts[j]] = a[i].value.elts[j]
								else:
									if target.elts[j] in liveVars:
										del liveVars[target.elts[j]]

					# Then get rid of any overwrites
					for e in target.elts:
						if type(e) in [ast.Name, ast.Subscript, ast.Attribute]:
							varId = None
							if type(e) == ast.Name:
								varId = e.id
							elif type(e.value) == ast.Name:
								varId = e.value.id

							liveKeys = list(liveVars.keys())
							for var in liveKeys:
								if varId in allVariableNamesUsed(liveVars[var]):
									del liveVars[var]
						else:
							log("transformations\tcopyPropagation\tWeird assign type: " + str(type(e)), "bug")
			elif type(a[i]) == ast.AugAssign:
				a[i].value = propagateValues(a[i].value, liveVars)
				assns = gatherAssignedVarIds([a[i].target])
				for target in assns:
					if target in liveVars:
						del liveVars[target]
			elif type(a[i]) == ast.For:
				# FIRST, propagate values into the iter
				if type(a[i].iter) != ast.Name: # if it IS a name, don't replace it!
					# Otherwise, we propagate first since this is evaluated once
					a[i].iter = propagateValues(a[i].iter, liveVars)

				# We reset the target variable, so reset the live vars
				names = []
				if type(a[i].target) == ast.Name:
					names = [a[i].target.id]
				elif type(a[i].target) in [ast.Tuple, ast.List]:
					for elt in a[i].target.elts:
						if type(elt) == ast.Name:
							names.append(elt.id)
						elif type(elt) == ast.Subscript:
							if type(elt.value) == ast.Name:
								names.append(elt.value.id)
							else:
								log("transformations\tcopyPropagation\tFor target subscript not a name: " + str(type(elt.value)) + "\t" + printFunction(elt.value), "bug")
						else:
							log("transformations\tcopyPropagation\tFor target not a name: " + str(type(elt)) + "\t" + printFunction(elt), "bug")
				elif type(a[i].target) == ast.Subscript:
					if type(a[i].target.value) == ast.Name:
						names.append(a[i].target.value.id)
					else:
						log("transformations\tcopyPropagation\tFor target subscript not a name: " + str(type(a[i].target.value)) + "\t" + printFunction(a[i].target.value), "bug")
				else:
					log("transformations\tcopyPropagation\tFor target not a name: " + str(type(a[i].target)) + "\t" + printFunction(a[i].target), "bug")

				for name in names:
					liveKeys = list(liveVars.keys())
					for var in liveKeys:
						if name in allVariableNamesUsed(liveVars[var]):
							del liveVars[var]
					if name in liveVars:
						del liveVars[name]
				clearBlockVars(a[i], liveVars)
				a[i].body = copyPropagation(a[i].body, copy.deepcopy(liveVars), inLoop=True)
				a[i].orelse = copyPropagation(a[i].orelse, copy.deepcopy(liveVars), inLoop=True)
			elif type(a[i]) == ast.While:
				clearBlockVars(a[i], liveVars)
				a[i].test = propagateValues(a[i].test, liveVars)
				a[i].body = copyPropagation(a[i].body, copy.deepcopy(liveVars), inLoop=True)
				a[i].orelse = copyPropagation(a[i].orelse, copy.deepcopy(liveVars), inLoop=True)
			elif type(a[i]) == ast.If:
				a[i].test = propagateValues(a[i].test, liveVars)
				liveVars1 = copy.deepcopy(liveVars)
				liveVars2 = copy.deepcopy(liveVars)
				a[i].body = copyPropagation(a[i].body, liveVars1)
				a[i].orelse = copyPropagation(a[i].orelse, liveVars2)
				liveVars.clear()
				# We can keep any values that occur in both
				for key in liveVars1:
					if key in liveVars2:
						if compareASTs(liveVars1[key], liveVars2[key], checkEquality=True) == 0:
							liveVars[key] = liveVars1[key]
			# TODO: think more deeply about how this should work
			elif type(a[i]) == ast.Try:
				a[i].body = copyPropagation(a[i].body, liveVars)
				for handler in a[i].handlers:
					handler.body = copyPropagation(handler.body, liveVars)
				a[i].orelse = copyPropagation(a[i].orelse, liveVars)
				a[i].finalbody = copyPropagation(a[i].finalbody, liveVars)
			elif type(a[i]) == ast.With:
				a[i].body = copyPropagation(a[i].body, liveVars)
			# With regular statements, just propagate the values
			elif type(a[i]) in [ast.Return, ast.Delete, ast.Raise, ast.Assert, ast.Expr]:
				propagateValues(a[i], liveVars)
			# Breaks and Continues mess everything up
			elif type(a[i]) in [ast.Break, ast.Continue]:
				break
			# These are not affected by this function
			elif type(a[i]) in [ast.Import, ast.ImportFrom, ast.Global, ast.Pass]:
				pass
			else:
				log("transformations\tcopyPropagation\tNot implemented: " + str(type(a[i])), "bug")
			i += 1
		return a
	else:
		log("transformations\tcopyPropagation\tNot a list: " + str(type(a)), "bug")
		return a

def deadCodeRemoval(a, liveVars=None, keepPrints=True, inLoop=False):
	"""Remove any code which will not be reached or used."""
	"""LiveVars keeps track of the variables that will be necessary"""
	if liveVars == None:
		liveVars = set()
	if type(a) == ast.Module:
		# Remove functions that will be overwritten anyway
		namesSeen = []
		i = len(a.body) - 1
		while i >= 0:
			if type(a.body[i]) == ast.FunctionDef:
				if a.body[i].name in namesSeen:
					# SPECIAL CHECK! Actually, the function will cause the code to crash if some of the args have the same name. Don't delete it then.
					argNames = []
					for arg in a.body[i].args.args:
						if arg.arg in argNames:
							break
						else:
							argNames.append(arg.arg)
					else: # only remove this if the args won't break it
						a.body.pop(i)
				else:
					namesSeen.append(a.body[i].name)
			elif type(a.body[i]) == ast.Assign:
				namesSeen += gatherAssignedVars(a.body[i].targets)
			i -= 1
		liveVars |= set(namesSeen) # make sure all global names are used!

	if type(a) in [ast.Module, ast.FunctionDef]:
		if type(a) == ast.Module and len(a.body) == 0:
			return a # just don't mess with it
		gid = a.body[0].global_id if len(a.body) > 0 and hasattr(a.body[0], "global_id") else None
		a.body = deadCodeRemoval(a.body, liveVars=liveVars, keepPrints=keepPrints, inLoop=inLoop)
		if len(a.body) == 0:
			a.body = [ast.Pass(removedLines=True)] if gid == None else [ast.Pass(removedLines=True, global_id=gid)]
		return a

	if type(a) == list:
		i = len(a) - 1
		while i >= 0 and len(a) > 0:
			if i >= len(a):
				i = len(a) - 1 # just in case
			stmt = a[i]
			t = type(stmt)
			# TODO: get rid of these if they aren't live
			if t in [ast.FunctionDef, ast.ClassDef]:
				newLiveVars = set()
				gid = a[i].body[0].global_id if len(a[i].body) > 0 and hasattr(a[i].body[0], "global_id") else None
				a[i] = deadCodeRemoval(a[i], liveVars=newLiveVars, keepPrints=keepPrints, inLoop=inLoop)
				liveVars |= newLiveVars
				# Empty functions are useless!
				if len(a[i].body) == 0:
					a[i].body = [ast.Pass(removedLines=True)] if gid == None else [ast.Pass(removedLines=True, global_id=gid)]
			elif t == ast.Return:
				# Get rid of everything that happens after this!
				a = a[:i+1]
				# Replace the variables
				liveVars.clear()
				liveVars |= set(allVariableNamesUsed(stmt))
			elif t in [ast.Delete, ast.Assert]:
				# Just add all variables used
				liveVars |= set(allVariableNamesUsed(stmt))
			elif t == ast.Assign:
				# Check to see if the names being assigned are in the set of live variables
				allDead = True
				allTargets = gatherAssignedVars(stmt.targets)
				allNamesUsed = allVariableNamesUsed(stmt.value)
				for target in allTargets:
					if type(target) == ast.Name and (target.id in liveVars or target.id in allNamesUsed):
						if target.id in liveVars:
							liveVars.remove(target.id)
						allDead = False
					elif type(target) in [ast.Subscript, ast.Attribute]:
						liveVars |= set(allVariableNamesUsed(target))
						allDead = False
				# Also, check if the variable itself is contained in the value, because that can crash too
				# If none are used, we can delete this line. Otherwise, use the value's vars
				if allDead and (not couldCrash(stmt)) and (not containsTokenStepString(stmt)):
					a.pop(i)
				else:
					liveVars |= set(allVariableNamesUsed(stmt.value))
			elif t == ast.AugAssign:
				liveVars |= set(allVariableNamesUsed(stmt.target))
				liveVars |= set(allVariableNamesUsed(stmt.value))
			elif t == ast.For:
				# If there is no use of break, there's no reason to use else with the loop,
				# so move the lines outside and go over them separately
				if len(stmt.orelse) > 0 and countOccurances(stmt, ast.Break) == 0:
					lines = stmt.orelse
					stmt.orelse = []
					a[i:i+1] = [stmt] + lines
					i += len(lines)
					continue # don't subtract one

				targetNames = []
				if type(a[i].target) == ast.Name:
					targetNames = [a[i].target.id]
				elif type(a[i].target) in [ast.Tuple, ast.List]:
					for elt in a[i].target.elts:
						if type(elt) == ast.Name:
							targetNames.append(elt.id)
						elif type(elt) == ast.Subscript:
							if type(elt.value) == ast.Name:
								targetNames.append(elt.value.id)
							else:
								log("transformations\tdeadCodeRemoval\tFor target subscript not a name: " + str(type(elt.value)) + "\t" + printFunction(elt.value), "bug")
						else:
							log("transformations\tdeadCodeRemoval\tFor target not a name: " + str(type(elt)) + "\t" + printFunction(elt), "bug")
				elif type(a[i].target) == ast.Subscript:
					if type(a[i].target.value) == ast.Name:
						targetNames.append(a[i].target.value.id)
					else:
						log("transformations\tdeadCodeRemoval\tFor target subscript not a name: " + str(type(a[i].target.value)) + "\t" + printFunction(a[i].target.value), "bug")
				else:
					log("transformations\tdeadCodeRemoval\tFor target not a name: " + str(type(a[i].target)) + "\t" + printFunction(a[i].target), "bug")

				# We need to make ALL variables in the loop live, since they update continuously
				liveVars |= set(allVariableNamesUsed(stmt))
				gid = stmt.body[0].global_id if len(stmt.body) > 0 and hasattr(stmt.body[0], "global_id") else None
				stmt.body = deadCodeRemoval(stmt.body, copy.deepcopy(liveVars), keepPrints=keepPrints, inLoop=True)
				stmt.orelse = deadCodeRemoval(stmt.orelse, copy.deepcopy(liveVars), keepPrints=keepPrints, inLoop=inLoop)
				# If the body is empty and we don't need the target, get rid of it!
				if len(stmt.body) == 0:
					for name in targetNames:
						if name in liveVars:
							stmt.body = [ast.Pass(removedLines=True)] if gid == None else [ast.Pass(removedLines=True, global_id=gid)]
							break
					else:
						if couldCrash(stmt.iter) or containsTokenStepString(stmt.iter):
							a[i] = ast.Expr(stmt.iter, collapsedExpr=True)
						else:
							a.pop(i)
						if len(stmt.orelse) > 0:
							a[i:i+1] = a[i] + stmt.orelse

				# The names are wiped UPDATE - NOPE, what if we never enter the loop? 
				#for name in targetNames:
				#	liveVars.remove(name)
			elif t == ast.While:
				# If there is no use of break, there's no reason to use else with the loop,
				# so move the lines outside and go over them separately
				if len(stmt.orelse) > 0 and countOccurances(stmt, ast.Break) == 0:
					lines = stmt.orelse
					stmt.orelse = []
					a[i:i+1] = [stmt] + lines
					i += len(lines)
					continue

				# We need to make ALL variables in the loop live, since they update continuously
				liveVars |= set(allVariableNamesUsed(stmt))
				old_global_id = stmt.body[0].global_id
				stmt.body = deadCodeRemoval(stmt.body, copy.deepcopy(liveVars), keepPrints=keepPrints, inLoop=True)
				stmt.orelse = deadCodeRemoval(stmt.orelse, copy.deepcopy(liveVars), keepPrints=keepPrints, inLoop=inLoop)
				# If the body is empty, get rid of it!
				if len(stmt.body) == 0:
					stmt.body = [ast.Pass(removedLines=True, global_id=old_global_id)]
			elif t == ast.If:
				# First, if True/False, just replace it with the lines
				test = a[i].test
				if type(test) == ast.NameConstant and test.value in [True, False]:
					assignedVars = getAllAssignedVars(a[i])
					for var in assignedVars:
						# UNLESS we have a weird variable assignment problem
						if var.id[0] == "g" and hasattr(var, "originalId"):
							log("canonicalize\tdeadCodeRemoval\tWeird global variable: " + printFunction(a[i]), "bug")
							break
					else:
						if test.value == True:
							a[i:i+1] = a[i].body
						else:
							a[i:i+1] = a[i].orelse
						continue
				# For if statements, see if you can shorten things
				liveVars1 = copy.deepcopy(liveVars)
				liveVars2 = copy.deepcopy(liveVars)
				stmt.body = deadCodeRemoval(stmt.body, liveVars1, keepPrints=keepPrints, inLoop=inLoop)
				stmt.orelse = deadCodeRemoval(stmt.orelse, liveVars2, keepPrints=keepPrints, inLoop=inLoop)
				liveVars.clear()
				allVars = liveVars1 | liveVars2 | set(allVariableNamesUsed(stmt.test))
				liveVars |= allVars
				if len(stmt.body) == 0 and len(stmt.orelse) == 0:
					# Get rid of the if and keep going
					if couldCrash(stmt.test) or containsTokenStepString(stmt.test):
						newStmt = ast.Expr(stmt.test, collapsedExpr=True)
						transferMetaData(stmt, newStmt)
						a[i] = newStmt
					else:
						a.pop(i)
					i -= 1
					continue
				if len(stmt.body) == 0:
					# If the body is empty, switch it with the else
					stmt.test = deMorganize(ast.UnaryOp(ast.Not(addedNotOp=True), stmt.test, addedNot=True))
					(stmt.body, stmt.orelse) = (stmt.orelse, stmt.body)
				if len(stmt.orelse) == 0:
					# See if we can make the rest of the function the else statement
					if type(stmt.body[-1]) == type(a[-1]) == ast.Return:
						# If the if is larger than the rest, switch them!
						if len(stmt.body) > len(a[i+1:]):
							stmt.test = deMorganize(ast.UnaryOp(ast.Not(addedNotOp=True), stmt.test, addedNot=True))
							(a[i+1:], stmt.body) = (stmt.body, a[i+1:])
				else:
					# Check to see if we should switch the if and else parts
					if len(stmt.body) > len(stmt.orelse):
						stmt.test = deMorganize(ast.UnaryOp(ast.Not(addedNotOp=True), stmt.test, addedNot=True))
						(stmt.body, stmt.orelse) = (stmt.orelse, stmt.body)
			elif t == ast.Import:
				if len(stmt.names) == 0:
					a.pop(i)
			elif t == ast.Global:
				j = 0
				while j < len(a.names):
					if a.names[j] not in liveVars:
						a.names.pop(j)
					else:
						j += 1
			elif t == ast.Expr:
				# Remove the line if it won't crash things.
				if couldCrash(stmt) or containsTokenStepString(stmt):
					liveVars |= set(allVariableNamesUsed(stmt))
				else:
					# check whether any of these variables might crash the program
					# I know, it's weird, but occasionally a student might use a var before defining it
					allVars = allVariableNamesUsed(stmt)
					for j in range(i):
						if type(a[j]) == ast.Assign:
							for id in gatherAssignedVarIds(a[j].targets):
								if id in allVars:
									allVars.remove(id)
					if len(allVars) > 0:
						liveVars |= set(allVariableNamesUsed(stmt))
					else:
						a.pop(i)
			# for now, just be careful with these types of statements
			elif t in [ast.With, ast.Raise, ast.Try]:
				liveVars |= set(allVariableNamesUsed(stmt))
			elif t == ast.Pass:
				a.pop(i) # pass does *nothing*
			elif t in [ast.Continue, ast.Break]:
				if inLoop: # If we're in a loop, nothing that follows matters! Otherwise, leave it alone, this will just crash.
					a = a[:i+1]
					break
			# We don't know what they're doing- leave it alone
			elif t in [ast.ImportFrom]:
				pass
			# Have not yet implemented these
			else:
				log("transformations\tdeadCodeRemoval\tNot implemented: " + str(type(stmt)), "bug")
			i -= 1
		return a
	else:
		log("transformations\tdeadCodeRemoval\tNot a list: " + str(a), "bug")
		return a

### ORDERING FUNCTIONS ###

def getKeyDict(d, key):
	if key not in d:
		d[key] = { "self" : key }
	return d[key]

def traverseTrail(d, trail):
	temp = d
	for key in trail:
		temp = temp[key]
	return temp

def areDisjoint(a, b):
	"""Are the sets of values that satisfy these two boolean constraints disjoint?"""
	# The easiest way to be disjoint is to have comparisons that cover different areas
	if type(a) == type(b) == ast.Compare:
		aop = a.ops[0]
		bop = b.ops[0]
		aLeft = a.left
		aRight = a.comparators[0]
		bLeft = b.left
		bRight = b.comparators[0]
		alblComp = compareASTs(aLeft, bLeft, checkEquality=True)
		albrComp = compareASTs(aLeft, bRight, checkEquality=True)
		arblComp = compareASTs(aRight, bLeft, checkEquality=True)
		arbrComp = compareASTs(aRight, bRight, checkEquality=True)
		altype = type(aLeft) in [ast.Num, ast.Str]
		artype = type(aRight) in [ast.Num, ast.Str]
		bltype = type(bLeft) in [ast.Num, ast.Str]
		brtype = type(bRight) in [ast.Num, ast.Str]

		if (type(aop) == ast.Eq and type(bop) == ast.NotEq) or \
			(type(bop) == ast.Eq and type(aop) == ast.NotEq):
			# x == y, x != y
			if (alblComp == 0 and arbrComp == 0) or (albrComp == 0 and arblComp == 0):
				return True
		elif type(aop) == type(bop) == ast.Eq:
			if (alblComp == 0 and arbrComp == 0) or (albrComp == 0 and arblComp == 0):
				return False
			# x = num1, x = num2
			elif alblComp == 0 and artype and brtype:
				return True
			elif albrComp == 0 and artype and bltype:
				return True
			elif arblComp == 0 and altype and brtype:
				return True
			elif arbrComp == 0 and altype and bltype:
				return True
		elif (type(aop) == ast.Lt and type(bop) == ast.GtE) or \
			(type(aop) == ast.Gt and type(bop) == ast.LtE) or \
			(type(aop) == ast.LtE and type(bop) == ast.Gt) or \
			(type(aop) == ast.GtE and type(bop) == ast.Lt) or \
			(type(aop) == ast.Is and type(bop) == ast.IsNot) or \
			(type(aop) == ast.IsNot and type(bop) == ast.Is) or \
			(type(aop) == ast.In and type(bop) == ast.NotIn) or \
			(type(aop) == ast.NotIn and type(bop) == ast.In):
			if alblComp == 0 and arbrComp == 0:
				return True
		elif (type(aop) == ast.Lt and type(bop) == ast.LtE) or \
			(type(aop) == ast.Gt and type(bop) == ast.GtE) or \
			(type(aop) == ast.LtE and type(bop) == ast.Lt) or \
			(type(aop) == ast.GtE and type(bop) == ast.Gt):
			if albrComp == 0 and arblComp == 0:
				return True
	elif type(a) == type(b) == ast.BoolOp:
		return False # for now- TODO: when is this not true?
	elif type(a) == ast.UnaryOp and type(a.op) == ast.Not:
		if compareASTs(a.operand, b, checkEquality=True) == 0:
			return True
	elif type(b) == ast.UnaryOp and type(b.op) == ast.Not:
		if compareASTs(b.operand, a, checkEquality=True) == 0:
			return True
	return False

def crashesOn(a):
	"""Determines where the expression might crash"""
	# TODO: integrate typeCrashes
	if not isinstance(a, ast.AST):
		return []
	if type(a) == ast.BinOp:
		l = eventualType(a.left)
		r = eventualType(a.right)
		if type(a.op) == ast.Add:
			if not ((l == r == str) or (l in [int, float] and r in [int, float])):
				return [a]
		elif type(a.op) == ast.Mult:
			if not ((l == str and r == int) or (l == int and r == str) or \
				(l in [int, float] and r in [int, float])):
				return [a]
		elif type(a.op) in [ast.Sub, ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd]:
			if l not in [int, float] or r not in [int, float]:
				return [a]
		else: # ast.Div, ast.FloorDiv, ast.Mod
			if (type(a.right) != ast.Num or a.right.n == 0) or \
				(l not in [int, float] or r not in [int, float]):
				return [a]
	elif type(a) == ast.UnaryOp:
		if type(a.op) in [ast.UAdd, ast.USub]:
			if eventualType(a.operand) not in [int, float]:
				return [a]
		elif type(a.op) == ast.Invert:
			if eventualType(a.operand) != int:
				return [a]
	elif type(a) == ast.Compare:
		if len(a.ops) != len(a.comparators):
			return [a]
		elif type(a.ops[0]) in [ast.In, ast.NotIn] and not isIterableType(eventualType(a.comparators[0])):
			return [a]
		elif type(a.ops[0]) in [ast.Lt, ast.LtE, ast.Gt, ast.GtE]:
			# In Python3, you can't compare different types. BOOOOOO!!
			firstType = eventualType(a.left)
			if firstType == None:
				return [a]
			for comp in a.comparators:
				if eventualType(comp) != firstType:
					return [a]
	elif type(a) == ast.Call:
		env = [] # TODO: what if the environments aren't imported?
		funMaps = { "math" : mathFunctions, "string" : builtInStringFunctions }
		safeFunMaps = { "math" : safeMathFunctions, "string" : safeStringFunctions }
		if type(a.func) == ast.Name:
			funDict = builtInFunctions
			safeFuns = builtInSafeFunctions
			funName = a.func.id
		elif type(a.func) == ast.Attribute:
			if type(a.func.value) == ast.Name and a.func.value.id in funMaps:
				funDict = funMaps[a.func.value.id]
				safeFuns = safeFunMaps[a.func.value.id]
				funName = a.func.attr
			elif eventualType(a.func.value) == str:
				funDict = funMaps["string"]
				safeFuns = safeFunMaps["string"]
				funName = a.func.attr
			else: # including list and dict
				return [a]
		else:
			return [a]

		runOnce = 0 # So we can break
		while (runOnce == 0):
			if funName in safeFuns:
				argTypes = []
				for i in range(len(a.args)):
					eventual = eventualType(a.args[i])
					if eventual == None:
						return [a]
					argTypes.append(eventual)

				if funName in ["max", "min"]:
					break # Special functions

				for key in funDict[funName]:
					if len(key) != len(argTypes):
						continue
					for i in range(len(key)):
						if not (key[i] == argTypes[i] or issubclass(argTypes[i], key[i])):
							break
					else:
						break
				else:
					return [a]
				break # found one that works
			else:
				return [a]
	elif type(a) == ast.Subscript:
		if eventualType(a.value) not in [str, list, tuple]:
			return [a]
	elif type(a) == ast.Name:
		# If it's an undefined variable, it might crash
		if hasattr(a, "randomVar"):
			return [a]
	elif type(a) == ast.Slice:
		if a.lower != None and eventualType(a.lower) != int:
			return [a]
		if a.upper != None and eventualType(a.upper) != int:
			return [a]
		if a.step != None and eventualType(a.step) != int:
			return [a]
	elif type(a) in [ast.Assert, ast.Import, ast.ImportFrom, ast.Attribute, ast.Index]:
		return [a]

	allCrashes = []
	for child in ast.iter_child_nodes(a):
		allCrashes += crashesOn(child)
	return allCrashes

def isNegation(a, b):
	"""Is a the negation of b?"""
	return compareASTs(deMorganize(ast.UnaryOp(ast.Not(), deepcopy(a))), b, checkEquality=True) == 0

def reverse(op):
	"""Reverse the direction of the comparison for normalization purposes"""
	rev = not op.reversed if hasattr(op, "reversed") else True
	if type(op) == ast.Gt:
		newOp = ast.Lt()
		transferMetaData(op, newOp)
		newOp.reversed = rev
		return newOp
	elif type(op) == ast.GtE:
		newOp = ast.LtE()
		transferMetaData(op, newOp)
		newOp.reversed = rev
		return newOp
	else:
		return op # Do not change!

def orderCommutativeOperations(a):
	"""Order all expressions that are in commutative operations"""
	"""TODO: add commutative function lines?"""
	if not isinstance(a, ast.AST):
		return a
	# If branches can be commutative as long as their tests are disjoint
	if type(a) == ast.If:
		a = applyToChildren(a, orderCommutativeOperations)
		# If the else is (strictly) shorter than the body, switch them
		if len(a.orelse) != 0 and len(a.body) > len(a.orelse):
			newTest = ast.UnaryOp(ast.Not(addedNotOp=True), a.test)
			transferMetaData(a.test, newTest)
			newTest.negated = True
			newTest = deMorganize(newTest)
			a.test = newTest
			(a.body,a.orelse) = (a.orelse,a.body)

		# Then collect all the branches. The leftover orelse is the final else
		branches = [(a.test, a.body, a.global_id)]
		orElse = a.orelse
		while len(orElse) == 1 and type(orElse[0]) == ast.If:
			branches.append((orElse[0].test, orElse[0].body, orElse[0].global_id))
			orElse = orElse[0].orelse

		# If we have branches to order...
		if len(branches) != 1:
			# Sort the branches based on their tests
			# We have to sort carefully because of the possibility for crashing
			isSorted = False
			while not isSorted:
				isSorted = True
				for i in range(len(branches)-1):
					# First, do we even want to swap these two?
					# Branch tests MUST be disjoint to be swapped- otherwise, we break semantics
					if areDisjoint(branches[i][0], branches[i+1][0]) and \
						compareASTs(branches[i][0], branches[i+1][0]) > 0:
						if not (couldCrash(branches[i][0]) or couldCrash(branches[i+1][0])):
							(branches[i],branches[i+1]) = (branches[i+1],branches[i])
							isSorted = False
						# Two values can be swapped if they crash on the SAME thing
						elif couldCrash(branches[i][0]) and couldCrash(branches[i+1][0]):
							# Check to see if they crash on the same things
							l1 = sorted(crashesOn(branches[i][0]), key=functools.cmp_to_key(compareASTs))
							l2 = sorted(crashesOn(branches[i+1][0]), key=functools.cmp_to_key(compareASTs))
							if compareASTs(l1, l2, checkEquality=True) == 0:
								(branches[i],branches[i+1]) = (branches[i+1],branches[i])
								isSorted = False
			# Do our last two branches nicely form an if/else already?
			if len(orElse) == 0 and isNegation(branches[-1][0], branches[-2][0]):
				starter = branches[-1][1] # skip the if
			else:
				starter = [ast.If(branches[-1][0], branches[-1][1], orElse, global_id=branches[-1][2])]
			# Create the new conditional tree
			for i in range(len(branches)-2, -1, -1):
				starter = [ast.If(branches[i][0], branches[i][1], starter, global_id=branches[i][2])]
			a = starter[0]
		return a
	elif type(a) == ast.BoolOp:
		# If all the values are booleans and won't crash, we can sort them
		canSort = True
		for i in range(len(a.values)):
			a.values[i] = orderCommutativeOperations(a.values[i])
			if couldCrash(a.values[i]) or eventualType(a.values[i]) != bool or containsTokenStepString(a.values[i]):
				canSort = False

		if canSort:
			a.values = sorted(a.values, key=functools.cmp_to_key(compareASTs))
		else:
			# Even if there are some problems, we can partially sort. See above
			isSorted = False
			while not isSorted:
				isSorted = True
				for i in range(len(a.values)-1):
					if compareASTs(a.values[i], a.values[i+1]) > 0 and \
						eventualType(a.values[i]) == bool and eventualType(a.values[i+1]) == bool:
						if not (couldCrash(a.values[i]) or couldCrash(a.values[i+1])):
							(a.values[i],a.values[i+1]) = (a.values[i+1],a.values[i])
							isSorted = False
						# Two values can also be swapped if they crash on the SAME thing
						elif couldCrash(a.values[i]) and couldCrash(a.values[i+1]):
							# Check to see if they crash on the same things
							l1 = sorted(crashesOn(a.values[i]), key=functools.cmp_to_key(compareASTs))
							l2 = sorted(crashesOn(a.values[i+1]), key=functools.cmp_to_key(compareASTs))
							if compareASTs(l1, l2, checkEquality=True) == 0:
								(a.values[i],a.values[i+1]) = (a.values[i+1],a.values[i])
								isSorted = False
		return a
	elif type(a) == ast.BinOp:
		top = type(a.op)
		l = a.left = orderCommutativeOperations(a.left)
		r = a.right = orderCommutativeOperations(a.right)

		# Don't reorder if we're currently walking through hint steps
		if containsTokenStepString(l) or containsTokenStepString(r):
			return a

		# TODO: what about possible crashes?
		# Certain operands are commutative
		if (top in [ast.Mult, ast.BitOr, ast.BitXor, ast.BitAnd]) or \
			((top == ast.Add) and ((eventualType(l) in [int, float, bool]) or \
									(eventualType(r) in [int, float, bool]))):
			# Break the chain of binary operations into a list of the
			# operands over the same op, then sort the operands
			operands = [[l, a.op], [r, None]]
			changeMade = True
			i = 0
			while i < len(operands):
				[operand, op] = operands[i]
				if type(operand) == ast.BinOp and type(operand.op) == top:
					operands[i:i+1] = [[operand.left, operand.op], [operand.right, op]]
				else:
					i += 1
			operands = sorted(operands, key=functools.cmp_to_key(lambda x,y : compareASTs(x[0], y[0])))
			for i in range(len(operands)-1): # push all the ops forward
				if operands[i][1] == None:
					operands[i][1] = operands[i+1][1]
					operands[i+1][1] = None
			# Then put them back into a single expression, descending to the left
			left = operands[0][0]
			for i in range(1, len(operands)):
				left = ast.BinOp(left, operands[i-1][1], operands[i][0], orderedBinOp=True)
			transferMetaData(a, left)
			return left
		elif top == ast.Add:
			# This might be concatenation, not addition
			if type( r ) == ast.BinOp and type(r.op) == top:
				# We want the operators to descend to the left
				a.left = orderCommutativeOperations(ast.BinOp(l, r.op, r.left, global_id=r.global_id))
				a.right = r.right
		return a
	elif type(a) == ast.Dict:
		for i in range(len(a.keys)):
			a.keys[i] = orderCommutativeOperations(a.keys[i])
			a.values[i] = orderCommutativeOperations(a.values[i])

		pairs = list(zip(a.keys, a.values))
		pairs.sort(key=functools.cmp_to_key(lambda x,y : compareASTs(x[0],y[0]))) # sort by keys
		k, v = zip(*pairs) if len(pairs) > 0 else ([], [])
		a.keys = list(k)
		a.values = list(v)
		return a
	elif type(a) == ast.Compare:
		l = a.left = orderCommutativeOperations(a.left)
		r = orderCommutativeOperations(a.comparators[0])
		a.comparators = [r]

		# Don't reorder when we're doing hint steps
		if containsTokenStepString(l) or containsTokenStepString(r):
			return a

		if (type(a.ops[0]) in [ast.Eq, ast.NotEq]):
			# Equals and not-equals are commutative
			if compareASTs(l, r) > 0:
				a.left, a.comparators[0] = a.comparators[0], a.left
		elif (type(a.ops[0]) in [ast.Gt, ast.GtE]):
			# We'll always use < and <=, just so everything's the same
			a.ops = [reverse(a.ops[0])]
			a.left, a.comparators[0] = a.comparators[0], a.left
		elif (type(a.ops[0]) in [ast.In, ast.NotIn]):
			if type(r) == ast.List:
				# If it's a list of items, sort the list
				# TODO: should we implement crashable sorting here?
				for i in range(len(r.elts)):
					if couldCrash(r.elts[i]):
						break # don't sort if there'a a crash!
				else:
					r.elts = sorted(r.elts, key=functools.cmp_to_key(compareASTs))
					# Then remove duplicates
					i = 0
					while i < len(r.elts) - 1:
						if compareASTs(r.elts[i], r.elts[i+1], checkEquality=True) == 0:
							r.elts.pop(i+1)
						else:
							i += 1
		return a
	elif type(a) == ast.Call:
		if type(a.func) == ast.Name:
			# These functions are commutative and show up a lot
			if a.func.id in ["min", "max"]:
				crashable = False
				for i in range(len(a.args)):
					a.args[i] = orderCommutativeOperations(a.args[i])
					if couldCrash(a.args[i]) or containsTokenStepString(a.args[i]):
						crashable = True
				# TODO: crashable sorting here?
				if not crashable:
					a.args = sorted(a.args, key=functools.cmp_to_key(compareASTs))
				return a
	return applyToChildren(a, orderCommutativeOperations)

def deMorganize(a):
	"""Apply De Morgan's law throughout the code in order to canonicalize"""
	if not isinstance(a, ast.AST):
		return a
	# We only care about statements beginning with not
	if type(a) == ast.UnaryOp and type(a.op) == ast.Not:
		oper = a.operand
		top = type(oper)

		# not (blah and gah) == (not blah or not gah)
		if top == ast.BoolOp:
			oper.op = negate(oper.op)
			for i in range(len(oper.values)):
				oper.values[i] = deMorganize(negate(oper.values[i]))
			oper.negated = not oper.negated if hasattr(oper, "negated") else True
			transferMetaData(a, oper)
			return oper
		# not a < b == a >= b
		elif top == ast.Compare:
			oper.left = deMorganize(oper.left)
			oper.ops = [negate(oper.ops[0])]
			oper.comparators = [deMorganize(oper.comparators[0])]
			oper.negated = not oper.negated if hasattr(oper, "negated") else True
			transferMetaData(a, oper)
			return oper
		# not not blah == blah
		elif top == ast.UnaryOp and type(oper.op) == ast.Not:
			oper.operand = deMorganize(oper.operand)
			if eventualType(oper.operand) != bool:
				return a
			oper.operand.negated = not oper.operand.negated if hasattr(oper.operand, "negated") else True
			return oper.operand
		elif top == ast.NameConstant:
			if oper.value in [True, False]:
				oper = negate(oper)
				transferMetaData(a, oper)
				return oper
			elif oper.value == None:
				tmp = ast.NameConstant(True)
				transferMetaData(a, tmp)
				tmp.negated = True
				return tmp
			else:
				log("Unknown NameConstant: " + str(oper.value), "bug")

	return applyToChildren(a, deMorganize)

##### CLEANUP FUNCTIONS #####

def cleanupEquals(a):
	"""Gets rid of silly blah == True statements that students make"""
	if not isinstance(a, ast.AST):
		return a
	if type(a) == ast.Call:
		a.func = cleanupEquals(a.func)
		for i in range(len(a.args)):
			# But test expressions don't carry through to function arguments
			a.args[i] = cleanupEquals(a.args[i])
		return a
	elif type(a) == ast.Compare and type(a.ops[0]) in [ast.Eq, ast.NotEq]:
		l = a.left = cleanupEquals(a.left)
		r = cleanupEquals(a.comparators[0])
		a.comparators = [r]
		if type(l) == ast.NameConstant and l.value in [True, False]:
			(l,r) = (r,l)
		# If we have (boolean expression) == True
		if type(r) == ast.NameConstant and r.value in [True, False] and (eventualType(l) == bool):
			# Matching types
			if (type(a.ops[0]) == ast.Eq and r.value == True) or \
				(type(a.ops[0]) == ast.NotEq and r.value == False):
				transferMetaData(a, l) # make sure to keep the original location
				return l
			else:
				tmp = ast.UnaryOp(ast.Not(addedNotOp=True), l)
				transferMetaData(a, tmp)
				return tmp
		else:
			return a
	else:
		return applyToChildren(a, cleanupEquals)

def cleanupBoolOps(a):
	"""When possible, combine adjacent boolean expressions"""
	"""Note- we are assuming that all ops are the first op (as is done in the simplify function)"""
	if not isinstance(a, ast.AST):
		return a
	if type(a) == ast.BoolOp:
		allTypesWork = True
		for i in range(len(a.values)):
			a.values[i] = cleanupBoolOps(a.values[i])
			if eventualType(a.values[i]) != bool or hasattr(a.values[i], "multiComp"):
				allTypesWork = False

		# We can't reduce if the types aren't all booleans
		if not allTypesWork:
			return a

		i = 0
		while i < len(a.values) - 1:
			current = a.values[i]
			next = a.values[i+1]
			# (a and b and c and d) or (a and e and d) == a and ((b and c) or e) and d
			if type(current) == type(next) == ast.BoolOp:
				if type(current.op) == type(next.op):
					minlength = min(len(current.values), len(next.values)) # shortest length

					# First, check for all identical values from the front
					j = 0
					while j < minlength:
						if compareASTs(current.values[j], next.values[j], checkEquality=True) != 0:
							break
						j += 1

					# Same values in both, so get rid of the latter line
					if j == len(current.values) == len(next.values):
						a.values.pop(i+1)
						continue
			i += 1
		### If reduced to one item, just return that item
		return a.values[0] if (len(a.values) == 1) else a
	return applyToChildren(a, cleanupBoolOps)

def cleanupRanges(a):
	"""Remove any range shenanigans, because Python lets you include unneccessary values"""
	if not isinstance(a, ast.AST):
		return a
	if type(a) == ast.Call:
		if type(a.func) == ast.Name:
			if a.func.id in ["range"]:
				if len(a.args) == 3:
					# The step defaults to 1!
					if type(a.args[2]) == ast.Num and a.args[2].n == 1:
						a.args = a.args[:-1]
				if len(a.args) == 2:
					# The start defaults to 0!
					if type(a.args[0]) == ast.Num and a.args[0].n == 0:
						a.args = a.args[1:]
	return applyToChildren(a, cleanupRanges)

def cleanupSlices(a):
	"""Remove any slice shenanigans, because Python lets you include unneccessary values"""
	if not isinstance(a, ast.AST):
		return a
	if type(a) == ast.Subscript:
		if type(a.slice) == ast.Slice:
			# Lower defaults to 0
			if a.slice.lower != None and type(a.slice.lower) == ast.Num and a.slice.lower.n == 0:
				a.slice.lower = None
			# Upper defaults to len(value)
			if a.slice.upper != None and type(a.slice.upper) == ast.Call and \
				type(a.slice.upper.func) == ast.Name and a.slice.upper.func.id == "len":
				if compareASTs(a.value, a.slice.upper.args[0], checkEquality=True) == 0:
					a.slice.upper = None
			# Step defaults to 1
			if a.slice.step != None and type(a.slice.step) == ast.Num and a.slice.step.n == 1:
				a.slice.step = None
	return applyToChildren(a, cleanupSlices)

def cleanupTypes(a):
	"""Remove any unneccessary type mappings"""
	if not isinstance(a, ast.AST):
		return a
	# No need to cast something if it'll be changed anyway by a binary operation
	if type(a) == ast.BinOp:
		a.left = cleanupTypes(a.left)
		a.right = cleanupTypes(a.right)
		# Ints become floats naturally
		if eventualType(a.left) == eventualType(a.right) == float:
			if type(a.right) == ast.Call and type(a.right.func) == ast.Name and \
				a.right.func.id == "float" and len(a.right.args) == 1 and len(a.right.keywords) == 0 and \
				eventualType(a.right.args[0]) in [int, float]:
				a.right = a.right.args[0]
			elif type(a.left) == ast.Call and type(a.left.func) == ast.Name and \
				a.left.func.id == "float" and len(a.left.args) == 1 and len(a.left.keywords) == 0 and \
				eventualType(a.left.args[0]) in [int, float]:
				a.left = a.left.args[0]
		return a
	elif type(a) == ast.Call and type(a.func) == ast.Name and len(a.args) == 1 and len(a.keywords) == 0:
		a.func = cleanupTypes(a.func)
		a.args = [cleanupTypes(a.args[0])]
		# If the type already matches, no need to cast it
		funName = a.func.id
		argType = eventualType(a.args[0])
		if type(a.func) == ast.Name:
			if (funName == "float" and argType == float) or \
				(funName == "int" and argType == int) or \
				(funName == "bool" and argType == bool) or \
				(funName == "str" and argType == str):
				return a.args[0]
	return applyToChildren(a, cleanupTypes)

def turnPositive(a):
	"""Take a negative number and make it positive"""
	if type(a) == ast.UnaryOp and type(a.op) == ast.USub:
		return a.operand
	elif type(a) == ast.Num and type(a.n) != complex and a.n < 0:
		a.n = a.n * -1
		return a
	else:
		log("transformations\tturnPositive\tFailure: " + str(a), "bug")
		return a

def isNegative(a):
	"""Is the give number negative?"""
	if type(a) == ast.UnaryOp and type(a.op) == ast.USub:
		return True
	elif type(a) == ast.Num and type(a.n) != complex and a.n < 0:
		return True
	else:
		return False

def cleanupNegations(a):
	"""Remove unneccessary negations"""
	if not isinstance(a, ast.AST):
		return a
	elif type(a) == ast.BinOp:
		a.left = cleanupNegations(a.left)
		a.right = cleanupNegations(a.right)

		if type(a.op) == ast.Add:
			# x + (-y)
			if isNegative(a.right):
				a.right = turnPositive(a.right)
				a.op = ast.Sub(global_id=a.op.global_id, num_negated=True)
				return a
			# (-x) + y
			elif isNegative(a.left):
				if couldCrash(a.left) and couldCrash(a.right):
					return a # can't switch if it'll change the message
				else:
					(a.left,a.right) = (a.right,turnPositive(a.left))
					a.op = ast.Sub(global_id=a.op.global_id, num_negated=True)
					return a
		elif type(a.op) == ast.Sub:
			# x - (-y)
			if isNegative(a.right):
				a.right = turnPositive(a.right)
				a.op = ast.Add(global_id=a.op.global_id, num_negated=True)
				return a
			elif type(a.right) == ast.BinOp:
				# x - (y + z) = x + (-y - z)
				if type(a.right.op) == ast.Add:
					a.right.left = cleanupNegations(ast.UnaryOp(ast.USub(addedOtherOp=True), a.right.left, addedOther=True))
					a.right.op = ast.Sub(global_id=a.right.op.global_id, num_negated=True)
					a.op = ast.Add(global_id=a.op.global_id, num_negated=True)
					return a
				# x - (y - z) = x + (-y + z) = x + (z - y)
				elif type(a.right.op) == ast.Sub:
					if couldCrash(a.right.left) and couldCrash(a.right.right):
						a.right.left = cleanupNegations(ast.UnaryOp(ast.USub(addedOtherOp=True), a.right.left, addedOther=True))
						a.right.op = ast.Add(global_id=a.right.op.global_id, num_negated=True)
						a.op = ast.Add(global_id=a.op.global_id, num_negated=True)
						return a
					else:
						(a.right.left, a.right.right) = (a.right.right, a.right.left)
						a.op = ast.Add(global_id=a.op.global_id, num_negated=True)
						return a
		# Move negations to the outer part of multiplications
		elif type(a.op) == ast.Mult:
			# -x * -y
			if isNegative(a.left) and isNegative(a.right):
				a.left = turnPositive(a.left)
				a.right = turnPositive(a.right)
				return a
			# -x * y = -(x*y)
			elif isNegative(a.left):
				if eventualType(a.right) in [int, float]:
					a.left = turnPositive(a.left)
					return cleanupNegations(ast.UnaryOp(ast.USub(addedOtherOp=True), a, addedOther=True))
			# x * -y = -(x*y)
			elif isNegative(a.right):
				if eventualType(a.left) in [int, float]:
					a.right = turnPositive(a.right)
					return cleanupNegations(ast.UnaryOp(ast.USub(addedOtherOp=True), a, addedOther=True))
		elif type(a.op) in [ast.Div, ast.FloorDiv]:
			if isNegative(a.left) and isNegative(a.right):
				a.left = turnPositive(a.left)
				a.right = turnPositive(a.right)
				return a
		return a
	elif type(a) == ast.UnaryOp:
		a.operand = cleanupNegations(a.operand)
		if type(a.op) == ast.USub:
			if type(a.operand) == ast.BinOp:
				# -(x + y) = -x - y
				if type(a.operand.op) == ast.Add:
					a.operand.left = cleanupNegations(ast.UnaryOp(ast.USub(addedOtherOp=True), a.operand.left, addedOther=True))
					a.operand.op = ast.Sub(global_id=a.operand.op.global_id, num_negated=True)
					transferMetaData(a, a.operand)
					return a.operand
				# -(x - y) = -x + y = y - x
				elif type(a.operand.op) == ast.Sub:
					if couldCrash(a.operand.left) and couldCrash(a.operand.right):
						a.operand.left = cleanupNegations(ast.UnaryOp(ast.USub(addedOtherOp=True), a.operand.left, addedOther=True))
						a.operand.op = ast.Add(global_id=a.operand.op.global_id, num_negated=True)
						transferMetaData(a, a.operand)
						return a.operand
					else:
						(a.operand.left,a.operand.right) = (a.operand.right,a.operand.left)
						transferMetaData(a, a.operand)
						return a.operand
		return a
	# Special case for absolute value
	elif type(a) == ast.Call and type(a.func) == ast.Name and a.func.id == "abs" and len(a.args) == 1:
		a.args[0] = cleanupNegations(a.args[0])
		if type(a.args[0]) == ast.UnaryOp and type(a.args[0].op) == ast.USub:
			a.args[0] = a.args[0].operand
		elif type(a.args[0]) == ast.BinOp and type(a.args[0].op) == ast.Sub:
			if not (couldCrash(a.args[0].left) and couldCrash(a.args[0].right)) and \
				compareASTs(a.args[0].left, a.args[0].right) > 0:
				(a.args[0].left,a.args[0].right) = (a.args[0].right,a.args[0].left)
		return a
	else:
		return applyToChildren(a, cleanupNegations)

### CONDITIONAL TRANSFORMATIONS ###

def combineConditionals(a):
	"""When possible, combine conditional branches"""
	if not isinstance(a, ast.AST):
		return a
	elif type(a) == ast.If:
		for i in range(len(a.body)):
			a.body[i] = combineConditionals(a.body[i])
		for i in range(len(a.orelse)):
			a.orelse[i] = combineConditionals(a.orelse[i])

		# if a: if b:   x can be - if a and b:    x
		if (len(a.orelse) == 0) and (len(a.body) == 1) and \
			(type(a.body[0]) == ast.If) and (len(a.body[0].orelse) == 0):
			a.test = ast.BoolOp(ast.And(combinedConditionalOp=True), [a.test, a.body[0].test], combinedConditional=True)
			a.body = a.body[0].body
		# if a: x elif b:   x can be - if a or b:   x
		elif (len(a.orelse) == 1) and \
			(type(a.orelse[0]) == ast.If) and (len(a.orelse[0].orelse) == 0):
			if compareASTs(a.body, a.orelse[0].body, checkEquality=True) == 0:
				a.test = ast.BoolOp(ast.Or(combinedConditionalOp=True), [a.test, a.orelse[0].test], combinedConditional=True)
				a.orelse = []
		return a
	else:
		return applyToChildren(a, combineConditionals)

def staticVars(l, vars):
	"""Determines whether the given lines change the given variables"""
	# First, if one of the variables can be modified, there might be a problem
	mutableVars = []
	for var in vars:
		if (not (hasattr(var, "type") and (var.type in [int, float, str, bool]))):
			mutableVars.append(var)

	for i in range(len(l)):
		if type(l[i]) == ast.Assign:
			for var in vars:
				if var.id in allVariableNamesUsed(l[i].targets[0]):
					return False
		elif type(l[i]) == ast.AugAssign:
			for var in vars:
				if var.id in allVariableNamesUsed(l[i].target):
					return False
		elif type(l[i]) in [ast.If, ast.While]:
			if not (staticVars(l[i].body, vars) and staticVars(l[i].orelse, vars)):
				return False
		elif type(l[i]) == ast.For:
			for var in vars:
				if var.id in allVariableNamesUsed(l[i].target):
					return False
			if not (staticVars(l[i].body, vars) and staticVars(l[i].orelse, vars)):
				return False
		elif type(l[i]) in [ast.FunctionDef, ast.ClassDef, ast.Try, ast.With]:
			log("transformations\tstaticVars\tMissing type: " + str(type(l[i])), "bug")

		# If a mutable variable is used, we can't trust it
		for var in mutableVars:
			if var.id in allVariableNamesUsed(l[i]):
				return False
	return True

def getIfBranches(a):
	"""Gets all the branches of an if statement. Will only work if each else has a single line"""
	if type(a) != ast.If:
		return None

	if len(a.orelse) == 0:
		return [a]
	elif len(a.orelse) == 1:
		tmp = getIfBranches(a.orelse[0])
		if tmp == None:
			return None
		return [a] + tmp
	else:
		return None

def allVariablesUsed(a):
	"""Gathers all the variable names used in the ast"""
	if type(a) == list:
		variables = []
		for x in a:
			variables += allVariablesUsed(x)
		return variables

	if not isinstance(a, ast.AST):
		return []
	elif type(a) == ast.Name:
		return [a]
	elif type(a) == ast.Assign:
		variables = allVariablesUsed(a.value)
		for target in a.targets:
			if type(target) == ast.Name:
				pass
			elif type(target) in [ast.Tuple, ast.List]:
				for elt in target.elts:
					if type(elt) == ast.Name:
						pass
					else:
						variables += allVariablesUsed(elt)
			else:
				variables += allVariablesUsed(target)
		return variables
	else:
		variables = []
		for child in ast.iter_child_nodes(a):
			variables += allVariablesUsed(child)
		return variables

def conditionalRedundancy(a):
	"""When possible, remove redundant lines from conditionals and combine conditionals."""
	if type(a) == ast.Module:
		for i in range(len(a.body)):
			if type(a.body[i]) == ast.FunctionDef:
				a.body[i] = conditionalRedundancy(a.body[i])
		return a
	elif type(a) == ast.FunctionDef:
		a.body = conditionalRedundancy(a.body)
		return a

	if type(a) == list:
		i = 0
		while i < len(a):
			stmt = a[i]
			if type(stmt) == ast.If:
				stmt.body = conditionalRedundancy(stmt.body)
				stmt.orelse = conditionalRedundancy(stmt.orelse)

				# If a line appears in both, move it outside the conditionals
				if len(stmt.body) > 0 and len(stmt.orelse) > 0 and compareASTs(stmt.body[-1], stmt.orelse[-1], checkEquality=True) == 0:
					nextLine = stmt.body[-1]
					nextLine.second_global_id = stmt.orelse[-1].global_id
					stmt.body = stmt.body[:-1]
					stmt.orelse = stmt.orelse[:-1]
					stmt.moved_line = nextLine.global_id
					# Remove the if statement if both if and else are empty
					if len(stmt.body) == 0 and len(stmt.orelse) == 0:
						newLine = ast.Expr(stmt.test)
						transferMetaData(stmt, newLine)
						a[i:i+1] = [newLine, nextLine]
					# Switch if and else if if is empty
					elif len(stmt.body) == 0:
						stmt.test = ast.UnaryOp(ast.Not(addedNotOp=True), stmt.test, addedNot=True)
						stmt.body = stmt.orelse
						stmt.orelse = []
						a[i:i+1] = [stmt, nextLine]
					else:
						a[i:i+1] = [stmt, nextLine]
					continue # skip incrementing so that we check the conditional again
				# Join adjacent, disjoint ifs
				elif i+1 < len(a) and type(a[i+1]) == ast.If:
					branches1 = getIfBranches(stmt)
					branches2 = getIfBranches(a[i+1])
					if branches1 != None and branches2 != None:
						# First, check whether any vars used in the second set of branches will be changed by the first set
						testVars = sum(map(lambda b : allVariablesUsed(b.test), branches2), [])
						for branch in branches1:
							if not staticVars(branch.body, testVars):
								break
						else:
							branchCombos = [(x,y) for y in branches2 for x in branches1]
							for (branch1,branch2) in branchCombos:
								if not areDisjoint(branch1.test, branch2.test):
									break
							else:
								# We know the last else branch is empty- fill it with the next tree!
								branches1[-1].orelse = [a[i+1]]
								a.pop(i+1)
								continue # check this conditional again
			elif type(stmt) == ast.FunctionDef:
				stmt.body = conditionalRedundancy(stmt.body)
			elif type(stmt) in [ast.While, ast.For]:
				stmt.body = conditionalRedundancy(stmt.body)
				stmt.orelse = conditionalRedundancy(stmt.orelse)
			elif type(stmt) == ast.ClassDef:
				for x in range(len(stmt.body)):
					if type(stmt.body[x]) == ast.FunctionDef:
						stmt.body[x] = conditionalRedundancy(stmt.body[x])
			elif type(stmt) == ast.Try:
				stmt.body = conditionalRedundancy(stmt.body)
				for x in range(len(stmt.handlers)):
					stmt.handlers[x].body = conditionalRedundancy(stmt.handlers[x].body)
				stmt.orelse = conditionalRedundancy(stmt.orelse)
				stmt.finalbody = conditionalRedundancy(stmt.finalbody)
			elif type(stmt) == ast.With:
				stmt.body = conditionalRedundancy(stmt.body)
			else:
				pass
			i += 1
		return a
	else:
		log("transformations\tconditionalRedundancy\tStrange type: " + str(type(a)), "bug")

def collapseConditionals(a):
	"""When possible, combine adjacent conditionals"""
	if type(a) == ast.Module:
		for i in range(len(a.body)):
			if type(a.body[i]) == ast.FunctionDef:
				a.body[i] = collapseConditionals(a.body[i])
		return a
	elif type(a) == ast.FunctionDef:
		a.body = collapseConditionals(a.body)
		return a

	if type(a) == list:
		l = a
		i = len(l) - 1

		# Go through the lines backwards, since we're collapsing conditionals upwards
		while i >= 0:
			stmt = l[i]
			if type(stmt) == ast.If:
				stmt.body = collapseConditionals(stmt.body)
				stmt.orelse = collapseConditionals(stmt.orelse)

				# First, check to see if we can collapse across the if and its else
				if len(l[i].body) == 1 and len(l[i].orelse) == 1:
					ifLine = l[i].body[0]
					elseLine = l[i].orelse[0]

					# This only works for Assign and Return
					if type(ifLine) == type(elseLine) == ast.Assign and \
						compareASTs(ifLine.targets, elseLine.targets, checkEquality=True) == 0:
						pass
					elif type(ifLine) == ast.Return and type(elseLine) == ast.Return:
						pass
					else:
						i -= 1
						continue # skip past this

					if type(ifLine.value) == type(elseLine.value) == ast.Name and \
						ifLine.value.id in ['True', 'False'] and elseLine.value.id in ['True', 'False']:
						if ifLine.value.id == elseLine.value.id:
							# If they both return the same thing, just replace the if altogether.
							# But keep the test in case it crashes- we'll remove it later
							ifLine.global_id = None # we're replacing the whole if statement
							l[i:i+1] = [ast.Expr(l[i].test, addedOther=True, moved_line=ifLine.global_id), ifLine]
						elif eventualType(l[i].test) == bool:
							testVal = l[i].test
							if ifLine.value.id == 'True':
								newVal = testVal
							else:
								newVal = ast.UnaryOp(ast.Not(addedNotOp=True), testVal, negated=True, collapsedExpr=True)

							if type(ifLine) == ast.Assign:
								newLine = ast.Assign(ifLine.targets, newVal)
							else:
								newLine = ast.Return(newVal)
							transferMetaData(l[i], newLine)
							l[i] = newLine
				# Next, check to see if we can collapse across the if and surrounding lines
				elif len(l[i].body) == 1 and len(l[i].orelse) == 0:
					ifLine = l[i].body[0]
					# First, check to see if the current and prior have the same return bodies
					if i != 0 and type(l[i-1]) == ast.If and \
						len(l[i-1].body) == 1 and len(l[i-1].orelse) == 0 and \
						type(ifLine) == ast.Return and compareASTs(ifLine, l[i-1].body[0], checkEquality=True) == 0:
						# If they do, combine their tests with an Or and get rid of this line
						l[i-1].test = ast.BoolOp(ast.Or(combinedConditionalOp=True), [l[i-1].test, l[i].test], combinedConditional=True)
						l[i-1].second_global_id = l[i].global_id
						l.pop(i)
					# Then, check whether the current and latter lines have the same returns
					elif i != len(l) - 1 and type(ifLine) == type(l[i+1]) == ast.Return and \
						type(ifLine.value) == type(l[i+1].value) == ast.Name and \
						ifLine.value.id in ['True', 'False'] and l[i+1].value.id in ['True', 'False']:
						if ifLine.value.id == l[i+1].value.id:
							# No point in keeping the if line- just use the return
							l[i] = ast.Expr(l[i].test, addedOther=True)
						else:
							if eventualType(l[i].test) == bool:
								testVal = l[i].test
								if ifLine.value.id == 'True':
									newLine = ast.Return(testVal)
								else:
									newLine = ast.Return(ast.UnaryOp(ast.Not(addedNotOp=True), testVal, negated=True, collapsedExpr=True))
								transferMetaData(l[i], newLine)
								l[i] = newLine
								l.pop(i+1) # get rid of the extra return
			elif type(stmt) == ast.FunctionDef:
				stmt.body = collapseConditionals(stmt.body)
			elif type(stmt) in [ast.While, ast.For]:
				stmt.body = collapseConditionals(stmt.body)
				stmt.orelse = collapseConditionals(stmt.orelse)
			elif type(stmt) == ast.ClassDef:
				for i in range(len(stmt.body)):
					if type(stmt.body[i]) == ast.FunctionDef:
						stmt.body[i] = collapseConditionals(stmt.body[i])
			elif type(stmt) == ast.Try:
				stmt.body = collapseConditionals(stmt.body)
				for i in range(len(stmt.handlers)):
					stmt.handlers[i].body = collapseConditionals(stmt.handlers[i].body)
				stmt.orelse = collapseConditionals(stmt.orelse)
				stmt.finalbody = collapseConditionals(stmt.finalbody)
			elif type(stmt) == ast.With:
				stmt.body = collapseConditionals(stmt.body)
			else:
				pass
			i -= 1
		return l
	else:
		log("transformations\tcollapseConditionals\tStrange type: " + str(type(a)), "bug")