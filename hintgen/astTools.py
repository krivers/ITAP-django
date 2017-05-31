import ast, copy, pickle
from .tools import log
from .namesets import *
from .display import printFunction

def cmp(a, b):
	if type(a) == type(b) == complex:
		return (a.real > b.real) - (a.real < b.real)
	return (a > b) - (a < b)

def tree_to_str(a):
	return repr(pickle.dumps(a))

def str_to_tree(s):
	return pickle.loads(eval(s))

def builtInName(id):
	"""Determines whether the given id is a built-in name"""
	return id in (builtInNames + supportedLibraries + \
		list(allPythonFunctions.keys()) + exceptionClasses)

def isConstant(x):
	"""Determine whether the provided AST is a constant"""
	return (type(x) in [ast.Num, ast.Str, ast.Bytes, ast.NameConstant])

def isIterableType(t):
	"""Can the given type be iterated over"""
	return t in [ dict, list, set, str, bytes, tuple ]

def isStatement(a):
	"""Determine whether the given node is a statement (vs an expression)"""
	return type(a) in [	ast.Module, ast.Interactive, ast.Expression, ast.Suite,
						ast.FunctionDef, ast.ClassDef, ast.Return, ast.Delete,
						ast.Assign, ast.AugAssign, ast.For, ast.While, 
						ast.If, ast.With, ast.Raise, ast.Try, 
					 	ast.Assert, ast.Import, ast.ImportFrom, ast.Global, 
					 	ast.Expr, ast.Pass, ast.Break, ast.Continue ]

def codeLength(a):
	"""Returns the number of characters in this AST"""
	if type(a) == list:
		return sum([codeLength(x) for x in a])
	return len(printFunction(a))

def applyToChildren(a, f):
	"""Apply the given function to all the children of a"""
	if a == None:
		return a
	for field in a._fields:
		child = getattr(a, field)
		if type(child) == list:
			i = 0
			while i < len(child):
				temp = f(child[i])
				if type(temp) == list:
					child = child[:i] + temp + child[i+1:]
					i += len(temp)
				else:
					child[i] = temp
					i += 1
		else:
			child = f(child)
		setattr(a, field, child)
	return a

def occursIn(sub, super):
	"""Does the first AST occur as a subtree of the second?"""
	superStatementTypes = [	ast.Module, ast.Interactive, ast.Suite,
							ast.FunctionDef, ast.ClassDef, ast.For, 
							ast.While, ast.If, ast.With, ast.Try, 
							ast.ExceptHandler ]
	if (not isinstance(super, ast.AST)):
		return False
	if type(sub) == type(super) and compareASTs(sub, super, checkEquality=True) == 0:
		return True
	# we know that a statement can never occur in an expression 
	# (or in a non-statement-holding statement), so cut the search off now to save time.
	if isStatement(sub) and type(super) not in superStatementTypes:
		return False 
	for child in ast.iter_child_nodes(super):
		if occursIn(sub, child):
			return True
	return False

def countOccurances(a, value):
	"""How many instances of this node type appear in the AST?"""
	if type(a) == list:
		return sum([countOccurances(x, value) for x in a])
	if not isinstance(a, ast.AST):
		return 0

	count = 0
	for node in ast.walk(a):
		if isinstance(node, value):
			count += 1
	return count

def countVariables(a, id):
	"""Count the number of times the given variable appears in the AST"""
	if type(a) == list:
		return sum([countVariables(x, id) for x in a])
	if not isinstance(a, ast.AST):
		return 0

	count = 0
	for node in ast.walk(a):
		if type(node) == ast.Name and node.id == id:
			count += 1
	return count

def gatherAllNames(a, keep_orig=True):
	"""Gather all names in the tree (variable or otherwise).
		Names are returned along with their original names 
		(which are used in variable mapping)"""
	if type(a) == list:
		allIds = set()
		for line in a:
			allIds |= gatherAllNames(line)
		return allIds
	if not isinstance(a, ast.AST):
		return set()

	allIds = set()
	for node in ast.walk(a):
		if type(node) == ast.Name:
			origName = node.originalId if (keep_orig and hasattr(node, "originalId")) else None
			allIds |= set([(node.id, origName)])
	return allIds

def gatherAllVariables(a, keep_orig=True):
	"""Gather all variable names in the tree. Names are returned along
		with their original names (which are used in variable mapping)"""
	if type(a) == list:
		allIds = set()
		for line in a:
			allIds |= gatherAllVariables(line)
		return allIds
	if not isinstance(a, ast.AST):
		return set()

	allIds = set()
	for node in ast.walk(a):
		if type(node) == ast.Name or type(node) == ast.arg:
			currentId = node.id if type(node) == ast.Name else node.arg
			# Only take variables
			if not (builtInName(currentId) or hasattr(node, "dontChangeName")):
				origName = node.originalId if (keep_orig and hasattr(node, "originalId")) else None
				if (currentId, origName) not in allIds:
					for pair in allIds:
						if pair[0] == currentId:
							if pair[1] == None:
								allIds -= {pair}
								allIds |= {(currentId, origName)}
							elif origName == None:
								pass
							else:
								log("astTools\tgatherAllVariables\tConflicting originalIds? " + pair[0] + " : " + pair[1] + " , " + origName + "\n" + printFunction(a), "bug")
							break
					else:
						allIds |= {(currentId, origName)}
	return allIds

def gatherAllParameters(a, keep_orig=True):
	"""Gather all parameters in the tree. Names are returned along
		with their original names (which are used in variable mapping)"""
	if type(a) == list:
		allIds = set()
		for line in a:
			allIds |= gatherAllVariables(line)
		return allIds
	if not isinstance(a, ast.AST):
		return set()

	allIds = set()
	for node in ast.walk(a):
		if type(node) == ast.arg:
			origName = node.originalId if (keep_orig and hasattr(node, "originalId")) else None
			allIds |= set([(node.arg, origName)])
	return allIds

def gatherAllHelpers(a, restricted_names):
	"""Gather all helper function names in the tree that have been anonymized"""
	if type(a) != ast.Module:
		return set()
	helpers = set()
	for item in a.body:
		if type(item) == ast.FunctionDef:
			if not hasattr(item, "dontChangeName") and item.name not in restricted_names: # this got anonymized
				origName = item.originalId if hasattr(item, "originalId") else None
				helpers |= set([(item.name, origName)])
	return helpers

def gatherAllFunctionNames(a):
	"""Gather all helper function names in the tree that have been anonymized"""
	if type(a) != ast.Module:
		return set()
	helpers = set()
	for item in a.body:
		if type(item) == ast.FunctionDef:
			origName = item.originalId if hasattr(item, "originalId") else None
			helpers |= set([(item.name, origName)])
	return helpers

def gatherAssignedVars(targets):
	"""Take a list of assigned variables and extract the names/subscripts/attributes"""
	if type(targets) != list:
		targets = [targets]
	newTargets = []
	for target in targets:
		if type(target) in [ast.Tuple, ast.List]:
			newTargets += gatherAssignedVars(target.elts)
		elif type(target) in [ast.Name, ast.Subscript, ast.Attribute]:
			newTargets.append(target)
		else:
			log("astTools\tgatherAssignedVars\tWeird Assign Type: " + str(type(target)),"bug")
	return newTargets

def gatherAssignedVarIds(targets):
	"""Just get the ids of Names"""
	vars = gatherAssignedVars(targets)
	return [y.id for y in filter(lambda x : type(x) == ast.Name, vars)]

def getAllAssignedVarIds(a):
	if not isinstance(a, ast.AST):
		return []
	ids = []
	for child in ast.walk(a):
		if type(child) == ast.Assign:
			ids += gatherAssignedVarIds(child.targets)
		elif type(child) == ast.AugAssign:
			ids += gatherAssignedVarIds([child.target])
		elif type(child) == ast.For:
			ids += gatherAssignedVarIds([child.target])
	return ids

def getAllFunctions(a):
	"""Collects all the functions in the given module"""
	if not isinstance(a, ast.AST):
		return []
	functions = []
	for child in ast.walk(a):
		if type(child) == ast.FunctionDef:
			functions.append(child.name)
	return functions

def getAllImports(a):
	"""Gather all imported module names"""
	if not isinstance(a, ast.AST):
		return []
	imports = []
	for child in ast.walk(a):
		if type(child) == ast.Import:
			for alias in child.names:
				if alias.name in supportedLibraries:
					imports.append(alias.asname if alias.asname != None else alias.name)
				else:
					log("astTools\tgetAllImports\tUnknown library: " + alias.name, "bug")
		elif type(child) == ast.ImportFrom:
			if child.module in supportedLibraries:
				for alias in child.names: # these are all functions
					if alias.name in libraryMap[child.module]:
						imports.append(alias.asname if alias.asname != None else alias.name)
					else:
						log("astTools\tgetAllImports\tUnknown import from name: " + \
									child.module + "," + alias.name, "bug")
			else:
				log("astTools\tgetAllImports\tUnknown library: " + child.module, "bug")
	return imports

def getAllGlobalNames(a):
	# Finds all names that can be accessed at the global level in the AST
	if type(a) != ast.Module:
		return []
	names = []
	for obj in a.body:
		if type(obj) in [ast.FunctionDef, ast.ClassDef]:
			names.append(obj.name)
		elif type(obj) in [ast.Assign, ast.AugAssign]:
			targets = obj.targets if type(obj) == ast.Assign else [obj.target]
			for target in obj.targets:
				if type(target) == ast.Name:
					names.append(target.id)
				elif type(target) in [ast.Tuple, ast.List]:
					for elt in target.elts:
						if type(elt) == ast.Name:
							names.append(elt.id)
		elif type(obj) in [ast.Import, ast.ImportFrom]:
			for module in obj.names:
				names.append(module.asname if module.asname != None else module.name)
	return names

def doBinaryOp(op, l, r):
	"""Perform the given AST binary operation on the values"""
	top = type(op)
	if top == ast.Add:
		return l + r
	elif top == ast.Sub:
		return l - r
	elif top == ast.Mult:
		return l * r
	elif top == ast.Div:
		# Don't bother if this will be a really long float- it won't work properly!
		# Also, in Python 3 this is floating division, so perform it accordingly.
		val = 1.0 * l / r
		if (val * 1e10 % 1.0) != 0:
			raise Exception("Repeating Float")
		return val
	elif top == ast.Mod:
		return l % r
	elif top == ast.Pow:
		return l ** r
	elif top == ast.LShift:
		return l << r
	elif top == ast.RShift:
		return l >> r
	elif top == ast.BitOr:
		return l | r
	elif top == ast.BitXor:
		return l ^ r
	elif top == ast.BitAnd:
		return l & r
	elif top == ast.FloorDiv:
		return l // r

def doUnaryOp(op, val):
	"""Perform the given AST unary operation on the value"""
	top = type(op)
	if top == ast.Invert:
		return ~ val
	elif top == ast.Not:
		return not val
	elif top == ast.UAdd:
		return val
	elif top == ast.USub:
		return -val

def doCompare(op, left, right):
	"""Perform the given AST comparison on the values"""
	top = type(op)
	if top == ast.Eq:
		return left == right
	elif top == ast.NotEq:
		return left != right
	elif top == ast.Lt:
		return left < right
	elif top == ast.LtE:
		return left <= right
	elif top == ast.Gt:
		return left > right
	elif top == ast.GtE:
		return left >= right
	elif top == ast.Is:
		return left is right
	elif top == ast.IsNot:
		return left is not right
	elif top == ast.In:
		return left in right
	elif top == ast.NotIn:
		return left not in right

def num_negate(op):
	top = type(op)
	neg = not op.num_negated if hasattr(op, "num_negated") else True
	if top == ast.Add:
		newOp = ast.Sub()
	elif top == ast.Sub:
		newOp = ast.Add()
	elif top in [ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.LShift, 
				 ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd, ast.FloorDiv]:
		return None # can't negate this
	elif top in [ast.Num, ast.Name]:
		# this is a normal value, so put a - in front of it
		newOp = ast.UnaryOp(ast.USub(addedNeg=True), op)
	else:
		log("astTools\tnum_negate\tUnusual type: " + str(top), "bug")
	transferMetaData(op, newOp)
	newOp.num_negated = neg
	return newOp

def negate(op):
	"""Return the negation of the provided operator"""
	top = type(op)
	neg = not op.negated if hasattr(op, "negated") else True
	if top == ast.And:
		newOp = ast.Or()
	elif top == ast.Or:
		newOp = ast.And()
	elif top == ast.Eq:
		newOp = ast.NotEq()
	elif top == ast.NotEq:
		newOp = ast.Eq()
	elif top == ast.Lt:
		newOp = ast.GtE()
	elif top == ast.GtE:
		newOp = ast.Lt()
	elif top == ast.Gt:
		newOp = ast.LtE()
	elif top == ast.LtE:
		newOp = ast.Gt()
	elif top == ast.Is:
		newOp = ast.IsNot()
	elif top == ast.IsNot:
		newOp = ast.Is()
	elif top == ast.In:
		newOp = ast.NotIn()
	elif top == ast.NotIn:
		newOp = ast.In()
	elif top == ast.NameConstant and op.value in [True, False]:
		op.value = not op.value
		op.negated = neg
		return op
	elif top == ast.Compare:
		if len(op.ops) == 1:
			op.ops[0] = negate(op.ops[0])
			op.negated = neg
			return op
		else:
			values = []
			allOperands = [op.left] + op.comparators
			for i in range(len(op.ops)):
				values.append(ast.Compare(allOperands[i], [negate(op.ops[i])],
										  [allOperands[i+1]], multiCompPart=True))
			newOp = ast.BoolOp(ast.Or(multiCompOp=True), values, multiComp=True)
	elif top == ast.UnaryOp and type(op.op) == ast.Not and \
			eventualType(op.operand) == bool: # this can mess things up type-wise
		return op.operand
	else:
		# this is a normal value, so put a not around it
		newOp = ast.UnaryOp(ast.Not(addedNot=True), op)
	transferMetaData(op, newOp)
	newOp.negated = neg
	return newOp

def couldCrash(a):
	"""Determines whether the given AST could possibly crash"""
	typeCrashes = True # toggle based on whether you care about potential crashes caused by types
	if not isinstance(a, ast.AST):
		return False

	if type(a) == ast.Try:
		for handler in a.handlers:
			for child in ast.iter_child_nodes(handler):
				if couldCrash(child):
					return True
		for other in a.orelse:
			for child in ast.iter_child_nodes(other):
				if couldCrash(child):
					return True
		for line in a.finalbody:
			for child in ast.iter_child_nodes(line):
				if couldCrash(child):
					return True
		return False

	# If any child could crash, this can crash
	for child in ast.iter_child_nodes(a):
		if couldCrash(child):
			return True

	if type(a) == ast.FunctionDef:
		argNames = []
		for arg in a.args.args:
			if arg.arg in argNames: # conflicting arg names!
				return True
			else:
				argNames.append(arg.arg)
	if type(a) == ast.Assign:
		for target in a.targets:
			if type(target) != ast.Name: # can crash if it's a tuple and we can't unpack the value
				return True
	elif type(a) in [ast.For, ast.comprehension]: # check if the target or iter will break things
		if type(a.target) not in [ast.Name, ast.Tuple, ast.List]:
			return True
		elif type(a.target) in [ast.Tuple, ast.List]:
			for x in a.target.elts:
				if type(x) != ast.Name:
					return True
		elif isIterableType(eventualType(a.iter)):
			return True
	elif type(a) == ast.Import:
		for name in a.names:
			if name not in supportedLibraries:
				return True
	elif type(a) == ast.ImportFrom:
		if a.module not in supportedLibraries:
			return True
		if a.level != None:
			return True
		for name in a.names:
			if name not in libraryMap[a.module]:
				return True
	elif type(a) == ast.BinOp:
		l = eventualType(a.left)
		r = eventualType(a.right)
		if type(a.op) == ast.Add:
			if not ((l == r == str) or (l in [int, float] and r in [int, float])):
				return typeCrashes
		elif type(a.op) == ast.Mult:
			if not ((l == str and r == int) or (l == int and r == str) or \
				(l in [int, float] and r in [int, float])):
				return typeCrashes
		elif type(a.op) in [ast.Sub, ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd]:
			if not (l in [int, float] and r in [int, float]):
				return typeCrashes
		elif type(a.op) == ast.Pow:
			if not ((l in [int, float] and r == int) or \
				(l in [int, float] and type(a.right) == ast.Num and \
				 type(a.right.n) != complex and \
				 (a.right.n >= 1 or a.right.n == 0 or a.right.n <= -1))):
				return True
		else: # ast.Div, ast.FloorDiv, ast.Mod
			if type(a.right) == ast.Num and a.right.n != 0:
				if l not in [int, float]:
					return typeCrashes
			else:
				return True # Divide by zero error
	elif type(a) == ast.UnaryOp:
		if type(a.op) in [ast.UAdd, ast.USub]:
			if eventualType(a.operand) not in [int, float]:
				return typeCrashes
		elif type(a.op) == ast.Invert:
			if eventualType(a.operand) != int:
				return typeCrashes
	elif type(a) == ast.Compare:
		if len(a.ops) != len(a.comparators):
			return True
		elif type(a.ops[0]) in [ast.In, ast.NotIn]:
			if not isIterableType(eventualType(a.comparators[0])):
				return True
			elif eventualType(a.comparators[0]) in [str, bytes] and eventualType(a.left) not in [str, bytes]:
				return True
		elif type(a.ops[0]) in [ast.Lt, ast.LtE, ast.Gt, ast.GtE]:
			# In Python3, you can't compare different types. BOOOOOO!!
			firstType = eventualType(a.left)
			if firstType == None:
				return True
			for comp in a.comparators:
				if eventualType(comp) != firstType:
					return True
	elif type(a) == ast.Call:
		env = [] # TODO: what if the environments aren't imported?
		# First, gather up the needed variables
		if type(a.func) == ast.Name:
			funName = a.func.id
			if funName not in builtInSafeFunctions:
				return True
			funDict = builtInFunctions
		elif type(a.func) == ast.Attribute:
			if type(a.func.value) == a.Name and \
				(not hasattr(a.func.value, "varID")) and \
				a.func.value.id in supportedLibraries:
				funName = a.func.attr
				if funName not in safeLibraryMap(a.func.value.id):
					return True
				funDict = libraryMap[a.func.value.id]
			elif eventualType(a.func.value) == str:
				funName = a.func.attr
				if funName not in safeStringFunctions:
					return True
				funDict = builtInStringFunctions
			else: # list and dict are definitely crashable
				return True
		else:
			return True

		if funName in ["max", "min"]:
			return False # Special functions that have infinite args

		# First, load up the arg types
		argTypes = []
		for i in range(len(a.args)):
			eventual = eventualType(a.args[i])
			if (eventual == None and typeCrashes):
				return True
			argTypes.append(eventual)

		if funDict[funName] != None:
			for argSet in funDict[funName]: # the given possibilities of arg types
				if len(argSet) != len(argTypes):
					continue
				if not typeCrashes: # If we don't care about types, stop now
					return False

				for i in range(len(argSet)):
					if not (argSet[i] == argTypes[i] or issubclass(argTypes[i], argSet[i])):
						break
				else: # if all types matched
					return False
			return True # Didn't fit any of the options
	elif type(a) == ast.Subscript: # can only get an index from a string or list
		return eventualType(a.value) not in [str, list, tuple]
	elif type(a) == ast.Name:
		# If it's an undefined variable, it might crash
		if hasattr(a, "randomVar"):
			return True
	elif type(a) == ast.Slice:
		if a.lower != None and eventualType(a.lower) != int:
			return True
		if a.upper != None and eventualType(a.upper) != int:
			return True
		if a.step != None and eventualType(a.step) != int:
			return True
	elif type(a) in [ast.Raise, ast.Assert, ast.Pass, ast.Break, \
					 ast.Continue, ast.Yield, ast.Attribute, ast.ExtSlice, ast.Index, \
					 ast.Starred]:
		# All of these cases can definitely crash.
		return True
	return False

def eventualType(a):
	"""Get the type the expression will eventually be, if possible
		The expression might also crash! But we don't care about that here, 
		we'll deal with it elsewhere.
		Returning 'None' means that we cannot say at the moment"""
	if type(a) in builtInTypes:
		return type(a)
	if not isinstance(a, ast.AST):
		return None

	elif type(a) == ast.BoolOp:
		# In Python, it's the type of all the values in it
		# this may work differently in other languages
		t = eventualType(a.values[0])
		for i in range(1, len(a.values)):
			if eventualType(a.values[i]) != t:
				return None
		return t
	elif type(a) == ast.BinOp:
		l = eventualType(a.left)
		r = eventualType(a.right)
		# It is possible to add/multiply sequences
		if type(a.op) in [ast.Add, ast.Mult]:
			if isIterableType(l):
				return l
			elif isIterableType(r):
				return r
			elif l == float or r == float:
				return float
			elif l == int and r == int:
				return int
			return None
		elif type(a.op) == ast.Div:
			return float # always a float now
		# For others, check if we know whether it's a float or an int
		elif type(a.op) in [ast.FloorDiv, ast.LShift, ast.RShift, ast.BitOr, 
							ast.BitAnd, ast.BitXor]:
			return int
		elif float in [l, r]:
			return float
		elif l == int and r == int:
			return int
		else:
			return None # Otherwise, it could be a float- we don't know
	elif type(a) == ast.UnaryOp:
		if type(a.op) == ast.Invert:
			return int
		elif type(a.op) in [ast.UAdd, ast.USub]:
			return eventualType(a.operand)
		else: # Not op
			return bool
	elif type(a) == ast.Lambda:
		return function
	elif type(a) == ast.IfExp:
		l = eventualType(a.body)
		r = eventualType(a.orelse)
		if l == r:
			return l
		else:
			return None
	elif type(a) in [ast.Dict, ast.DictComp]:
		return dict
	elif type(a) in [ast.Set, ast.SetComp]:
		return set
	elif type(a) in [ast.List, ast.ListComp]:
		return list
	elif type(a) == ast.GeneratorExp:
		return None # can't represent a generator
	elif type(a) == ast.Yield:
		return None # we don't know
	elif type(a) == ast.Compare:
		return bool
	elif type(a) == ast.Call:
		# Go through our different sets of known functions to see if we know the type
		argTypes = [eventualType(x) for x in a.args]
		if type(a.func) == ast.Name:
			funDict = builtInFunctions
			funName = a.func.id
		elif type(a.func) == ast.Attribute:
			# TODO: get a better solution than this
			funName = a.func.attr
			if type(a.func.value) == ast.Name and \
				(not hasattr(a.func.value, "varID")) and \
				a.func.value.id in supportedLibraries:
				funDict = libraryDictMap[a.func.value.id]
				if a.func.value.id in ["string", "str", "list", "dict"] and len(argTypes) > 0:
					argTypes.pop(0) # get rid of the first string arg
			elif eventualType(a.func.value) == str:
				funDict = builtInStringFunctions
			elif eventualType(a.func.value) == list:
				funDict = builtInListFunctions
			elif eventualType(a.func.value) == dict:
				funDict = builtInDictFunctions
			else:
				return None
		else:
			return None

		if funName in ["max", "min"]:
			# If all args are the same type, that's our type
			uniqueTypes = set(argTypes)
			if len(uniqueTypes) == 1:
				return uniqueTypes.pop()
			return None

		if funName in funDict and funDict[funName] != None:
			possibleTypes = []
			for argSet in funDict[funName]:
				if len(argSet) == len(argTypes):
					# All types must match!
					for i in range(len(argSet)):
						if argSet[i] == None or argTypes[i] == None: # We don't know, but that's okay
							continue
						if not (argSet[i] == argTypes[i] or (issubclass(argTypes[i], argSet[i]))):
							break
					else:
						possibleTypes.append(funDict[funName][argSet])
			possibleTypes = set(possibleTypes)
			if len(possibleTypes) == 1: # If there's only one possibility, that's our type!
				return possibleTypes.pop()
		return None
	elif type(a) in [ast.Str, ast.Bytes]:
		if containsTokenStepString(a):
			return None
		return str
	elif type(a) == ast.Num:
		return type(a.n)
	elif type(a) == ast.Attribute:
		return None # we have no way of knowing
	elif type(a) == ast.Subscript:
		# We're slicing the object, so the type will stay the same
		t = eventualType(a.value)
		if t == None:
			return None
		elif t == str:
			return str # indexing a string
		elif t in [list, tuple]:
			if type(a.slice) == ast.Slice:
				return t
			# Otherwise, we need the types of the elements
			if type(a.value) in [ast.List, ast.Tuple]:
				if len(a.value.elts) == 0:
					return None # We don't know
				else:
					eltType = eventualType(a.value.elts[0])
					for elt in a.value.elts:
						if eventualType(elt) != eltType:
							return None # Disagreement!
					return eltType
		elif t in [dict, int]:
			return None
		else:
			log("astTools\teventualType\tUnknown type in subscript: " + str(t), "bug")
		return None # We can't know for now...
	elif type(a) == ast.NameConstant:
		if a.value == True or a.value == False:
			return bool
		elif a.value == None:
			return type(None)
		return None
	elif type(a) == ast.Name:
		if hasattr(a, "type"): # If it's a variable we categorized
			return a.type
		return None
	elif type(a) == ast.Tuple:
		return tuple
	elif type(a) == ast.Starred:
		return None # too complicated
	else:
		log("astTools\teventualType\tUnimplemented type " + str(type(a)), "bug")
		return None

def depthOfAST(a):
	"""Determine the depth of the AST"""
	if not isinstance(a, ast.AST):
		return 0
	m = 0
	for child in ast.iter_child_nodes(a):
		tmp = depthOfAST(child)
		if tmp > m:
			m = tmp
	return m + 1

def compareASTs(a, b, checkEquality=False):
	"""A comparison function for ASTs"""
	# None before others
	if a == b == None:
		return 0
	elif a == None or b == None:
		return -1 if a == None else 1

	if type(a) == type(b) == list:
		if len(a) != len(b):
			return len(a) - len(b)
		for i in range(len(a)):
			r = compareASTs(a[i], b[i], checkEquality=checkEquality)
			if r != 0:
				return r
		return 0

	# AST before primitive
	if (not isinstance(a, ast.AST)) and (not isinstance(b, ast.AST)):
		if type(a) != type(b):
			builtins = [bool, int, float, str, bytes]
			if type(a) not in builtins or type(b) not in builtins:
				log("MISSING BUILT-IN TYPE: " + str(type(a)) + "," + str(type(b)))
			return builtins.index(type(a)) - builtins.index(type(b))
		return cmp(a, b)
	elif (not isinstance(a, ast.AST)) or (not isinstance(b, ast.AST)):
		return -1 if isinstance(a, ast.AST) else 1

	# Order by differing types
	if type(a) != type(b):
		# Here is a brief ordering of types that we care about
		blehTypes = [ ast.Load, ast.Store, ast.Del, ast.AugLoad, ast.AugStore, ast.Param ]
		if type(a) in blehTypes and type(b) in blehTypes:
			return 0
		elif type(a) in blehTypes or type(b) in blehTypes:
			return -1 if type(a) in blehTypes else 1

		types = [	ast.Module, ast.Interactive, ast.Expression, ast.Suite,

					ast.Break, ast.Continue, ast.Pass, ast.Global,
					ast.Expr, ast.Assign, ast.AugAssign, ast.Return,
					ast.Assert, ast.Delete, ast.If, ast.For, ast.While,
					ast.With, ast.Import, ast.ImportFrom, ast.Raise,
					ast.Try, ast.FunctionDef,
					ast.ClassDef,

					ast.BinOp, ast.BoolOp, ast.Compare, ast.UnaryOp,
					ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp,
					ast.Yield, ast.Lambda, ast.IfExp, ast.Call, ast.Subscript,
					ast.Attribute, ast.Dict, ast.List, ast.Tuple,
					ast.Set, ast.Name, ast.Str, ast.Bytes, ast.Num, 
					ast.NameConstant, ast.Starred,

					ast.Ellipsis, ast.Index, ast.Slice, ast.ExtSlice,

					ast.And, ast.Or, ast.Add, ast.Sub, ast.Mult, ast.Div,
					ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr,
					ast.BitXor, ast.BitAnd, ast.FloorDiv, ast.Invert, ast.Not,
					ast.UAdd, ast.USub, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
					ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn,

					ast.alias, ast.keyword, ast.arguments, ast.arg, ast.comprehension,
					ast.ExceptHandler, ast.withitem
				]
		if (type(a) not in types) or (type(b) not in types):
			log("astTools\tcompareASTs\tmissing type:" + str(type(a)) + "," + str(type(b)), "bug")
			return 0
		return types.index(type(a)) - types.index(type(b))

	# Then, more complex expressions- but don't bother with this if we're just checking equality
	if not checkEquality:
		ad = depthOfAST(a)
		bd = depthOfAST(b)
		if ad != bd:
			return bd - ad

	# NameConstants are special
	if type(a) == ast.NameConstant:
		if a.value == None or b.value == None:
			return 1 if a.value != None else (0 if b.value == None else -1) # short and works

		if a.value in [True, False] or b.value in [True, False]:
			return 1 if a.value not in [True, False] else (cmp(a.value, b.value) if b.value in [True, False] else -1)

	if type(a) == ast.Name:
		return cmp(a.id, b.id)

	# Operations and attributes are all ok
	elif type(a) in [	ast.And, ast.Or, ast.Add, ast.Sub, ast.Mult, ast.Div,
						ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr,
						ast.BitXor, ast.BitAnd, ast.FloorDiv, ast.Invert,
						ast.Not, ast.UAdd, ast.USub, ast.Eq, ast.NotEq, ast.Lt,
						ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In,
						ast.NotIn, ast.Load, ast.Store, ast.Del, ast.AugLoad,
						ast.AugStore, ast.Param, ast.Ellipsis, ast.Pass,
						ast.Break, ast.Continue
					]:
		return 0

	# Now compare based on the attributes in the identical types
	attrMap = { ast.Module : ["body"], ast.Interactive : ["body"],
				ast.Expression : ["body"], ast.Suite : ["body"],

				ast.FunctionDef : ["name", "args", "body", "decorator_list", "returns"],
				ast.ClassDef : ["name", "bases", "keywords", "body", "decorator_list"],
				ast.Return : ["value"],
				ast.Delete : ["targets"],
				ast.Assign : ["targets", "value"],
				ast.AugAssign : ["target", "op", "value"],
				ast.For : ["target", "iter", "body", "orelse"],
				ast.While : ["test", "body", "orelse"],
				ast.If : ["test", "body", "orelse"],
				ast.With : ["items", "body"],
				ast.Raise : ["exc", "cause"],
				ast.Try : ["body", "handlers", "orelse", "finalbody"],
				ast.Assert : ["test", "msg"],
				ast.Import : ["names"],
				ast.ImportFrom : ["module", "names", "level"],
				ast.Global : ["names"],
				ast.Expr : ["value"],

				ast.BoolOp : ["op", "values"],
				ast.BinOp : ["left", "op", "right"],
				ast.UnaryOp : ["op", "operand"],
				ast.Lambda : ["args", "body"],
				ast.IfExp : ["test", "body", "orelse"],
				ast.Dict : ["keys", "values"],
				ast.Set : ["elts"],
				ast.ListComp : ["elt", "generators"],
				ast.SetComp : ["elt", "generators"],
				ast.DictComp : ["key", "value", "generators"],
				ast.GeneratorExp : ["elt", "generators"],
				ast.Yield : ["value"],
				ast.Compare : ["left", "ops", "comparators"],
				ast.Call : ["func", "args", "keywords"],
				ast.Num : ["n"],
				ast.Str : ["s"],
				ast.Bytes : ["s"],
				ast.NameConstant : ["value"],
				ast.Attribute : ["value", "attr"],
				ast.Subscript : ["value", "slice"],
				ast.List : ["elts"],
				ast.Tuple : ["elts"],
				ast.Starred : ["value"],

				ast.Slice : ["lower", "upper", "step"],
				ast.ExtSlice : ["dims"],
				ast.Index : ["value"],

				ast.comprehension : ["target", "iter", "ifs"],
				ast.ExceptHandler : ["type", "name", "body"],
				ast.arguments : ["args", "vararg", "kwonlyargs", "kw_defaults", "kwarg", "defaults"],
				ast.arg : ["arg", "annotation"],
				ast.keyword : ["arg", "value"],
				ast.alias : ["name", "asname"],
				ast.withitem : ["context_expr", "optional_vars"] }

	for attr in attrMap[type(a)]:
		r = compareASTs(getattr(a, attr), getattr(b, attr), checkEquality=checkEquality)
		if r != 0:
			return r
	# If all attributes are identical, they're equal
	return 0

def deepcopyList(l):
	"""Deepcopy of a list"""
	if l == None:
		return None
	if isinstance(l, ast.AST):
		return deepcopy(l)
	if type(l) != list:
		log("astTools\tdeepcopyList\tNot a list: " + str(type(l)), "bug")
		return copy.deepcopy(l)

	newList = []
	for line in l:
		newList.append(deepcopy(line))
	return newList

def deepcopy(a):
	"""Let's try to keep this as quick as possible"""
	if a == None:
		return None
	if type(a) == list:
		return deepcopyList(a)
	elif type(a) in [int, float, str, bool]:
		return a
	if not isinstance(a, ast.AST):
		log("astTools\tdeepcopy\tNot an AST: " + str(type(a)), "bug")
		return copy.deepcopy(a)

	g = a.global_id if hasattr(a, "global_id") else None
	cp = None
	# Objects without lineno, col_offset
	if type(a) in [	ast.And, ast.Or, ast.Add, ast.Sub, ast.Mult, ast.Div,
						ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr,
						ast.BitXor, ast.BitAnd, ast.FloorDiv, ast.Invert,
						ast.Not, ast.UAdd, ast.USub, ast.Eq, ast.NotEq, ast.Lt,
						ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In,
						ast.NotIn, ast.Load, ast.Store, ast.Del, ast.AugLoad,
						ast.AugStore, ast.Param
					]:
		return a
	elif type(a) == ast.Module:
		cp = ast.Module(deepcopyList(a.body))
	elif type(a) == ast.Interactive:
		cp = ast.Interactive(deepcopyList(a.body))
	elif type(a) == ast.Expression:
		cp = ast.Expression(deepcopy(a.body))
	elif type(a) == ast.Suite:
		cp = ast.Suite(deepcopyList(a.body))

	elif type(a) == ast.FunctionDef:
		cp = ast.FunctionDef(a.name, deepcopy(a.args), deepcopyList(a.body),
			deepcopyList(a.decorator_list), deepcopy(a.returns))
	elif type(a) == ast.ClassDef:
		cp = ast.ClassDef(a.name, deepcopyList(a.bases), deepcopyList(a.keywords), deepcopyList(a.body),
			deepcopyList(a.decorator_list))
	elif type(a) == ast.Return:
		cp = ast.Return(deepcopy(a.value))
	elif type(a) == ast.Delete:
		cp = ast.Delete(deepcopyList(a.targets))
	elif type(a) == ast.Assign:
		cp = ast.Assign(deepcopyList(a.targets), deepcopy(a.value))
	elif type(a) == ast.AugAssign:
		cp = ast.AugAssign(deepcopy(a.target), deepcopy(a.op),
			deepcopy(a.value))
	elif type(a) == ast.For:
		cp = ast.For(deepcopy(a.target), deepcopy(a.iter),
			deepcopyList(a.body), deepcopyList(a.orelse))
	elif type(a) == ast.While:
		cp = ast.While(deepcopy(a.test), deepcopyList(a.body),
			deepcopyList(a.orelse))
	elif type(a) == ast.If:
		cp = ast.If(deepcopy(a.test), deepcopyList(a.body),
			deepcopyList(a.orelse))
	elif type(a) == ast.With:
		cp = ast.With(deepcopyList(a.items),deepcopyList(a.body))
	elif type(a) == ast.Raise:
		cp = ast.Raise(deepcopy(a.exc), deepcopy(a.cause))
	elif type(a) == ast.Try:
		cp = ast.Try(deepcopyList(a.body), deepcopyList(a.handlers),
			deepcopyList(a.orelse), deepcopyList(a.finalbody))
	elif type(a) == ast.Assert:
		cp = ast.Assert(deepcopy(a.test), deepcopy(a.msg))
	elif type(a) == ast.Import:
		cp = ast.Import(deepcopyList(a.names))
	elif type(a) == ast.ImportFrom:
		cp = ast.ImportFrom(a.module, deepcopyList(a.names), a.level)
	elif type(a) == ast.Global:
		cp = ast.Global(a.names[:])
	elif type(a) == ast.Expr:
		cp = ast.Expr(deepcopy(a.value))
	elif type(a) == ast.Pass:
		cp = ast.Pass()
	elif type(a) == ast.Break:
		cp = ast.Break()
	elif type(a) == ast.Continue:
		cp = ast.Continue()

	elif type(a) == ast.BoolOp:
		cp = ast.BoolOp(a.op, deepcopyList(a.values))
	elif type(a) == ast.BinOp:
		cp = ast.BinOp(deepcopy(a.left), a.op, deepcopy(a.right))
	elif type(a) == ast.UnaryOp:
		cp = ast.UnaryOp(a.op, deepcopy(a.operand))
	elif type(a) == ast.Lambda:
		cp = ast.Lambda(deepcopy(a.args), deepcopy(a.body))
	elif type(a) == ast.IfExp:
		cp = ast.IfExp(deepcopy(a.test), deepcopy(a.body), deepcopy(a.orelse))
	elif type(a) == ast.Dict:
		cp = ast.Dict(deepcopyList(a.keys), deepcopyList(a.values))
	elif type(a) == ast.Set:
		cp = ast.Set(deepcopyList(a.elts))
	elif type(a) == ast.ListComp:
		cp = ast.ListComp(deepcopy(a.elt), deepcopyList(a.generators))
	elif type(a) == ast.SetComp:
		cp = ast.SetComp(deepcopy(a.elt), deepcopyList(a.generators))
	elif type(a) == ast.DictComp:
		cp = ast.DictComp(deepcopy(a.key), deepcopy(a.value),
			deepcopyList(a.generators))
	elif type(a) == ast.GeneratorExp:
		cp = ast.GeneratorExp(deepcopy(a.elt), deepcopyList(a.generators))
	elif type(a) == ast.Yield:
		cp = ast.Yield(deepcopy(a.value))
	elif type(a) == ast.Compare:
		cp = ast.Compare(deepcopy(a.left), a.ops[:],
			deepcopyList(a.comparators))
	elif type(a) == ast.Call:
		cp = ast.Call(deepcopy(a.func), deepcopyList(a.args), deepcopyList(a.keywords))
	elif type(a) == ast.Num:
		cp = ast.Num(a.n)
	elif type(a) == ast.Str:
		cp = ast.Str(a.s)
	elif type(a) == ast.Bytes:
		cp = ast.Bytes(a.s)
	elif type(a) == ast.NameConstant:
		cp = ast.NameConstant(a.value)
	elif type(a) == ast.Attribute:
		cp = ast.Attribute(deepcopy(a.value), a.attr, a.ctx)
	elif type(a) == ast.Subscript:
		cp = ast.Subscript(deepcopy(a.value), deepcopy(a.slice), a.ctx)
	elif type(a) == ast.Name:
		cp = ast.Name(a.id, a.ctx)
	elif type(a) == ast.List:
		cp = ast.List(deepcopyList(a.elts), a.ctx)
	elif type(a) == ast.Tuple:
		cp = ast.Tuple(deepcopyList(a.elts), a.ctx)
	elif type(a) == ast.Starred:
		cp = ast.Starred(deepcopy(a.value), a.ctx)

	elif type(a) == ast.Slice:
		cp = ast.Slice(deepcopy(a.lower), deepcopy(a.upper), deepcopy(a.step))
	elif type(a) == ast.ExtSlice:
		cp = ast.ExtSlice(deepcopyList(a.dims))
	elif type(a) == ast.Index:
		cp = ast.Index(deepcopy(a.value))

	elif type(a) == ast.comprehension:
		cp = ast.comprehension(deepcopy(a.target), deepcopy(a.iter),
			deepcopyList(a.ifs))
	elif type(a) == ast.ExceptHandler:
		cp = ast.ExceptHandler(deepcopy(a.type), a.name, deepcopyList(a.body))
	elif type(a) == ast.arguments:
		cp = ast.arguments(deepcopyList(a.args), deepcopy(a.vararg), 
			deepcopyList(a.kwonlyargs), deepcopyList(a.kw_defaults), 
			deepcopy(a.kwarg), deepcopyList(a.defaults))
	elif type(a) == ast.arg:
		cp = ast.arg(a.arg, deepcopy(a.annotation))
	elif type(a) == ast.keyword:
		cp = ast.keyword(a.arg, deepcopy(a.value))
	elif type(a) == ast.alias:
		cp = ast.alias(a.name, a.asname)
	elif type(a) == ast.withitem:
		cp = ast.withitem(deepcopy(a.context_expr), deepcopy(a.optional_vars))
	else:
		log("astTools\tdeepcopy\tNot implemented: " + str(type(a)), "bug")
		cp = copy.deepcopy(a)

	transferMetaData(a, cp)
	return cp

def exportToJson(a):
	"""Export the ast to json format"""
	if a == None:
		return "null"
	elif type(a) in [int, float]:
		return str(a)
	elif type(a) == str:
		return '"' + a + '"'
	elif not isinstance(a, ast.AST):
		log("astTools\texportToJson\tMissing type: " + str(type(a)), "bug")

	s = "{\n"
	if type(a) in astNames:
		s += '"' + astNames[type(a)] + '": {\n'
		for field in a._fields:
			s += '"' + field + '": '
			value = getattr(a, field)
			if type(value) == list:
				s += "["
				for item in value:
					s += exportToJson(item) + ", "
				if len(value) > 0:
					s = s[:-2]
				s += "]"
			else:
				s += exportToJson(value)
			s += ", "
		if len(a._fields) > 0:
			s = s[:-2]
		s += "}"
	else:
		log("astTools\texportToJson\tMissing AST type: " + str(type(a)), "bug")
	s += "}"
	return s

### ITAP/Canonicalization Functions ###

def isTokenStepString(s):
	"""Determine whether this is a placeholder string"""
	if len(s) < 2:
		return False
	return s[0] == "~" and s[-1] == "~"

def getParentFunction(s):
	underscoreSep = s.split("_")
	if len(underscoreSep) == 1:
		return None
	result = "_".join(underscoreSep[1:])
	if result == "newvar" or result == "global":
		return None
	return result

def isAnonVariable(s):
	"""Specificies whether the given string is an anonymized variable name"""
	preUnderscore = s.split("_")[0] # the part before the function name
	return len(preUnderscore) > 1 and \
		preUnderscore[0] in ["g", "p", "v", "r", "n", "z"] and \
		preUnderscore[1:].isdigit()

def isDefault(a):
	"""Our programs have a default setting of return 42, so we should detect that"""
	if type(a) == ast.Module and len(a.body) == 1:
		a = a.body[0]
	else:
		return False

	if type(a) != ast.FunctionDef:
		return False

	if len(a.body) == 0:
		return True
	elif len(a.body) == 1:
		if type(a.body[0]) == ast.Return:
			if a.body[0].value == None or \
				type(a.body[0].value) == ast.Num and a.body[0].value.n == 42:
				return True
	return False

def transferMetaData(a, b):
	"""Transfer the metadata of a onto b"""
	properties = [	"global_id", "second_global_id", "lineno", "col_offset",
					"originalId", "varID", "variableGlobalId", 
					"randomVar", "propagatedVariable", "loadedVariable", "dontChangeName",
					"reversed", "negated", "inverted",
					"augAssignVal", "augAssignBinOp",
					"combinedConditional", "combinedConditionalOp",
					"multiComp", "multiCompPart", "multiCompMiddle", "multiCompOp",
					"addedNot", "addedNotOp", "addedOther", "addedOtherOp", "addedNeg",
					"collapsedExpr", "removedLines",
					"helperVar", "helperReturnVal", "helperParamAssign", "helperReturnAssign", 
					"orderedBinOp", "typeCastFunction", "moved_line" ]
	for prop in properties:
		if hasattr(a, prop):
			setattr(b, prop, getattr(a, prop))

def assignPropertyToAll(a, prop):
	"""Assign the provided property to all children"""
	if type(a) == list:
		for child in a:
			assignPropertyToAll(child, prop)
	elif isinstance(a, ast.AST):
		for node in ast.walk(a):
			setattr(node, prop, True)

def removePropertyFromAll(a, prop):
	if type(a) == list:
		for child in a:
			removePropertyFromAll(child, prop)
	elif isinstance(a, ast.AST):
		for node in ast.walk(a):
			if hasattr(node, prop):
				delattr(node, prop)

def containsTokenStepString(a):
	"""This is used to keep token-level hint chaining from breaking."""
	if not isinstance(a, ast.AST):
		return False

	for node in ast.walk(a):
		if type(node) == ast.Str and isTokenStepString(node.s):
			return True
	return False

def applyVariableMap(a, variableMap):
	if not isinstance(a, ast.AST):
		return a
	if type(a) == ast.Name:
		if a.id in variableMap:
			a.id = variableMap[a.id]
	elif type(a) in [ast.FunctionDef, ast.ClassDef]:
		if a.name in variableMap:
			a.name = variableMap[a.name]
	return applyToChildren(a, lambda x : applyVariableMap(x, variableMap))

def applyHelperMap(a, helperMap):
	if not isinstance(a, ast.AST):
		return a
	if type(a) == ast.Name:
		if a.id in helperMap:
			a.id = helperMap[a.id]
	elif type(a) == ast.FunctionDef:
		if a.name in helperMap:
			a.name = helperMap[a.name]
	return applyToChildren(a, lambda x : applyHelperMap(x, helperMap))


def astFormat(x, gid=None):
	"""Given a value, turn it into an AST if it's a constant; otherwise, leave it alone."""
	if type(x) in [int, float, complex]:
		return ast.Num(x)
	elif type(x) == bool or x == None:
		return ast.NameConstant(x)
	elif type(x) == type:
		types = { bool : "bool", int : "int", float : "float", 
			complex : "complex", str : "str", bytes : "bytes", unicode : "unicode",
			list : "list", tuple : "tuple", dict : "dict" }
		return ast.Name(types[x], ast.Load())
	elif type(x) == str: # str or unicode
		return ast.Str(x)
	elif type(x) == bytes:
		return ast.Bytes(x)
	elif type(x) == list:
		elts = [astFormat(val) for val in x]
		return ast.List(elts, ast.Load())
	elif type(x) == dict:
		keys = []
		vals = []
		for key in x:
			keys.append(astFormat(key))
			vals.append(astFormat(x[key]))
		return ast.Dict(keys, vals)
	elif type(x) == tuple:
		elts = [astFormat(val) for val in x]
		return ast.Tuple(elts, ast.Load())
	elif type(x) == set:
		elts = [astFormat(val) for val in x]
		if len(elts) == 0: # needs to be a call instead
			return ast.Call(ast.Name("set", ast.Load()), [], [])
		else:
			return ast.Set(elts)
	elif type(x) == slice:
		return ast.Slice(astFormat(x.start), astFormat(x.stop), astFormat(x.step))
	elif isinstance(x, ast.AST):
		return x # Do not change if it's not constant!
	else:
		log("astTools\tastFormat\t" + str(type(x)) + "," + str(x),"bug")
		return None

def basicFormat(x):
	"""Given an AST, turn it into its value if it's constant; otherwise, leave it alone"""
	if type(x) == ast.Num:
		return x.n
	elif type(x) == ast.NameConstant:
		return x.value
	elif type(x) == ast.Str:
		return x.s
	elif type(x) == ast.Bytes:
		return x.s
	return x # Do not change if it's not a constant!

def structureTree(a):
	if type(a) == list:
		for i in range(len(a)):
			a[i] = structureTree(a[i])
		return a
	elif not isinstance(a, ast.AST):
		return a
	else:
		if type(a) == ast.FunctionDef:
			a.name = "~name~"
			a.args = structureTree(a.args)
			a.body = structureTree(a.body)
			a.decorator_list = structureTree(a.decorator_list)
			a.returns = structureTree(a.returns)
		elif type(a) == ast.ClassDef:
			a.name = "~name~"
			a.bases = structureTree(a.bases)
			a.keywords = structureTree(a.keywords)
			a.body = structureTree(a.body)
			a.decorator_list = structureTree(a.decorator_list)
		elif type(a) == ast.AugAssign:
			a.target = structureTree(a.target)
			a.op = ast.Str("~op~")
			a.value = structureTree(a.value)
		elif type(a) == ast.Import:
			a.names = [ast.Str("~module~")]
		elif type(a) == ast.ImportFrom:
			a.module = "~module~"
			a.names = [ast.Str("~names~")]
		elif type(a) == ast.Global:
			a.names = ast.Str("~var~")
		elif type(a) == ast.BoolOp:
			a.op = ast.Str("~op~")
			a.values = structureTree(a.values)
		elif type(a) == ast.BinOp:
			a.op = ast.Str("~op~")
			a.left = structureTree(a.left)
			a.right = structureTree(a.right)
		elif type(a) == ast.UnaryOp:
			a.op = ast.Str("~op~")
			a.operand = structureTree(a.operand)
		elif type(a) == ast.Dict:
			return ast.Str("~dictionary~")
		elif type(a) == ast.Set:
			return ast.Str("~set~")
		elif type(a) == ast.Compare:
			a.ops = [ast.Str("~op~")]*len(a.ops)
			a.left = structureTree(a.left)
			a.comparators = structureTree(a.comparators)
		elif type(a) == ast.Call:
			# leave the function alone
			a.args = structureTree(a.args)
			a.keywords = structureTree(a.keywords)
		elif type(a) == ast.Num:
			return ast.Str("~number~")
		elif type(a) == ast.Str:
			return ast.Str("~string~")
		elif type(a) == ast.Bytes:
			return ast.Str("~bytes~")
		elif type(a) == ast.Attribute:
			a.value = structureTree(a.value)
		elif type(a) == ast.Name:
			a.id = "~var~"
		elif type(a) == ast.List:
			return ast.Str("~list~")
		elif type(a) == ast.Tuple:
			return ast.Str("~tuple~")
		elif type(a) in [ast.And, ast.Or, ast.Add, ast.Sub, ast.Mult, ast.Div, 
							ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr, 
							ast.BitXor, ast.BitAnd, ast.FloorDiv, ast.Invert, 
							ast.Not, ast.UAdd, ast.USub, ast.Eq, ast.NotEq,
							ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, 
							ast.In, ast.NotIn ]:
			return ast.Str("~op~")
		elif type(a) == ast.arguments:
			a.args = structureTree(a.args)
			a.vararg = ast.Str("~arg~") if a.vararg != None else None
			a.kwonlyargs = structureTree(a.kwonlyargs)
			a.kw_defaults = structureTree(a.kw_defaults)
			a.kwarg = ast.Str("~keyword~") if a.kwarg != None else None
			a.defaults = structureTree(a.defaults)
		elif type(a) == ast.arg:
			a.arg = "~arg~"
			a.annotation = structureTree(a.annotation)
		elif type(a) == ast.keyword:
			a.arg = "~keyword~"
			a.value = structureTree(a.value)
		elif type(a) == ast.alias:
			a.name = "~name~"
			a.asname = "~asname~" if a.asname != None else None
		else:
			for field in a._fields:
				setattr(a, field, structureTree(getattr(a, field)))
		return a



