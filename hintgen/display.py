import ast
from .tools import log

#===============================================================================
# These functions are used for displaying ASTs. printAst displays the tree,
# while printFunction displays the syntax
#===============================================================================

# TODO: add AsyncFunctionDef, AsyncFor, AsyncWith, AnnAssign, Nonlocal, Await, YieldFrom, FormattedValue, JoinedStr, Starred

def printFunction(a, indent=0):
	s = ""
	if a == None:
		return ""
	if not isinstance(a, ast.AST):
		log("display\tprintFunction\tNot AST: " + str(type(a)) + "," + str(a), "bug")
		return str(a)

	t = type(a)
	if t in [ast.Module, ast.Interactive, ast.Suite]:
		for line in a.body:
			s += printFunction(line, indent)
	elif t == ast.Expression:
		s += printFunction(a.body, indent)
	elif t == ast.FunctionDef:
		for dec in a.decorator_list:
			s += (indent * 4 * " ") + "@" + printFunction(dec, indent) + "\n"
		s += (indent * 4 * " ") + "def " + a.name + "(" + \
				printFunction(a.args, indent) + "):\n"
		for stmt in a.body:
			s += printFunction(stmt, indent+1)
		# TODO: returns
	elif t == ast.ClassDef:
		for dec in a.decorator_list:
			s += (indent * 4 * " ") + "@" + printFunction(dec, indent) + "\n"
		s += (indent * 4 * " ") + "class " + a.name
		if len(a.bases) > 0 or len(a.keywords) > 0:
			s += "("
			for base in a.bases:
				s += printFunction(base, indent) + ", "
			for keyword in a.keywords:
				s += printFunction(keyword, indent) + ", "
			s += s[:-2] + ")"
		s += ":\n"
		for stmt in a.body:
			s += printFunction(stmt, indent+1)
	elif t == ast.Return:
		s += (indent * 4 * " ") + "return " + \
				printFunction(a.value, indent) + "\n"
	elif t == ast.Delete:
		s += (indent * 4 * " ") + "del "
		for target in a.targets:
			s += printFunction(target, indent) + ", "
		if len(a.targets) >= 1:
			s = s[:-2]
		s += "\n"
	elif t == ast.Assign:
		s += (indent * 4 * " ")
		for target in a.targets:
			s += printFunction(target, indent) + " = "
		s += printFunction(a.value, indent) + "\n"
	elif t == ast.AugAssign:
		s += (indent * 4 * " ")
		s += printFunction(a.target, indent) + " " + \
				printFunction(a.op, indent) + "= " + \
				printFunction(a.value, indent) + "\n"
	elif t == ast.For:
		s += (indent * 4 * " ")
		s += "for " + \
				printFunction(a.target, indent) + " in " + \
				printFunction(a.iter, indent) + ":\n"
		for line in a.body:
			s += printFunction(line, indent + 1)
		if len(a.orelse) > 0:
			s += (indent * 4 * " ")
			s += "else:\n"
			for line in a.orelse:
				s += printFunction(line, indent + 1)
	elif t == ast.While:
		s += (indent * 4 * " ")
		s += "while " + printFunction(a.test, indent) + ":\n"
		for line in a.body:
			s += printFunction(line, indent + 1)
		if len(a.orelse) > 0:
			s += (indent * 4 * " ")
			s += "else:\n"
			for line in a.orelse:
				s += printFunction(line, indent + 1)
	elif t == ast.If:
		s += (indent * 4 * " ")
		s += "if " + printFunction(a.test, indent) + ":\n"
		for line in a.body:
			s += printFunction(line, indent + 1)
		branch = a.orelse
		# elifs
		while len(branch) == 1 and type(branch[0]) == ast.If:
			s += (indent * 4 * " ")
			s += "elif " + printFunction(branch[0].test, indent) + ":\n"
			for line in branch[0].body:
				s += printFunction(line, indent + 1)
			branch = branch[0].orelse
		if len(branch) > 0:
			s += (indent * 4 * " ")
			s += "else:\n"
			for line in branch:
				s += printFunction(line, indent + 1)
	elif t == ast.With:
		s += (indent * 4 * " ")
		s += "with "
		for item in a.items:
			s += printFunction(item, indent) + ", "
		if len(a.items) > 0:
			s = s[:-2]
		s += ":\n"
		for line in a.body:
			s += printFunction(line, indent + 1)
	elif t == ast.Raise:
		s += (indent * 4 * " ")
		s += "raise"
		if a.exc != None:
			s += " " + printFunction(a.exc, indent)
		# TODO: what is cause?!?
		s += "\n"
	elif type(a) == ast.Try:
		s += (indent * 4 * " ") + "try:\n"
		for line in a.body:
			s += printFunction(line, indent + 1)
		for handler in a.handlers:
			s += printFunction(handler, indent)
		if len(a.orelse) > 0:
			s += (indent * 4 * " ") + "else:\n"
			for line in a.orelse:
				s += printFunction(line, indent + 1)
		if len(a.finalbody) > 0:
			s += (indent * 4 * " ") + "finally:\n"
			for line in a.finalbody:
				s += printFunction(line, indent + 1)
	elif t == ast.Assert:
		s += (indent * 4 * " ")
		s += "assert " + printFunction(a.test, indent)
		if a.msg != None:
			s += ", " + printFunction(a.msg, indent)
		s += "\n"
	elif t == ast.Import:
		s += (indent * 4 * " ") + "import "
		for n in a.names:
			s += printFunction(n, indent) + ", "
		if len(a.names) > 0:
			s = s[:-2]
		s += "\n"
	elif t == ast.ImportFrom:
		s += (indent * 4 * " ") + "from "
		s += ("." * a.level if a.level != None else "") + a.module + " import "
		for name in a.names:
			s += printFunction(name, indent) + ", "
		if len(a.names) > 0:
			s = s[:-2]
		s += "\n"
	elif t == ast.Global:
		s += (indent * 4 * " ") + "global "
		for name in a.names:
			s += name + ", "
		s = s[:-2] + "\n"
	elif t == ast.Expr:
		s += (indent * 4 * " ") + printFunction(a.value, indent) + "\n"
	elif t == ast.Pass:
		s += (indent * 4 * " ") + "pass\n"
	elif t == ast.Break:
		s += (indent * 4 * " ") + "break\n"
	elif t == ast.Continue:
		s += (indent * 4 * " ") + "continue\n"

	elif t == ast.BoolOp:
		s += "(" + printFunction(a.values[0], indent)
		for i in range(1, len(a.values)):
			s += " " + printFunction(a.op, indent) + " " + \
					printFunction(a.values[i], indent)
		s += ")"
	elif t == ast.BinOp:
		s += "(" + printFunction(a.left, indent)
		s += " " + printFunction(a.op, indent) + " "
		s += printFunction(a.right, indent) + ")"
	elif t == ast.UnaryOp:
		s += "(" + printFunction(a.op, indent) + " "
		s += printFunction(a.operand, indent) + ")"
	elif t == ast.Lambda:
		s += "lambda "
		s += printFunction(a.arguments, indent) + ": "
		s += printFunction(a.body, indent)
	elif t == ast.IfExp:
		s += "(" + printFunction(a.body, indent)
		s += " if " + printFunction(a.test, indent)
		s += " else " + printFunction(a.orelse, indent) + ")"
	elif t == ast.Dict:
		s += "{ "
		for i in range(len(a.keys)):
			s += printFunction(a.keys[i], indent)
			s += " : "
			s += printFunction(a.values[i], indent)
			s += ", "
		if len(a.keys) >= 1:
			s = s[:-2]
		s += " }"
	elif t == ast.Set:
		# Empty sets must be initialized in a special way
		if len(a.elts) == 0:
			s += "set()"
		else:
			s += "{"
			for elt in a.elts:
				s += printFunction(elt, indent) + ", "
			s = s[:-2]
			s += "}"
	elif t == ast.ListComp:
		s += "["
		s += printFunction(a.elt, indent) + " "
		for gen in a.generators:
			s += printFunction(gen, indent) + " "
		s = s[:-1]
		s += "]"
	elif t == ast.SetComp:
		s += "{"
		s += printFunction(a.elt, indent) + " "
		for gen in a.generators:
			s += printFunction(gen, indent) + " "
		s = s[:-1]
		s += "}"
	elif t == ast.DictComp:
		s += "{"
		s += printFunction(a.key, indent) + " : " + \
				printFunction(a.value, indent) + " "
		for gen in a.generators:
			s += printFunction(gen, indent) + " "
		s = s[:-1]
		s += "}"
	elif t == ast.GeneratorExp:
		s += "("
		s += printFunction(a.elt, indent) + " "
		for gen in a.generators:
			s += printFunction(gen, indent) + " "
		s = s[:-1]
		s += ")"
	elif t == ast.Yield:
		s += "yield " + printFunction(a.value, indent)
	elif t == ast.Compare:
		s += "(" + printFunction(a.left, indent)
		for i in range(len(a.ops)):
			s += " " + printFunction(a.ops[i], indent)
			if i < len(a.comparators):
				s += " " + printFunction(a.comparators[i], indent)
		if len(a.comparators) > len(a.ops):
			for i in range(len(a.ops), len(a.comparators)):
				s += " " + printFunction(a.comparators[i], indent)
		s += ")"
	elif t == ast.Call:
		s += printFunction(a.func, indent) + "("
		for arg in a.args:
			s += printFunction(arg, indent) + ", "
		for key in a.keywords:
			s += printFunction(key, indent) + ", "
		if len(a.args) + len(a.keywords) >= 1:
			s = s[:-2]
		s += ")"
	elif t == ast.Num:
		if a.n != None:
			if a.n < 0:
				s += '(' + str(a.n) + ')'
			else:
				s += str(a.n)
	elif t == ast.Str:
		if a.s != None:
			val = repr(a.s)
			if val[0] == '"': # There must be a single quote in there...
				val = "'''" + val[1:len(val)-1] + "'''"
			s += val
			#s += "'" + a.s.replace("'", "\\'").replace('"', "\\'").replace("\n","\\n") + "'"
	elif t == ast.Bytes:
		s += str(a.s)
	elif t == ast.NameConstant:
		s += str(a.value)
	elif t == ast.Attribute:
		s += printFunction(a.value, indent) + "." + str(a.attr)
	elif t == ast.Subscript:
		s += printFunction(a.value, indent) + "[" + printFunction(a.slice, indent) + "]"
	elif t == ast.Name:
		s += a.id
	elif t == ast.List:
		s += "["
		for elt in a.elts:
			s += printFunction(elt, indent) + ", "
		if len(a.elts) >= 1:
			s = s[:-2]
		s += "]"
	elif t == ast.Tuple:
		s += "("
		for elt in a.elts:
			s += printFunction(elt, indent) + ", "
		if len(a.elts) > 1:
			s = s[:-2]
		elif len(a.elts) == 1:
			s = s[:-1] # don't get rid of the comma! It clarifies that this is a tuple
		s += ")"
	elif t == ast.Starred:
		s += "*" + printFunction(a.value, indent)
	elif t == ast.Ellipsis:
		s += "..."
	elif t == ast.Slice:
		if a.lower != None:
			s += printFunction(a.lower, indent)
		s += ":"
		if a.upper != None:
			s += printFunction(a.upper, indent)
		if a.step != None:
			s += ":" + printFunction(a.step, indent)
	elif t == ast.ExtSlice:
		for dim in a.dims:
			s += printFunction(dim, indent) + ", "
		if len(a.dims) > 0:
			s = s[:-2]
	elif t == ast.Index:
		s += printFunction(a.value, indent)

	elif t == ast.comprehension:
		s += "for "
		s += printFunction(a.target, indent) + " "
		s += "in "
		s += printFunction(a.iter, indent) + " "	
		for cond in a.ifs:
			s += "if "
			s += printFunction(cond, indent) + " "
		s = s[:-1]
	elif t == ast.ExceptHandler:
		s += (indent * 4 * " ") + "except"
		if a.type != None:
			s += " " + printFunction(a.type, indent)
			if a.name != None:
				s += " as " + a.name
		s += ":\n"
		for line in a.body:
			s += printFunction(line, indent + 1)
	elif t == ast.arguments:
		# Defaults are only applied AFTER non-defaults
		defaultStart = len(a.args) - len(a.defaults)
		for i in range(len(a.args)):
			s += printFunction(a.args[i], indent)
			if i >= defaultStart:
				s += "=" + printFunction(a.defaults[i - defaultStart], indent)
			s += ", "
		if a.vararg != None:
			s += "*" + printFunction(a.vararg, indent) + ", "
		if a.kwarg != None:
			s += "**" + printFunction(a.kwarg, indent) + ", "
		if a.vararg == None and a.kwarg == None and len(a.kwonlyargs) > 0:
			s += "*, "
		if len(a.kwonlyargs) > 0:
			for i in range(len(a.kwonlyargs)):
				s += printFunction(a.kwonlyargs[i], indent)
				s += "=" + printFunction(a.kw_defaults, indent) + ", "
		if (len(a.args) > 0 or a.vararg != None or a.kwarg != None or len(a.kwonlyargs) > 0):
			s = s[:-2]
	elif t == ast.arg:
		s += a.arg
		if a.annotation != None:
			s += ": " + printFunction(a.annotation, indent)
	elif t == ast.keyword:
		s += a.arg + "=" + printFunction(a.value, indent)
	elif t == ast.alias:
		s += a.name
		if a.asname != None:
			s += " as " + a.asname
	elif t == ast.withitem:
		s += printFunction(a.context_expr, indent)
		if a.optional_vars != None:
			s += " as " + printFunction(a.optional_vars, indent)
	else:
		ops = { ast.And : "and", ast.Or : "or",
				ast.Add : "+", ast.Sub : "-", ast.Mult : "*", ast.Div : "/", ast.Mod : "%",
				ast.Pow : "**", ast.LShift : "<<", ast.RShift : ">>", ast.BitOr : "|",
				ast.BitXor : "^", ast.BitAnd : "&", ast.FloorDiv : "//",
				ast.Invert : "~", ast.Not : "not", ast.UAdd : "+", ast.USub : "-",
				ast.Eq : "==", ast.NotEq : "!=", ast.Lt : "<", ast.LtE : "<=",
				ast.Gt : ">", ast.GtE : ">=", ast.Is : "is", ast.IsNot : "is not",
				ast.In : "in", ast.NotIn : "not in"}
		if type(a) in ops:
			return ops[type(a)]
		if type(a) in [ast.Load, ast.Store, ast.Del, ast.AugLoad, ast.AugStore, ast.Param]:
			return ""
		log("display\tMissing type: " + str(t), "bug")
	return s

def formatContext(trace, verb):
	traceD = {
			"value"				: {	"Return"				: ("return statement"),
									"Assign"				: ("right side of the assignment"),
									"AugAssign"				: ("right side of the assignment"),
									"Expression"			: ("expression"),
									"Dict Comprehension"	: ("left value of the dict comprehension"),
									"Yield"					: ("yield expression"),
									"Repr"					: ("repr expression"),
									"Attribute"				: ("attribute value"),
									"Subscript"				: ("outer part of the subscript"),
									"Index"					: ("inner part of the subscript"),
									"Keyword"				: ("right side of the keyword"),
									"Starred"				: ("value of the starred expression"),
									"Name Constant"			: ("constant value")							},
			"values"			: {	"Print"					: ("print statement"),
									"Boolean Operation"		: ("boolean operation"),
									"Dict"					: ("values of the dictionary")					},
			"name"				: {	"Function Definition"	: ("function name"),
									"Class Definition"		: ("class name"),
									"Except Handler"		: ("name of the except statement"),
									"Alias"					: ("alias")										},
			"names"				: {	"Import"				: ("import"),
									"ImportFrom" 			: ("import"),	
									"Global"				: ("global variables")							},
			"elt"				: { "List Comprehension"	: ("left element of the list comprehension"),
									"Set Comprehension"		: ("left element of the set comprehension"),
									"Generator"				: ("left element of the generator")				},
			"elts"				: {	"Set"					: ("set"),
									"List"					: ("list"),		
									"Tuple"					: ("tuple")										},
			"target"			: {	"AugAssign"				: ("left side of the assignment"),
									"For"					: ("target of the for loop"),
									"Comprehension"			: ("target of the comprehension")				},
			"targets"			: {	"Delete"				: ("delete statement"),
									"Assign"				: ("left side of the assignment")				},
			"op"				: {	"AugAssign" 			: ("assignment"),
									"Boolean Operation"		: ("boolean operation"),
									"Binary Operation"		: ("binary operation"),
									"Unary Operation"		: ("unary operation")							},
			"ops"				: {	"Compare"				: ("comparison operation")						},
			"arg"				: { "Keyword"				: ("left side of the keyword"),
								    "Argument" 				: ("argument")									},
			"args"				: {	"Function Definition"	: ("function arguments"),						   # single item
									"Lambda"				: ("lambda arguments"),							   # single item
									"Call"					: ("arguments of the function call"),			
									"Arguments"				: ("function arguments")						},
			"key"				: { "Dict Comprehension"	: ("left key of the dict comprehension")		},
			"keys"				: {	"Dict"					: ("keys of the dictionary")					},
			"kwarg"				: { "Arguments"				: ("keyword arg")								},
			"kwargs"			: { "Call"					: ("keyword args of the function call")			}, # single item
			"body"				: {	"Module"				: ("main codebase"),							   # list
									"Interactive"			: ("main codebase"),							   # list
									"Expression"			: ("main codebase"),
									"Suite"					: ("main codebase"),							   # list
									"Function Definition"	: ("function body"),							   # list
									"Class Definition"		: ("class body"),								   # list
									"For"					: ("lines of the for loop"),					   # list
									"While"					: ("lines of the while loop"),					   # list
									"If"					: ("main lines of the if statement"),			   # list
									"With"					: ("lines of the with block"),					   # list
									"Try"					: ("lines of the try block"),					   # list
									"Execute"				: ("exec expression"),
									"Lambda"				: ("lambda body"),
									"Ternary"				: ("ternary body"),
									"Except Handler"		: ("lines of the except block")					}, # list
			"orelse"			: {	"For"					: ("else part of the for loop"),				   # list	
									"While"					: ("else part of the while loop"),				   # list
									"If"					: ("lines of the else statement"),				   # list
									"Try"					: ("lines of the else statement"),				   # list
									"Ternary"				: ("ternary else value")						},
			"test"				: {	"While"					: ("test case of the while statement"),
									"If"					: ("test case of the if statement"),
									"Assert"				: ("assert expression"),
									"Ternary"				: ("test case of the ternary expression")		},
			"generators"		: { "List Comprehension"	: ("list comprehension"),
									"Set Comprehension"		: ("set comprehension"),
									"Dict Comprehension"	: ("dict comprehension"),
									"Generator"				: ("generator")									},
			"decorator_list"	: { "Function Definition"	: ("function decorators"),						   # list
									"Class Definition"		: ("class decorators")							}, # list
			"iter"				: {	"For"					: ("iterator of the for loop"),
									"Comprehension"			: ("iterator of the comprehension")				},
			"type"				: { "Raise"					: ("raised type"),
									"Except Handler"		: ("type of the except statement") 				},
			"left"				: {	"Binary Operation"		: ("left side of the binary operation"),
									"Compare"				: ("left side of the comparison")				},
			"bases"				: { "Class Definition"		: ("class bases")								},
			"dest"				: { "Print"					: ("print destination")							},
			"nl"				: { "Print"					: ("comma at the end of the print statement")	},
			"context_expr"		: { "With item"				: ("context of the with statement")				},
			"optional_vars"		: { "With item"				: ("context of the with statement")				}, # single item
			"inst"				: { "Raise"					: ("raise expression")							},
			"tback"				: { "Raise"					: ("raise expression")							},
			"handlers"			: { "Try"					: ("except block")								},
			"finalbody"			: { "Try"					: ("finally block")								}, # list
			"msg"				: { "Assert"				: ("assert message")							},
			"module"			: { "Import From"			: ("import module")								},
			"level"				: { "Import From"			: ("import module")								},
			"globals"			: { "Execute"				: ("exec global value")							}, # single item
			"locals"			: { "Execute"				: ("exec local value")							}, # single item
			"right"				: {	"Binary Operation"		: ("right side of the binary operation")		},
			"operand"			: {	"Unary Operation"		: ("value of the unary operation")				},
			"comparators"		: {	"Compare"				: ("right side of the comparison")				},
			"func"				: {	"Call"					: ("function call")								},
			"keywords"			: {	"Call"					: ("keywords of the function call")				},
			"starargs"			: { "Call"					: ("star args of the function call")			}, # single item
			"attr"				: {	"Attribute"				: ("attribute of the value")					},
			"slice"				: {	"Subscript"				: ("inner part of the subscript")				},
			"lower"				: {	"Slice"					: ("left side of the subscript slice")			},
			"upper"				: {	"Slice"					: ("right side of the subscript slice")			},
			"step"				: { "Step"					: ("rightmost side of the subscript slice")		},
			"dims"				: { "ExtSlice"				: ("slice")										},
			"ifs"				: { "Comprehension"			: ("if part of the comprehension")				},
			"vararg"			: { "Arguments"				: ("vararg")									},
			"defaults"			: { "Arguments"				: ("default values of the arguments")			},
			"asname"			: { "Alias"					: ("new name")									},
			"items"				: { "With" 					: ("context of the with statement")				}
	}

	# Find what type this is by trying to find the closest container in the path
	i = 0
	while i < len(trace):
		if type(trace[i]) == tuple:
			if trace[i][0] == "value" and trace[i][1] == "Attribute":
				pass
			elif trace[i][0] in traceD:
				break
			elif trace[i][0] in ["id", "n", "s"]:
				pass
			else:
				log("display\tformatContext\tSkipped field: " + str(trace[i]), "bug")
		i += 1
	else:
		return "" # this is probably covered by the line number

	field,typ = trace[i]
	if field in traceD and typ in traceD[field]:
		context = traceD[field][typ]
		return verb + "the " + context
	else:
		log("display\tformatContext\tMissing field: " + str(field) + "," + str(typ), "bug")
		return ""

def formatList(node, field):
	if type(node) != list:
		return None
	s = ""
	nameMap = { "body" : "line", "targets" : "value", "values" : "value", "orelse" : "line",
				"names" : "name", "keys" : "key", "elts" : "value", "ops" : "operator",
				"comparators" : "value", "args" : "argument", "keywords" : "keyword" }

	# Find what type this is
	itemType = nameMap[field] if field in nameMap else "line"

	if len(node) > 1:
		s = "the " + itemType + "s: "
		for line in node:
			s += formatNode(line) + ", "
	elif len(node) == 1:
		s = "the " + itemType + " "
		f = formatNode(node[0])
		if itemType == "line":
			f = "[" + f + "]"
		s += f
	return s

def formatNode(node):
	"""Create a string version of the given node"""
	if node == None:
		return ""
	t = type(node)
	if t == str:
		return "'" + node + "'"
	elif t == int or t == float:
		return str(node)
	elif t == list:
		return formatList(node, None)
	else:
		return printFunction(node, 0)