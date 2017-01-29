import ast, copy, math
from ..display import *
from ..astTools import *
from ..tools import log
from ..ChangeVector import *
from ..State import *
from ..models import Hint

def getBottomLine(tree):
	# get the last line number included in this AST
	if type(tree) in [ast.Module, ast.Interactive, ast.Suite]:
		if len(tree.body) == 0:
			return 1
		return getBottomLine(tree.body[-1])
	elif type(tree) in [ast.Expression, ast.Lambda]:
		return getBottomLine(tree.body)
	elif type(tree) == ast.FunctionDef:
		# TODO: add returns
		if len(tree.body) == 0:
			argLine = getBottomLine(tree.args)
			if argLine == -1: # -1 if we fcouldn't find it
				if len(tree.decorator_list) == 0:
					return tree.lineno
				return getBottomLine(tree.decorator_list[-1])
			return argLine
		return getBottomLine(tree.body[-1])
	elif type(tree) == ast.ClassDef:
		if len(tree.body) == 0:
			if len(tree.bases) == 0:
				if len(tree.keywords) == 0:
					if len(tree.decorator_list) == 0:
						return tree.lineno
					return getBottomLine(tree.decorator_list[-1])
				return getBottomLine(tree.keywords[-1])
			return getBottomLine(tree.bases[-1])
		return getBottomLine(tree.body[-1])
	elif type(tree) in [ast.Return, ast.Yield]:
		if tree.value == None:
			return tree.lineno
		return getBottomLine(tree.value)
	elif type(tree) == ast.Delete:
		if len(tree.targets) == 0:
			return tree.lineno
		return getBottomLine(tree.targets[-1])
	elif type(tree) in [ast.Assign, ast.AugAssign, ast.Expr,
						ast.Attribute, ast.Subscript, ast.Index, ast.keyword]:
		return getBottomLine(tree.value)
	elif type(tree) in [ast.For, ast.While, ast.If]:
		if len(tree.orelse) == 0:
			if len(tree.body) == 0:
				if type(tree) == ast.For:
					return getBottomLine(tree.iter)
				else:
					return getBottomLine(tree.test)
			return getBottomLine(tree.body[-1])
		return getBottomLine(tree.orelse[-1])
	elif type(tree) == ast.With:
		if len(tree.body) == 0:
			if len(tree.items) == 0:
				return tree.lineno
			return getBottomLine(tree.items[-1])
		return getBottomLine(tree.body[-1])
	elif type(tree) == ast.Raise:
		if tree.exc == None:
			if tree.cause == None:
				return tree.lineno
			return getBottomLine(tree.cause)
		return getBottomLine(tree.exc)
	elif type(tree) == ast.Try:
		if len(tree.finalbody) == 0:
			if len(tree.orelse) == 0:
				if len(tree.handlers) == 0:
					if len(tree.body) == 0:
						return tree.lineno
					return getBottomLine(tree.body[-1])
				return getBottomLine(tree.handlers[-1])
			return getBottomLine(tree.orelse[-1])
		return getBottomLine(tree.finalbody[-1])
	elif type(tree) == ast.Assert:
		if tree.msg == None:
			return getBottomLine(tree.test)
		return getBottomLine(tree.msg)
	elif type(tree) in [ast.Import, ast.ImportFrom, ast.Global, ast.Pass,
						ast.Break, ast.Continue, ast.Num, ast.Str, ast.Bytes, 
						ast.NameConstant, ast.Ellipsis]:
		return tree.lineno
	elif type(tree) == ast.Name:
		if hasattr(tree, "lineno"):
			return tree.lineno
		return -1
	elif type(tree) == ast.BoolOp:
		if len(tree.values) == 0:
			return tree.lineno
		return getBottomLine(tree.values[-1])
	elif type(tree) == ast.BinOp:
		return getBottomLine(tree.right)
	elif type(tree) == ast.UnaryOp:
		return getBottomLine(tree.operand)
	elif type(tree) == ast.IfExp:
		return getBottomLine(tree.orelse)
	elif type(tree) == ast.Dict:
		if len(tree.values) == 0:
			if len(tree.keys) == 0:
				return tree.lineno
			return getBottomLine(tree.keys[-1])
		return getBottomLine(tree.values[-1])
	elif type(tree) in [ast.Set, ast.List, ast.Tuple]:
		if len(tree.elts) == 0:
			return tree.lineno
		return getBottomLine(tree.elts[-1])
	elif type(tree) in [ast.ListComp, ast.SetComp, ast.GeneratorExp]:
		if len(tree.generators) == 0:
			return getBottomLine(tree.elt)
		return getBottomLine(tree.generators[-1])
	elif type(tree) == ast.DictComp:
		if len(tree.generators) == 0:
			return getBottomLine(tree.value)
		return getBottomLine(tree.generators[-1])
	elif type(tree) == ast.Compare:
		if len(tree.comparators) == 0:
			return getBottomLine(tree.left)
		return getBottomLine(tree.comparators[-1])
	elif type(tree) == ast.Call:
		if len(tree.keywords) == 0:
			if len(tree.args) == 0:
				return getBottomLine(tree.func)
			return getBottomLine(tree.args[-1])
		return getBottomLine(tree.keywords[-1])
	elif type(tree) == ast.Slice:
		if tree.step == None:
			if tree.upper == None:
				if tree.lower == None:
					return -1 # we don't know!
				return getBottomLine(tree.lower)
			return getBottomLine(tree.upper)
		return getBottomLine(tree.step)
	elif type(tree) == ast.ExtSlice:
		if len(tree.dims) == 0:
			return -1
		return getBottomLine(tree.dims[-1])
	elif type(tree) == ast.comprehension:
		if len(tree.ifs) == 0:
			return getBottomLine(tree.iter)
		return getBottomLine(tree.ifs[-1])
	elif type(tree) == ast.ExceptHandler:
		if len(tree.body) == 0:
			if tree.name == None:
				if tree.type == None:
					return tree.lineno
				return getBottomLine(tree.type)
			return getBottomLine(tree.name)
		return getBottomLine(tree.body[-1])
	elif type(tree) == ast.arguments:
		if len(tree.kw_defaults) == 0:
			if len(tree.defaults) == 0:
				if len(tree.args) == 0:
					return -1
				return getBottomLine(tree.args[-1])
			return getBottomLine(tree.defaults[-1])
		return getBottomLine(tree.kw_defaults[-1])
	elif type(tree) == ast.arg:
		if tree.annotation == None:
			return tree.lineno
		return getBottomLine(tree.annotation)
	elif type(tree) == ast.alias:
		return -1
	elif type(tree) == ast.withitem:
		if tree.optional_vars == None:
			return getBottomLine(tree.context_expr)
		return getBottomLine(tree.optional_vars)
	else:
		log("MISSING TYPE IN getBottomLine: " + str(type(tree)), "bug")
		return -1

def getLineNumber(tree, path, value):
	# Get the line number where the path leads to
	# TODO: add returns
	if isinstance(value, ast.AST) and hasattr(value, "lineno"):
		return value.lineno

	if len(path) == 0:
		return 0

	# If the value doesn't have the lineno, use traverseTree to try again
	firstStep = path[0]
	if type(firstStep) == tuple:
		# for all tuples, the line should stay the same
		cv = ChangeVector(path, 0, 1)
		location = cv.traverseTree(tree)
		childType = firstStep[0]
		if hasattr(location, childType):
			child = getattr(location, childType)
		else:
			log("generate_message\tgetLineNumber\tBroken path: " + \
				str(path) + printFunction(tree, 0), "bug")
			return getLineNumber(tree, path[1:], None)
		# First, check the locations that don't have linenos
		# (and have children with potentially missing linenos)
		if type(location) == ast.Slice:
			if childType == "lower":
				if child == None:
					if location.upper == None:
						if location.step == None:
							return getLineNumber(tree, path[1:], None)
						return location.step.lineno
					return location.upper.lineno
				return child.lineno
			elif childType == "upper":
				if child == None:
					if location.lower == None:
						if location.step == None:
							return getLineNumber(tree, path[1:], None)
						return location.step.lineno
					return getBottomLine(location.lower)
				return child.lineno
			elif childType == "step":
				if child == None:
					if location.upper == None:
						if location.lower == None:
							return getLineNumber(tree, path[1:], None)
						return getBottomLine(location.lower)
					return getBottomLine(location.upper)
				return child.lineno
		elif type(location) == ast.arguments:
			if childType == "vararg":
				if len(location.args) == 0:
					if len(location.defaults) == 0:
						return getLineNumber(tree, path[1:], None)
					return location.defaults[0].lineno
				return getBottomLine(location.args[-1])
			elif childType == "kwarg":
				if len(location.args) == 0:
					if len(location.defaults) == 0:
						return getLineNumber(tree, path[1:], None)
					return location.defaults[0].lineno
				return getBottomLine(location.args[-1])
			else:
				log("generate_message\tgetLineNumber\tMissing childType for arguments: " + str(childType), "bug")
		elif type(location) == ast.keyword:
			if childType == "arg":
				return location.value.lineno
		elif type(location) == ast.alias:
			return getLineNumber(tree, path[1:], None)

		# Second, check child-types that are optional and
		# may be None
		if child == None:
			if childType == "value":
				if type(location) in [ast.Return, ast.Yield]:
					return location.lineno
			elif childType == "name":
				if type(location) == ast.ExceptHandler:
					if location.type == None:
						return location.lineno
					return getBottomLine(location.type)
			elif childType == "kwargs":
				if location.starargs == None:
					if len(location.keywords) == 0:
						if len(location.args) == 0:
							return getBottomLine(location.func)
						return getBottomLine(location.args[-1])
					return getBottomLine(location.keywords[-1])
				return getBottomLine(location.starargs)
			elif childType == "type":
				return location.lineno
			elif childType == "dest":
				return getBottomLine(location)
			elif childType == "optional_vars":
				return getBottomLine(location.context_expr)
			elif childType == "inst":
				if location.type == None:
					return location.lineno
				return getBottomLine(location.type)
			elif childType == "tback":
				if location.type == None:
					if location.inst == None:
						return location.lineno
					return getBottomLine(location.inst)
				return getBottomLine(location.type)
			elif childType == "msg":
				return getBottomLine(location.test)
			elif childType == "globals":
				return getBottomLine(location.body)
			elif childType == "locals":
				if location.globals == None:
					return getBottomLine(location.body)
				return getBottomLine(location.globals)
			elif childType == "starargs":
				if len(location.keywords) == 0:
					if len(location.args) == 0:
						return getBottomLine(location.func)
					return getBottomLine(location.args[-1])
				return getBottomLine(location.keywords[-1])

		# Third, check non-expr/stmt child types
		if childType in ["module", "level", "id", "n", "s"]:
			return location.lineno
		elif childType in ["nl", "attr", "slice"]:
			return getBottomLine(location)
		elif childType == "name":
			if type(location) in [ast.FunctionDef, ast.ClassDef]:
				if len(location.decorator_list) == 0:
					return location.lineno
				return getBottomLine(location.decorator_list[-1]) + 1
		elif childType == "op":
			if type(location) == ast.AugAssign:
				return getBottomLine(location.target)
			elif type(location) == ast.BoolOp:
				if len(location.values) == 0:
					return location.lineno
				return getBottomLine(location.values[0])
			elif type(location) == ast.BinOp:
				return getBottomLine(location.left)
			elif type(location) == ast.UnaryOp:
				return location.lineno
		elif childType == "args":
			if type(location) == ast.FunctionDef:
				if len(child.args) == 0:
					if len(child.defaults) == 0:
						if len(location.decorator_list) == 0:
							return location.lineno
						return getBottomLine(location.decorator_list[-1]) + 1
					return child.defaults[0].lineno
				return child.args[0].lineno
			elif type(location) == ast.Lambda:
				return location.lineno
		# Once you have the right location,
		# either return its lineno or move up the path
		if hasattr(child, "lineno"):
			return child.lineno
		elif hasattr(location, "lineno"):
			return location.lineno
		else:
			log("MISSING LINENO: " + str(child) + "," + str(location), "bug")
			return getLineNumber(tree, path[1:], None)
	else: # type(firstStep) == int
		if firstStep == -1:
			# a move/swap vector; give the location of the first value
			# move up one, then put the value into the 'last' position
			cv = ChangeVector([-1, value] + path[1:], 0, 1) 
			location = cv.traverseTree(tree)
			if not hasattr(location, "lineno"): # include the value in the path
				return getLineNumber(tree, [value] + path[1:], None)
			return location.lineno
		# Otherwise it's an Add or Delete vector
		elif type(path[1]) == tuple:
			cv = ChangeVector(path[1:], 0, 1)
			location = cv.traverseTree(tree)
			childType = path[1][0]
			if hasattr(location, childType):
				l = getattr(location, childType)
			else:
				log("generate_message\tgetLineNumber\tPath incorrect: " + \
						str(path) + printFunction(tree, 0), "bug")
				return getLineNumber(tree, path[2:], None)
			# First, check the locations that don't have linenos
			if type(location) == ast.ExtSlice: # only child is dims
				if len(l) == 0:
					n = -1
				elif len(l) <= firstStep:
					n = getBottomLine(l[-1])
				else:
					n = getBottomLine(l[firstStep])
				return getLineNumber(tree, path[2:], None) if n == -1 else n

			# Next, look for lists that don't have elements with linenos
			if childType == "names":
				return location.lineno
			elif childType == "ops":
				if len(l) == 0 or firstStep == 0:
					return getBottomLine(location.left)
				elif len(l) <= firstStep:
					return getBottomLine(location.comparators[-1])
				else:
					return getBottomLine(location.comparators[firstStep-1])
			elif childType == "generators":
				if len(l) == 0:
					return getBottomLine(location)
				elif len(l) <= firstStep:
					return getBottomLine(l[-1])
				else:
					return location.generators[firstStep].target.lineno
			elif childType == "keywords":
				if len(l) == 0:
					if type(location) == ast.FunctionDef:
						if len(location.args) == 0:
							return getBottomLine(location.func)
						return getBottomLine(location.args[-1])
					else: # ClassDef
						if len(location.bases) == 0:
							if len(location.decorator_list) == 0:
								return location.lineno
							return getBottomLine(location.decorator_list[-1]) + 1
						return getBottomLine(location.bases[-1])
				elif len(l) <= firstStep:
					return getBottomLine(l[-1])
				else:
					return l[firstStep].value.lineno

			# Now look at all the remaining list-children
			if 0 < len(l) <= firstStep:
				if childType in ["body", "orelse", "decorator_list",
								 "handlers", "finalbody"]:
					return getBottomLine(l[-1]) + 1
				else:
					return getBottomLine(l[-1])
			elif 0 < len(l):
				return l[firstStep].lineno
			else: # len(l) == 0
				# First, the parents without linenos
				if type(location) == ast.comprehension: # only list is ifs
					return getBottomLine(location.iter)
				elif type(location) == ast.arguments:
					if childType == "args":
						if len(location.defaults) == 0:
							if len(location.kwonlyargs) == 0:
								if len(location.kw_defaults) == 0:
									return getLineNumber(tree, path[2:], None)
								return location.kw_defaults[0].lineno
							return location.kwonlyargs[0].lineno
						return location.defaults[0].lineno
					elif childType == "defaults":
						if len(location.args) == 0:
							if len(location.kwonlyargs) == 0:
								if len(location.kw_defaults) == 0:
									return getLineNumber(tree, path[2:], None)
								return getBottomLine(location.kw_defaults[-1])
							return getBottomLine(location.kwonlyargs[-1])
						return getBottomLine(location.args[-1])
					elif childType == "kwonlyargs":
						if len(location.args) == 0:
							if len(location.defaults) == 0:
								if len(location.kw_defaults) == 0:
									return getLineNumber(tree, path[2:], None)
								return getBottomLine(location.kw_defaults[-1])
							return getBottomLine(location.defaults[-1])
						return getBottomLine(location.args[-1])
					elif childType == "kw_defaults":
						if len(location.args) == 0:
							if len(location.defaults) == 0:
								if len(location.kwonlyargs) == 0:
									return getLineNumber(tree, path[2:], None)
								return getBottomLine(location.kwonlyargs[-1])
							return getBottomLine(location.defaults[-1])
						return getBottomLine(location.args[-1])
				# Then everyone else
				if childType in ["values", "elts", "ops", "targets", "keys",
								 "decorator_list"]:
					return location.lineno
				elif childType == "args":
					return getBottomLine(location.func)
				elif childType == "body":
					# need With, Except Handler
					if type(location) in [ast.Module, ast.Interactive,
										  ast.Suite]:
						return 1
					elif type(location) in [ast.FunctionDef, ast.ClassDef,
											ast.With, ast.ExceptHandler]:
						return getBottomLine(location) + 1
					elif type(location) in [ast.While, ast.If]:
						return getBottomLine(location.test) + 1
					elif type(location) == ast.For:
						return getBottomLine(location.iter) + 1
					elif type(location) == ast.Try:
						return location.lineno + 1
					else:
						log("MISSING BODY TYPE: " + str(type(location)), "bug")
				elif childType in ["orelse", "finalbody"]:
					return getBottomLine(location) + 1
				elif childType == "bases":
					if len(location.decorator_list) == 0:
						return location.lineno
					else:
						return getBottomLine(location.decorator_list[-1]) + 1
				elif childType == "handlers":
					if len(location.body) == 0:
						return location.lineno + 1
					else:
						return getBottomLine(location.body[-1]) + 1
				elif childType == "comparators":
					return getBottomLine(location.left)
				else:
					log("MISSING ROW TYPE: " + str(childType), "bug")
		else:
			log("MISSING ROW TYPE IN INT: " + str(path), "bug")

def getColumnNumber(tree, path, value):
	# Get the line number that this path leads to
	if isinstance(value, ast.AST) and hasattr(value, "col_offset"):
		return value.col_offset

	if len(path) == 0:
		return 0

	firstStep = path[0]
	if type(firstStep) == tuple:
		cv = ChangeVector(path, 0, 1)
		location = cv.traverseTree(tree)
		childType = firstStep[0]
		if hasattr(location, childType):
			child = getattr(location, childType)
		else:
			log("generate_message\tgetColumnNumber\tBroken path: " + \
				str(path) + printFunction(tree, 0), "bug")
			return getColumnNumber(tree, path[1:], None)

		# First, check the locations that don't have cols
		# (and have children with potentially missing cols)
		if type(location) == ast.Slice:
			if childType == "lower":
				if location.lower == None:
					if location.upper == None:
						if location.step == None:
							return getColumnNumber(tree, path[1:], None) + \
								len("[")
						return location.step.col_offset - len("::")
					return location.upper.col_offset - len(":")
				return location.lower.col_offset
			elif childType == "upper":
				if location.upper == None:
					if location.lower == None:
						if location.step == None:
							return getColumnNumber(tree, path[1:], None) + \
								len("[:")
						return location.step.col_offset - len(":")
					return location.lower.col_offset + \
						codeLength(location.lower) + len(":")
				return location.upper.col_offset
			elif childType == "step":
				if location.step == None:
					if location.upper == None:
						if location.lower == None:
							return getColumnNumber(tree, path[1:], None) + \
								len("[::")
						return location.lower.col_offset + \
							codeLength(location.lower) + len("::")
					return location.upper.col_offset + \
						codeLength(location.upper) + len(":")
				return location.step.col_offset
		elif type(location) == ast.arguments:
			if childType == "vararg":
				if len(location.args) == 0:
					return getColumnNumber(tree, path[1:], None)
				return location.args[-1].col_offset + \
					codeLength(location.args[-1]) + len(", ")
			elif childType == "kwarg":
				if len(location.args) == 0:
					col = getColumnNumber(tree, path[1:], None)
				else:
					col = location.args[-1].col_offset + \
						codeLength(location.args[-1]) + len(", ")
				if location.vararg != None:
					col += len(location.vararg) + len(", ")
				return col
		elif type(location) == ast.keyword:
			if childType == "arg":
				return location.value.col_offset - len(" : ") - \
					len(location.arg)
		elif type(location) == ast.alias:
			if childType == "name":
				return getColumnNumber(tree, path[1:], None)
			elif childType == "asname":
				return getColumnNumber(tree, path[1:], None) + \
					len(tree.name) + len(" as ")

		# Second, check child-types that are optional and
		# may be None
		if child == None:
			if childType == "value":
				if type(location) == ast.Return:
					return location.col_offset + len("return ")
				elif type(location) == ast.Yield:
					return location.col_offset + len("yield ")
			elif childType == "name":
				if type(location) == ast.ExceptHandler:
					if location.type == None:
						return location.col_offset + len("except ")
					return location.type.col_offset + \
						codeLength(location.type) + len("(")
			elif childType == "kwargs":
				if location.starargs == None:
					if len(location.keywords) == 0:
						if len(location.args) == 0:
							return location.func.col_offset + \
								codeLength(location.func) + len("(")
						return location.args[-1].col_offset + \
							codeLength(location.args[-1]) + len(", ")
					return location.keywords[-1].value.col_offset + \
						codeLength(location.keywords[-1].value) + \
						len(", ")
				return location.starargs.col_offset + \
					codeLength(location.starargs) + len(", ")
			elif childType == "type":
				if type(location) == ast.ExceptHandler:
					return location.lineno + len("except ")
			elif childType == "dest":
				if len(location.values) == 0:
					return location.col_offset + len("print(")
				return location.values[-1].col_offset + \
					codeLength(location.values[-1]) + len(", ")
			elif childType == "optional_vars":
				return location.context_expr.col_offset + \
					codeLength(location.context_expr) + len(" as ")
			elif childType == "exc":
				return location.lineno + len("raise ")
			elif childType == "msg":
				return location.test.col_offset + \
					codeLength(location.test) + len(", ")
			elif childType == "globals":
				return location.body.col_offset + \
					codeLength(location.body) + len(", ")
			elif childType == "locals":
				if location.globals == None:
					return location.body.col_offset + \
						codeLength(location.body) + len(", ")
				return location.globals.col_offset + \
					codeLength(location.globals) + len(", ")
			elif childType == "starargs":
				if len(location.keywords) == 0:
					if len(location.args) == 0:
						return location.func.col_offset + \
							codeLength(location.func) + len("(")
					return location.args[-1].col_offset + \
						codeLength(location.args[-1]) + len(", ")
				return location.keywords[-1].value.col_offset + \
					codeLength(location.keywords[-1].value) + \
					len(", ")

		# Third, check non-expr/stmt child types
		if childType in ["id", "n", "s"]:
			return location.col_offset
		elif childType == "name":
			if type(location) == ast.FunctionDef:
				return location.col_offset + len("def ")
			elif type(location) == ast.ClassDef:
				return location.col_offset + len("class ")
		elif childType == "op":
			if type(location) == ast.AugAssign:
				return location.target.col_offset + \
					codeLength(location.target) + len(" ")
			elif type(location) == ast.BoolOp:
				return location.values[0].col_offset + \
					codeLength(location.values[0]) + len(" ")
			elif type(location) == ast.BinOp:
				return location.left.col_offset + \
					codeLength(location.left) + len(" ")
			elif type(location) == ast.UnaryOp:
				return location.col_offset
		elif childType == "args":
			if type(location) == ast.FunctionDef:
				return location.col_offset + len("def ") + \
					len(location.name) + len("(")
			elif type(location) == ast.Lambda:
				return location.col_offset + len("lambda ")
		elif childType == "nl":
			if location.dest == None:
				if len(location.values) == 0:
					return location.col_offset + len("print(")
				return location.values[-1].col_offset + \
					codeLength(location.values[-1]) + len(", ")
			return location.dest.col_offset + \
				codeLength(location.dest) + len(", ")
		elif childType == "module":
			return location.col_offset + "from " + location.level
		elif childType == "level":
			return location.col_offset + "from "
		elif childType == "attr":
			return location.value.col_offset + \
				codeLength(location.value) + len(".")
		elif childType == "slice":
			return location.value.col_offset + \
				codeLength(location.value) + len("[")

		if hasattr(child, "col_offset"):
			return child.col_offset
		elif hasattr(location, "col_offset"):
			return location.col_offset
		else:
			log("MISSING COL: " + str(child) + "," + str(location), "bug")
			return getLineNumber(tree, path[1:], None)
	elif type(firstStep) == int:
		if firstStep == -1:
			# a move/swap vector; give the location of the first value
			cv = ChangeVector([0, value] + path[1:], 0, 1)
			location = cv.traverseTree(tree)
			return location.col_offset
		elif type(path[1]) == tuple:
			cv = ChangeVector(path[1:], 0, 1)
			location = cv.traverseTree(tree)
			childType = path[1][0]
			if hasattr(location, childType):
				l = getattr(location, childType)
			else:
				log("generate_message\tgetColumnNumber\tBroken path: " + \
					str(path) + printFunction(tree, 0), "bug")
				return getColumnNumber(tree, path[2:], None)

			# First, check the locations that don't have linenos
			if type(location) == ast.ExtSlice: # only child is dims
				col = getColumnNumber(tree, path[2:], None) + len("[")
				for i in range(min(firstStep, len(l))):
					col += codeLength(l[i]) + len(":")
				return col

			# Next, look for lists that don't have elements with linenos
			if childType == "names":
				if type(location) == ast.ImportFrom:
					col = location.col_offset + len("from ") + \
						(location.level if location.level != None else 0) + \
						len(location.module) if location.module != None else 0
				elif type(location) == ast.Import:
					col = location.col_offset + len("import ")
				elif type(location) == ast.Global:
					col = location.col_offset + len("global ")
				# add the length of each of the names
				for i in range(min(firstStep, len(l))):
					col += len(l[i])
				return col
			elif childType == "ops":
				if len(l) == 0 or firstStep == 0:
					return location.left.col_offset + \
						codeLength(location.left) + len(" ")
				else:
					index = -1 if (len(l) <= firstStep) else (firstStep - 1)
					return location.comparators[index].col_offset + \
						codeLength(location.comparators[index]) + \
						len(" ")
			elif childType == "generators":
				if len(l) == 0:
					if type(location) in [ast.ListComp, ast.SetComp, 
										  ast.GeneratorExp]:
						return location.elt.col_offset + \
							codeLength(location.elt) + len(" ")
					elif type(location) == ast.DictComp:
						return location.value.col_offset + \
							codeLength(location.value) + len(" ")
				elif len(l) <= firstStep:
					if len(l[-1].ifs) == 0:
						return l[-1].iter.col_offset + \
							codeLength(l[-1].iter) + len(" ")
					return l[-1].ifs[-1].col_offset + \
						codeLength(l[-1].ifs[-1]) + len(" ")
				else:
					return l[firstStep].target.col_offset
			elif childType == "keywords":
				if len(l) == 0:
					if type(location) == ast.FunctionDef:
						if len(location.args) == 0:
							return location.func.col_offset + \
								codeLength(location.func) + len("(")
						return location.args[-1].col_offset + \
							codeLength(location.args[-1]) + len(", ")
					else: # ClassDef
						if len(location.bases) == 0:
							return location.col_offset + len(location.name) + len("(")
						return location.bases[-1].col_offset + \
							codeLength(location.bases[-1] + len(", "))
				elif len(l) <= firstStep:
					return l[-1].value.col_offset + \
						codeLength(l[-1].value) + len(", ")
				else:
					return l[firstStep].value.col_offset - len(" : ") - \
						len(l[firstStep].arg)

			# First, the parents without cols
			if type(location) == ast.comprehension: # only list is ifs
				if len(l) == 0:
					return location.iter.col_offset + \
						codeLength(location.iter) + len(" ")
				elif len(l) <= firstStep:
					return l[-1].col_offset + codeLength(l[-1]) + \
						len(" ")
				else:
					return l[firstStep].col_offset
			elif type(location) == ast.arguments:
				# TODO: add kwonlyargs and kw_defaults
				if childType == "args":
					if len(l) == 0:
						return getColumnNumber(tree, path[2:], None)
					elif len(l) <= firstStep: # inserting to the back
						return l[-1].col_offset + \
							codeLength(l[-1]) + len(", ")
					else:
						return l[firstStep].col_offset
				elif childType == "defaults":
					if len(l) == 0:
						if len(location.args) == 0:
							col = getColumnNumber(tree, path[2:], None)
						else:
							col = location.args[-1].col_offset + \
								  codeLength(location.args[-1]) + \
								  len(", ")
						if location.vararg != None:
							col += len(location.vararg) + len(", ")
						if location.kwarg != None:
							col += len(location.kwarg) + len(", ")
						return col
					elif len(l) <= firstStep:
						return l[-1].col_offset + \
							codeLength(l[-1]) + len(" ")
					else:
						return l[firstStep].col_offset

			# Then the statements
			if childType == "decorator_list":
				return location.col_offset # outermost level
			elif childType == "body":
				if type(location) in [ast.Module, ast.Interactive, ast.Suite]:
					return 0
				elif type(location) in [ast.FunctionDef, ast.ClassDef, 
										ast.With, ast.ExceptHandler]:
					if len(l) == 0:
						return location.col_offset + 4
					return l[0].col_offset
				elif type(location) in [ast.For, ast.While, ast.If]:
					if len(l) == 0:
						if len(location.orelse) == 0:
							return location.col_offset + 4
						return location.orelse[0].col_offset
					return l[0].col_offset
				elif type(location) == ast.Try:
					if len(l) == 0:
						if len(location.handlers) == 0:
							if len(location.orelse) == 0:
								if len(location.finalbody) == 0:
									return location.col_offset + 4
								return location.finalbody[0].col_offset
							return location.orelse[0].col_offset
						return location.handlers[0].col_offset
					return l[0].col_offset
			elif childType == "orelse":
				if type(location) in [ast.For, ast.While, ast.If]:
					if len(l) == 0:
						if len(location.body) == 0:
							return location.col_offset + 4
						return location.body[0].col_offset
					return l[0].col_offset
				elif type(location) == ast.Try:
					if len(l) == 0:
						if len(location.body) == 0:
							if len(location.handlers) == 0:
								if len(location.finalbody) == 0:
									return location.col_offset + 4
								return location.finalbody[0].col_offset
							return location.handlers[0].col_offset
						return location.body[0].col_offset
					return l[0].col_offset
			elif childType == "handlers":
				if len(l) == 0:
					if len(location.body) == 0:
						if len(location.orelse) == 0:
							return location.col_offset + 4
						return location.orelse[0].col_offset
					return location.body[0].col_offset
				return l[0].col_offset
			elif childType == "finalbody":
				if len(l) == 0:
					if len(location.body) == 0:
						return location.col_offset + 4
					return location.body[0].col_offset
				return l[0].col_offset

			# Then everyone else
			if 0 < len(l) <= firstStep:
				if type(location) == ast.Dict:
					if childType == "values" and \
						len(location.keys) > len(location.values):
						i = -1 if len(location.keys) <= firstStep else firstStep
						return location.keys[i].col_offset + \
							codeLength(location.keys[i]) + len(" : ")
					elif childType == "keys" and \
						len(location.keys) <= len(location.values):
						i = -1 if len(location.values) <= firstStep else firstStep - 1
						return location.values[i].col_offset + \
							codeLength(location.values[i]) + len(", ")

				col = l[-1].col_offset + codeLength(l[-1])
				if childType in ["values", "bases"]:
					pass
				elif childType == "comparators":
					col += len(" ")
				elif childType in ["elts", "targets", "args", "keys"]:
					col += len(", ")
				return col
			elif 0 < len(l):
				return l[firstStep].col_offset
			else: # len(l) == 0
				if childType == "values":
					if type(location) == ast.Dict:
						return location.col_offset + len("{ ")
					elif type(location) == ast.BoolOp:
						return location.col_offset
				elif childType in ["elts", "keys"]:
					return location.col_offset + len("{ ")
				elif childType == "targets":
					if type(location) == ast.Delete:
						return location.col_offset + len("delete ")
					elif type(location) == ast.Assign:
						return location.col_offset
				elif childType == "args":
					return location.func.col_offset + \
						codeLength(location.func) + len("(")
				elif childType == "bases":
					return len("class ") + len(location.name) + len("(")
				elif childType == "comparators":
					return location.left.col_offset + \
						codeLength(location.left) + len(" ") + \
						codeLength(location.ops[0]) + len(" ")
				else:
					log("MISSING COL TYPE IN TUPLE:" + str(childType), "bug")

def getLineNumberFromAst(a):
	if not isinstance(a, ast.AST):
		return None
	if hasattr(a, "lineno"):
		return a.lineno

	line = None
	for child in ast.iter_child_nodes(a):
		line = getLineNumberFromAst(child)
		if line != None:
			return line
	return line

def getFirst(a):
	# Return the first value if the list has at least one element
	return a[0] if len(a) > 0 else None

def formatStatement(a):
	return [a if isStatement(a) else ast.Expr(a)]

def formatStatementList(a, s):
	return [ast.Expr(ast.Str(s))] if len(a) > 0 else []

def formatExpressionList(a, s):
	return [ast.Str(s)] if len(a) > 0 else []

def reduceToOneToken(oldVal, newVal, typeVector):
	keepFirst = type(oldVal) == type(newVal) # if the type matched, keep the first field choice
	if not isinstance(newVal, ast.AST):
		return newVal
	isSubvector = typeVector == "sub" # need to check for subvector to keep

	# all the statements need to be treated a little differently from expressions
	if type(newVal) in [ast.Module, ast.Interactive, ast.Suite]: # adding a function or class item
		tmpBody = formatStatementList(newVal.body, "~program~")
		if keepFirst:
			if len(newVal.body) > 0:
				tmpBody = [reduceToOneToken(getFirst(oldVal.body), newVal.body[0], None)]
		elif isSubvector:
			for i in range(len(newVal.body)):
				if occursIn(oldVal, newVal.body[i]):
					tmpBody = formatStatement(oldVal)
					break
		newVal.body = tmpBody
	elif type(newVal) == ast.Expression:
		tmpBody = ast.Str("~program~")
		if keepFirst:
			tmpBody = reduceToOneToken(oldVal.body, newVal.body, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.body):
				tmpBody = oldVal
		newVal.body = tmpBody
	elif type(newVal) in [ast.FunctionDef, ast.ClassDef]:
		# Keep the name and the args/bases
		tmpBody = formatStatementList(newVal.body, "~body~")
		tmpDecorators = []
		if keepFirst:
			if len(newVal.body) > 0:
				tmpBody = [reduceToOneToken(getFirst(oldVal.body), newVal.body[0], None)]
			elif len(newVal.decorator_list) > 0:
				tmpDecorators = [reduceToOneToken(getFirst(oldVal.decorator_list), newVal.decorator_list[0], None)]
		elif isSubvector:
			for i in range(len(newVal.body)):
				if occursIn(oldVal, newVal.body[i]):
					tmpBody = formatStatement(oldVal)
					break
			else:
				for i in range(len(newVal.decorator_list)):
					if occursIn(oldVal, newVal.decorator_list[i]):
						tmpDecorators = formatStatement(oldVal)
						break
		newVal.body = tmpBody
		newVal.decorator_list = tmpDecorators
	elif type(newVal) in [ast.Return, ast.Attribute, ast.Index]:
		# Leave attr/context alone in Attribute
		tmpValue = ast.Str("~value~")
		if keepFirst:
			tmpValue = reduceToOneToken(oldVal.value, newVal.value, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.value):
				tmpValue = oldVal
		newVal.value = tmpValue
	elif type(newVal) == ast.Delete:
		tmpTargets = [ast.Str("~variable~")]
		if keepFirst:
			if len(newVal.targets) > 0:
				tmpTargets = [reduceToOneToken(getFirst(oldVal.targets), newVal.targets[0], None)]
		elif isSubvector:
			for i in range(len(newVal.targets)):
				if occursIn(oldVal, newVal.targets[i]):
					tmpTargets = [oldVal]
					break
		newVal.targets = tmpTargets
	elif type(newVal) in [ast.Assign, ast.AugAssign]:
		# Leave target[s] and op alone
		tmpValue = ast.Str("~value~")
		if keepFirst:
			tmpValue = reduceToOneToken(oldVal.value, newVal.value, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.value):
				tmpValue = oldVal
		newVal.value = tmpValue
	elif type(newVal) == ast.For:
		# Leave target alone
		tmpIter = ast.Str("~value to iterate over~")
		tmpBody = formatStatementList(newVal.body, "~body~")
		tmpOrelse = formatStatementList(newVal.orelse, "~else body~")
		if keepFirst:
			tmpIter = reduceToOneToken(oldVal.iter, newVal.iter, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.iter):
				tmpIter = oldVal
			else:
				for i in range(len(newVal.body)):
					if occursIn(oldVal, newVal.body[i]):
						tmpBody = formatStatement(oldVal)
						break
				else:
					for i in range(len(newVal.orelse)):
						if occursIn(oldVal, newVal.orelse[i]):
							tmpOrelse = formatStatement(oldVal)
							break
		newVal.iter = tmpIter
		newVal.body = tmpBody
		newVal.orelse = tmpOrelse
	elif type(newVal) in [ast.While, ast.If]:
		tmpTest = ast.Str("~test value~")
		tmpBody = formatStatementList(newVal.body, "~body~")
		tmpOrelse = formatStatementList(newVal.orelse, "~else body~")
		if keepFirst:
			tmpTest = reduceToOneToken(oldVal.test, newVal.test, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.test):
				tmpTest = oldVal
			else:
				for i in range(len(newVal.body)):
					if occursIn(oldVal, newVal.body[i]):
						tmpBody = formatStatement(oldVal)
						break
				else:
					for i in range(len(newVal.orelse)):
						if occursIn(oldVal, newVal.orelse[i]):
							tmpOrelse = formatStatement(oldVal)
							break
		newVal.test = tmpTest
		newVal.body = tmpBody
		newVal.orelse = tmpOrelse
	elif type(newVal) == ast.With:
		tmpItems = [reduceToOneToken(None, newVal.items[0], None)] if len(newVal.items) > 0 else []
		tmpBody = formatStatementList(newVal.body, "~body~")
		if keepFirst:
			if len(newVal.items) > 0:
				tmpItems = [reduceToOneToken(getFirst(oldVal.items), newVal.items[0], None)]
			elif len(newVal.body) > 0:
				tmpBody = [reduceToOneToken(getFirst(oldVal.body), newVal.body[0], None)]
		elif isSubvector:
			for i in range(len(newVal.items)):
				if occursIn(oldVal, newVal.items[i]):
					tmpItems = formatStatement(oldVal)
					break
			else:
				for i in range(len(newVal.body)):
					if occursIn(oldVal, newVal.body[i]):
						tmpBody = formatStatement(oldVal)
						break
		newVal.items = tmpItems
		newVal.body = tmpBody
	elif type(newVal) == ast.Raise:
		tmpExc = ast.Str("~exception~") if newVal.exc != None else None
		tmpCause = None
		if keepFirst:
			if newVal.exc != None:
				tmpExc = reduceToOneToken(oldVal.exc, newVal.exc, None)
			elif newVal.cause != None:
				tmpCause = reduceToOneToken(oldVal.cause, newVal.cause, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.exc):
				tmpExc = oldVal
			elif occursIn(oldVal, newVal.cause):
				tmpCause = oldVal
		newVal.exc = tmpExc
		newVal.cause = tmpCause
	elif type(newVal) == ast.Try: # Be careful with excepthandlers
		tmpBody = formatStatementList(newVal.body, "~body~")
		tmpHandlers = [reduceToOneToken(None, newVal.handlers[0], None)] if len(newVal.handlers) > 0 else []
		tmpOrelse = formatStatementList(newVal.orelse, "~else body~")
		tmpFinalbody = formatStatementList(newVal.finallybody, "~finally body~")
		if keepFirst:
			if len(newVal.body) > 0:
				tmpBody = [reduceToOneToken(getFirst(oldVal.body), newVal.body[0], None)]
			elif len(newVal.handlers) > 0:
				pass # we're already doing this, to be safe
			elif len(newVal.orelse) > 0:
				tmpOrelse = [reduceToOneToken(getFirst(oldVal.orelse), newVal.orelse[0], None)]
			elif len(newVal.finalbody) > 0:
				tmpFinalbody = [reduceToOneToken(getFirst(oldVal.finalbody), newVal.finalbody[0], None)]
		elif isSubvector:
			for i in range(len(newVal.body)):
				if occursIn(oldVal, newVal.body[i]):
					tmpBody = formatStatement(oldVal)
					break
			else:
				for i in range(len(newVal.handlers)):
					if occursIn(oldVal, newVal.handlers[i]):
						tmpHandlers = [reduceToOneToken(oldVal, newVal.handlers[i], "sub")]
						break
				else:
					for i in range(len(newVal.orelse)):
						if occursIn(oldVal, newVal.orelse[i]):
							tmpOrelse = formatStatement(oldVal)
							break
					else:
						for i in range(len(newVal.finalbody)):
							if occursIn(oldVal, newVal.finalbody[i]):
								tmpFinalbody = formatStatement(oldVal)
								break
		newVal.body = tmpBody
		newVal.handlers = tmpHandlers
		newVal.orelse = tmpOrelse
		newVal.finalbody = tmpFinalbody
	elif type(newVal) == ast.Assert:
		tmpTest = ast.Str("~test value~")
		tmpMsg = None
		if keepFirst:
			tmpTest = reduceToOneToken(oldVal.test, newVal.test, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.test):
				tmpTest = oldVal
			elif occursIn(oldVal, newVal.msg):
				tmpMsg = oldVal
		newVal.test = tmpTest
		newVal.msg = tmpMsg
	elif type(newVal) in [ast.Import, ast.ImportFrom, ast.Global]:
		# We can't just insert a string instead of the names, as it's an alias. So we'll just include the first imported name.
		# Leave module and level alone
		newVal.names = newVal.names[:1] if len(newVal.names) > 0 else []
	elif type(newVal) == ast.Expr:
		# Just go down to the next level
		newVal.value = reduceToOneToken(oldVal.value if type(oldVal) == ast.Expr else None, newVal.value, "sub" if isSubvector else None)
	elif type(newVal) == ast.BoolOp:
		# Leave the op alone
		tmpValues = [ast.Str("~left value~"), ast.Str("~right value~")] if len(newVal.values) > 0 else []
		if keepFirst:
			if len(newVal.values) > 0:
				tmpValues = [reduceToOneToken(getFirst(oldVal.values), newVal.values[0], None), ast.Str("~right value~")]
		elif isSubvector:
			for i in range(len(newVal.values)):
				if occursIn(oldVal, newVal.values[i]):
					if i == 0:
						tmpValues = [oldVal, ast.Str("~right value~")]
					elif i == len(newVal.values) - 1:
						tmpValues = [ast.Str("~left value~"), oldVal]
					else:
						tmpValues = [ast.Str("~left value~"), oldVal, ast.Str("~right value~")]
					break
		newVal.values = tmpValues
	elif type(newVal) == ast.BinOp:
		# Leave the op alone
		tmpLeft = ast.Str("~left value~")
		tmpRight = ast.Str("~right value~")
		if keepFirst:
			tmpLeft = reduceToOneToken(oldVal.left, newVal.left, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.left):
				tmpLeft = oldVal
			elif occursIn(oldVal, newVal.right):
				tmpRight = oldVal
		newVal.left = tmpLeft
		newVal.right = tmpRight
	elif type(newVal) == ast.UnaryOp:
		# Leave the op alone
		tmpOperand = ast.Str("~value~")
		if keepFirst:
			tmpOperand = reduceToOneToken(oldVal.operand, newVal.operand, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.operand):
				tmpOperand = oldVal
		newVal.operand = tmpOperand
	elif type(newVal) == ast.Lambda:
		# Leave the args alone
		tmpBody = ast.Str("~function body~")
		if keepFirst:
			tmpBody = reduceToOneToken(oldVal.body, newVal.body, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.body):
				tmpBody = oldVal
		newVal.body = tmpBody
	elif type(newVal) == ast.IfExp:
		tmpBody = ast.Str("~true result~")
		tmpTest = ast.Str("~test value~")
		tmpOrelse = ast.Str("~false result~")
		if keepFirst:
			tmpBody = reduceToOneToken(oldVal.body, newVal.body, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.body):
				tmpBody = oldVal
			elif occursIn(oldVal, newVal.test):
				tmpTest = oldVal
			elif occursIn(oldVal, newVal.orelse):
				tmpOrelse = oldVal
		newVal.body = tmpBody
		newVal.test = tmpTest
		newVal.orelse = tmpOrelse
	elif type(newVal) == ast.Dict:
		tmpKeys = formatExpressionList(newVal.keys, "~key~")
		tmpValues = formatExpressionList(newVal.values, "~value~")
		if keepFirst:
			if len(tmpKeys) > 0:
				tmpKeys = [reduceToOneToken(getFirst(oldVal.keys), newVal.keys[0], None)]
			elif len(tmpValues) > 0:
				tmpValues = [reduceToOneToken(getFirst(oldVal.values), newVal.values[0], None)]
		elif isSubvector:
			for i in range(len(newVal.keys)):
				if occursIn(oldVal, newVal.keys[i]):
					tmpKeys = [oldVal]
					break
			else:
				for i in range(len(newVal.values)):
					if occursIn(oldVal, newVal.values[i]):
						tmpValues = [oldVal]
						break
		newVal.keys = tmpKeys
		newVal.values = tmpValues
	elif type(newVal) in [ast.Set, ast.List, ast.Tuple]:
		# Leave context alone
		tmpElts = formatExpressionList(newVal.elts, "~values~")
		if keepFirst:
			if len(tmpElts) > 0:
				tmpElts = [reduceToOneToken(getFirst(oldVal.elts), newVal.elts[0], None)]
		elif isSubvector:
			for i in range(len(newVal.elts)):
				if occursIn(oldVal, newVal.elts[i]):
					tmpElts = [oldVal]
					break
		newVal.elts = tmpElts
	elif type(newVal) in [ast.ListComp, ast.SetComp, ast.GeneratorExp]: # Be careful with generators
		tmpElt = ast.Str("~value~")
		tmpGenerators = [reduceToOneToken(None, newVal.generators[0], None)] if len(newVal.generators) > 0 else []
		if keepFirst:
			tmpElt = reduceToOneToken(oldVal.elt, newVal.elt, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.elt):
				tmpElt = oldVal
			else:
				for i in range(len(newVal.generators)):
					if occursIn(oldVal, newVal.generators[i]):
						tmpGenerators = [reduceToOneToken(oldVal, newVal.generators[i], "sub")]
						break
		newVal.elt = tmpElt
		newVal.generators = tmpGenerators
	elif type(newVal) == ast.DictComp: # Be careful with generators
		tmpKey = ast.Str("~key~")
		tmpValue = ast.Str("~value~")
		tmpGenerators = [reduceToOneToken(None, newVal.generators[0], None)] if len(newVal.generators) > 0 else []
		if keepFirst:
			tmpKey = reduceToOneToken(oldVal.key, newVal.key, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.key):
				tmpKey = oldVal
			elif occursIn(oldVal, newVal.value):
				tmpValue = oldVal
			else:
				for i in range(len(newVal.generators)):
					if occursIn(oldVal, newVal.generators[i]):
						tmpGenerators = [reduceToOneToken(oldVal, newVal.generators[i], "sub")]
						break
		newVal.key = tmpKey
		newVal.value = tmpValue
		newVal.generators = tmpGenerators
	elif type(newVal) == ast.Yield:
		tmpValue = None
		if keepFirst:
			if newVal.value != None:
				tmpValue = reduceToOneToken(oldVal.value, newVal.value, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.value):
				tmpValue = oldVal
		newVal.value = tmpValue
	elif type(newVal) == ast.Compare:
		# Leave the op alone, but reduce to the number of values
		tmpLeft = ast.Str("~left value~")
		tmpOps = newVal.ops[:1] if len(newVal.ops) > 0 else []
		tmpComparators = [ast.Str("~right value~")]
		if keepFirst:
			tmpLeft = reduceToOneToken(oldVal.left, newVal.left, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.left):
				tmpLeft = oldVal
			else:
				for i in range(len(newVal.comparators)):
					if occursIn(oldVal, newVal.comparators[i]):
						tmpComparators = [oldVal]
						break
		newVal.left = tmpLeft
		newVal.ops = tmpOps
		newVal.comparators = tmpComparators
	elif type(newVal) == ast.Call:
		tmpFunc = ast.Str("~function name~")
		tmpArgs = formatExpressionList(newVal.args, "~args~")
		tmpKeywords = []
		if keepFirst:
			tmpFunc = reduceToOneToken(oldVal.func, newVal.func, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.func):
				tmpFunc = oldVal
			else:
				for i in range(len(newVal.args)):
					if occursIn(oldVal, newVal.args[i]):
						if len(newVal.args) == 1:
							tmpArgs = [oldVal]
						elif i == 0:
							tmpArgs = [oldVal, ast.Str("~remaining args~")]
						elif i == len(newVal.args) - 1:
							tmpArgs = [ast.Str("~starting args~"), oldVal]
						else:
							tmpArgs = [ast.Str("~starting args~"), oldVal, ast.Str("~remaining args~")]
						break
				else:
					for i in range(len(newVal.keywords)):
						if occursIn(oldVal, newVal.keywords[i]):
							tmpKeywords = [oldVal]
							break
		newVal.func = tmpFunc
		newVal.args = tmpArgs
		newVal.keywords = tmpKeywords
	elif type(newVal) == ast.Subscript: # Be careful with slices
		tmpValue = ast.Str("~value~")
		tmpSlice = reduceToOneToken(None, newVal.slice, None)
		if keepFirst:
			tmpValue = reduceToOneToken(oldVal.value, newVal.value, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.value):
				tmpValue = oldVal
			elif occursIn(oldVal, newVal.slice):
				tmpSlice = reduceToOneToken(oldVal, newVal.slice, "sub")
		newVal.value = tmpValue
		newVal.slice = tmpSlice
	elif type(newVal) == ast.Slice:
		tmpLower = None
		tmpUpper = None
		tmpStep = None
		if keepFirst:
			if newVal.lower != None:
				tmpLower = reduceToOneToken(oldVal.lower, newVal.lower, None)
			elif newVal.upper != None:
				tmpUpper = reduceToOneToken(oldVal.upper, newVal.upper, None)
			elif newVal.step != None:
				tmpStep = reduceToOneToken(oldVal.step, newVal.step, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.lower):
				tmpLower = oldVal
			elif occursIn(oldVal, newVal.upper):
				tmpUpper = oldVal
			elif occursIn(oldVal, newVal.step):
				tmpStep = oldVal
		newVal.lower = tmpLower
		newVal.upper = tmpUpper
		newVal.step = tmpStep
	elif type(newVal) == ast.ExtSlice:
		tmpDims = [reduceToOneToken(None, newVal.dims[0], None)] if len(newVal.dims) > 0 else []
		if keepFirst:
			if len(newVal.dims) > 0:
				tmpDims = [reduceToOneToken(getFirst(oldVal.dims), newVal.dims[0], None)]
		elif isSubvector:
			for i in range(len(newVal.dims)):
				if occursIn(oldVal, newVal.dims[i]):
					tmpDims = [reduceToOneToken(oldVal, newVal.dims[i], "sub")]
					break
		newVal.dims = tmpDims
	elif type(newVal) == ast.comprehension:
		# Leave the target alone
		tmpIter = ast.Str("~value to iterate over~")
		tmpIfs = []
		if keepFirst:
			tmpIter = reduceToOneToken(oldVal.iter, newVal.iter, None)
		elif isSubvector:
			if occursIn(oldVal, newVal.iter):
				tmpIter = oldVal
			else:
				for i in range(len(newVal.ifs)):
					if occursIn(oldVal, newVal.ifs[i]):
						tmpIfs = [oldVal]
						break
		newVal.iter = tmpIter
		newVal.ifs = tmpIfs
	elif type(newVal) == ast.ExceptHandler:
		tmpType = ast.Str("~exception type~") if newVal.type != None else None
		tmpName = None
		tmpBody = formatStatementList(newVal.body, "~body~")
		if keepFirst:
			if newVal.type != None:
				tmpType = reduceToOneToken(oldVal.type, newVal.type, None)
			elif newVal.name != None:
				tmpName = reduceToOneToken(oldVal.name, newVal.name, None)
			elif len(newVal.body) > 0:
				tmpBody = [reduceToOneToken(getFirst(oldVal.body), newVal.body[0], None)]
		elif isSubvector:
			if occursIn(oldVal, newVal.type):
				tmpType = oldVal
			elif occursIn(oldVal, newVal.name):
				tmpName = oldVal
			else:
				for i in range(len(newVal.body)):
					if occursIn(oldVal, newVal.body[i]):
						tmpBody = formatStatement(oldVal)
						break
		newVal.type = tmpType
		newVal.name = tmpName
		newVal.body = tmpBody
	elif type(newVal) in [	ast.Pass, ast.Continue, ast.Break, ast.Num, ast.Str, ast.Name, 
							ast.Load, ast.Store, ast.Del, ast.AugLoad, ast.AugStore, ast.Param,
							ast.Ellipsis, ast.And, ast.Or, ast.Add, ast.Sub, ast.Mult, ast.Div,
							ast.Mod, ast.Pow, ast.LShift, ast.RShift, ast.BitOr, ast.BitXor,
							ast.BitAnd, ast.FloorDiv, ast.Invert, ast.Not, ast.UAdd, ast.USub,
							ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot,
							ast.In, ast.NotIn, ast.arguments, ast.keyword, ast.alias]:
		pass
	else:
		log("generate_message\treduceToOneToken\tMissing AST type: " + str(type(newVal)), "bug")
	return newVal

def formatButCatchNone(val):
	if val == None:
		return "None"
	else:
		return formatNode(val)

def formatHints(s, edit, hintLevel, tree):
	"""Format the hints for human consumption"""
	hint = Hint(level=hintLevel)

	if len(edit) == 0:
		hint.message = "No hints could be generated."
		hint.save()
		return hint

	if hintLevel == "next_step" or hintLevel == "half_steps":
		hint.message = ""
		# Minimize the size of cv, without breaking the code
		i = 0
		startTree = edit[0].start
		while i < len(edit):
			cv = edit[i]
			(oldVal, newVal) = (cv.oldSubtree, cv.newSubtree)
			# Different phrases for different change vectors
			if isinstance(cv, AddVector):
				verb1, verb2, verb3 = "add ", "", " to "
				if hintLevel == 1:
					newVal = reduceToOneToken(oldVal, newVal, "add")
				(cv.oldSubtree, cv.newSubtree) = (oldVal, newVal)
				oldStr, newStr = "", formatButCatchNone(newVal)
			elif isinstance(cv, DeleteVector):
				verb1, verb2, verb3 = "remove ", "", " from "
				oldStr, newStr = formatButCatchNone(oldVal), ""
			elif isinstance(cv, SwapVector):
				verb1, verb2, verb3 = "swap ", " with ", " in "
				oldVal, newVal = cv.getSwapees()
				oldStr, newStr = formatButCatchNone(oldVal), formatButCatchNone(newVal)
			elif isinstance(cv, MoveVector):
				verb1, verb2, verb3 = "move ", " behind ", " in "
				oldVal, newVal = cv.getItems()
				oldStr, newStr = formatButCatchNone(oldVal), formatButCatchNone(newVal)
			elif isinstance(cv, SuperVector):
				verb1, verb2, verb3 = "change ", " to ", " in "
				oldStr, newStr = formatButCatchNone(oldVal), formatButCatchNone(newVal)
			else:
				type = ""
				if isinstance(cv, SubVector):
					verb1, verb2, verb3 = "change ", " to ", " in "
					type = "sub"
				else:
					verb1, verb2, verb3 = "replace ", " with ", " in "
					type = "replace"
				if not hasattr(cv, "wasMoveVector") and hintLevel == 1:
					newVal = reduceToOneToken(oldVal, newVal, type)

				oldStr, newStr = formatButCatchNone(oldVal), formatButCatchNone(newVal)
				(cv.oldSubtree, cv.newSubtree) = (oldVal, newVal)

			# Context
			context = formatContext(cv.path, verb3)

			# Position
			line = getLineNumber(cv.start, cv.path, oldVal)
			col = getColumnNumber(cv.start, cv.path, oldVal)
			if i == 0:
				hint.line = line
				hint.col = col
			if line == -1 or col == -1:
				if len(cv.path) == 2 and cv.path[0] == 0:
					line = col = 0
				else:
					log("generate_message\tformatHints\tCouldn't find line/col number: " + str(s.id) + ";" + \
							str(cv) + "\n" + printFunction(cv.start, 0), "bug")

			pos = "line " + str(line) + ", column " + str(col) + " "
			hint.message += "At " + pos + verb1 + "<b>" + oldStr + "</b>" + verb2 + "<b>" + newStr + "</b>" + context + "\n"

			tmp = cv.deepcopy()
			tmp.start = startTree
			t = tmp.applyChange()
			tmpS = State()
			tmpS.tree = t
			tmpS.fun = printFunction(t, 0)
			try:
				ast.parse(tmpS.fun)
				if hintLevel == "next_step" or (hintLevel == "half_steps" and i + 1 >= math.ceil(len(edit) / 2.0)):
					hint.message += "If you need more help, ask for feedback again."
					break
			except:
				pass
			startTree = t
			i += 1
		edit = edit[:i+1]
	if hintLevel == "structure":
		tree = deepcopy(tree)
		for e in edit:
			e.start = tree
			tree = e.applyChange()
		structure = structureTree(tree)
		hint.message = "To correct your code, aim for the following code structure:\n<b>" + printFunction(structure, 0) + "</b>"
		hint.message += "\nIf you need more help, ask for feedback again."
	elif hintLevel == "solution":
		tree = deepcopy(tree)
		for e in edit:
			e.start = tree
			tree = e.applyChange()

		hint.message = "Here is a correct solution to this problem which should be close to your solution: \n<b>" + printFunction(tree, 0) + "</b>"
	hint.save()
	return hint