import ast, copy, uuid
from .transformations import *
from ..namesets import allPythonFunctions
from ..display import printFunction
from ..test import test
from ..astTools import tree_to_str, deepcopy
from ..tools import log

def runGiveIds(a):
	global idCounter
	idCounter = 0
	giveIds(a)

idCounter = 0
def giveIds(a):
	global idCounter
	if isinstance(a, ast.AST):
		if type(a) in [ast.Load, ast.Store, ast.Del, ast.AugLoad, ast.AugStore, ast.Param]:
			return # skip these
		a.global_id = uuid.uuid1()
		idCounter += 1
		for field in a._fields:
			child = getattr(a, field)
			if type(child) == list:
				for i in range(len(child)):
					# Get rid of aliased items
					if hasattr(child[i], "global_id"):
						child[i] = copy.deepcopy(child[i])
					giveIds(child[i])
			else:
				# Get rid of aliased items
				if hasattr(child, "global_id"):
					child = copy.deepcopy(child)
					setattr(a, field, child)
				giveIds(child)

# def exists(d):
# 	for k in d:
# 		if "parsed" not in d[k] or d[k]["parsed"] == False:
# 			return True
# 	return False

# def findGlobalValues(a, globalVars, variables=None):
# 	if variables == None:
# 		variables = set()
# 	if not isinstance(a, ast.AST):
# 		return

# 	if type(a) == ast.FunctionDef:
# 		variables |= set(gatherAssignedVarIds(a.args.args))
# 	elif type(a) == ast.Assign:
# 		variables |= set(gatherAssignedVarIds(a.targets))
# 	elif type(a) == ast.Name:
# 		if a.id not in variables:
# 			globalVars.add(a.id)
# 		return
# 	for child in ast.iter_child_nodes(a):
# 		findGlobalValues(child, globalVars, variables)

# def reduceTree(a, t):
# 	helperD = { a.name : { "tree" : a, "parsed" : False } }
# 	toKeep = []
# 	while exists(helperD):
# 		# Find all necessary external names in the helper dictionary
# 		keys = helperD.keys()
# 		for k in keys:
# 			if "parsed" not in helperD[k]:
# 				# If it isn't in the python namespace...
# 				if k not in (builtInTypes + libraries + allPythonFunctions.keys()):
# 					log("canonicalize\treduceTree\tmissing parsed: " + str(k), "bug")
# 				helperD[k]["parsed"] = True
# 			elif not helperD[k]["parsed"]:
# 				globalNames = set()
# 				findGlobalValues(helperD[k]["tree"], globalNames)
# 				for name in globalNames:
# 					if name not in helperD:
# 						helperD[name] = { }
# 				helperD[k]["parsed"] = True

# 		# go through t and extract all corresponding values
# 		for i in range(len(t.body)):
# 			if i in toKeep:
# 				continue # already checked this one
# 			item = t.body[i]
# 			if item == a:
# 				toKeep.append(i)
# 			elif type(item) in [ast.ImportFrom]:
# 				toKeep.append(i)
# 			elif type(item) in [ast.Assert, ast.Expr]:
# 				continue
# 			elif type(item) in [ast.FunctionDef, ast.ClassDef]:
# 				if item.name in helperD:
# 					toKeep.append(i)
# 					helperD[item.name]["tree"] = item
# 					helperD[item.name]["parsed"] = False
# 			elif type(item) in [ast.Assign, ast.Import]:
# 				if type(item) == ast.Assign:
# 					names = gatherAssignedVarIds(item.targets)
# 				else:
# 					names = map(lambda x : x.asname if x.asname != None else x.name, a.names)
# 				keep = False
# 				for name in names:
# 					if name in helperD:
# 						keep = True
# 						helperD[name]["tree"] = item
# 						helperD[name]["parsed"] = False
# 				if keep:
# 					toKeep.append(i)
# 			elif type(item) in [ast.Delete, ast.AugAssign]:
# 				if type(item) == ast.Delete:
# 					names = gatherAssignedVarIds(item.targets)
# 				else:
# 					names = gatherAssignedVarIds([item.target])
# 				for name in names:
# 					if name in helperD:
# 						toKeep.append(i)
# 						break
# 			else:
# 				log("canonicalize\treduceTree\tMissing type: " + str(type(item)), "bug")
# 	toKeep.sort()
# 	newTree = ast.Module([])
# 	for i in toKeep:
# 		newTree.body.append(t.body[i])
# 	return newTree

def checkGlobalIds(a, l):
	if not isinstance(a, ast.AST):
		return
	elif type(a) in [ ast.Load, ast.Store, ast.Del, ast.AugLoad, ast.AugStore, ast.Param ]:
		return
	if not hasattr(a, "global_id"):
		addedNodes = ["propagatedVariable", "orderedBinOp", 
			"augAssignVal", "augAssignBinOp", 
			"combinedConditional", "combinedConditionalOp", 
			"multiCompPart", "multiCompOp",
			"second_global_id", "moved_line",
			# above this line has individualize functions. below does not.
			"addedNot", "addedNotOp", "addedOther", "addedOtherOp", 
			"collapsedExpr", "removedLines", 
			"helperVar", "helperReturn",
			"typeCastFunction", ]
		for t in addedNodes:
			if hasattr(a, t):
				break
		else: # only enter the else if none of the provided types are an attribute of a
			log("canonicalize\tcheckGlobalIds\tNo global id: " + str(l) + "," + str(a.__dict__) + "," + printFunction(a, 0), "bug")
	for f in ast.iter_child_nodes(a):
		checkGlobalIds(f, l + [type(a)])

def stateDiff(s, funName):
	return
	checkGlobalIds(s.tree, [])
	old_score = s.score
	old_feedback = s.feedback
	old_code = s.code
	s = test(s, forceRetest=True)
	if abs(old_score - s.score) > 0.001:
		log("canonicalize\tstateDiff\tScore mismatch: " + funName + "," + str(old_score) + "," + str(s.score), "bug")
		log(old_feedback + "," + s.feedback, "bug")
		log(old_code, "bug")
		log(printFunction(s.tree), "bug")
		log(printFunction(s.orig_tree), "bug")

def getCanonicalForm(s, given_names=None, argTypes=None):
	#s.tree = deepcopy(s.tree) # no shallow copying! We need to leave the old tree alone

	#giveIds(s.tree)
	#s.orig_tree = deepcopy(s.tree)
	#s.orig_tree_source = tree_to_str(s.tree)
	orig_score = s.score
	orig_feedback = s.feedback

	#crashableCopyPropagation
	transformations = [
				constantFolding,

				cleanupEquals,
				cleanupBoolOps,
				cleanupRanges,
				cleanupSlices,
				cleanupTypes,
				cleanupNegations,

				conditionalRedundancy,
				combineConditionals,
				collapseConditionals,

				copyPropagation,

				deMorganize,
				orderCommutativeOperations,

				deadCodeRemoval
				]

	s.tree = propogateMetadata(s.tree, argTypes, {}, [0])
	stateDiff(s, "propogateMetadata")
	s.tree = simplify(s.tree)
	stateDiff(s, "simplify")
	s.tree = anonymizeNames(s.tree, given_names)
	stateDiff(s, "anonymizeNames")
	oldTree = None
	while compareASTs(oldTree, s.tree, checkEquality=True) != 0:
		oldTree = deepcopy(s.tree)
		helperFolding(s.tree, s.problem.name)
		stateDiff(s, "helperFolding")
		for t in transformations:
			s.tree = t(s.tree) # modify in place
			stateDiff(s, str(t).split()[1])
	s.code = printFunction(s.tree)
	s.score = orig_score
	s.feedback = orig_feedback
	return s