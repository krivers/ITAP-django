import ast, types, collections

supportedLibraries = [ "string", "math", "random", "__future__", "copy" ]

builtInTypes = [ bool, bytes, complex, dict, float, int, list, 
				 set, str, tuple, type ]

staticTypeCastBuiltInFunctions = {
	"bool" : { (object,) : bool }, 
	"bytes" : bytes,
	"complex" : { (str, int) : complex, (str, float) : complex, (int, int) : complex,
				  (int, float) : complex, (float, int) : complex, (float, float) : complex },
	"dict" : { (collections.Iterable,) : dict }, 
	"enumerate" : { (collections.Iterable,) : enumerate },
	"float" : { (str,) : float, (int,) : float, (float,) : float },
	"frozenset" : frozenset, 
	"int" : { (str,) : int, (float,) : int, (int,) : int, (str, int) : int },
	"list" : { (collections.Iterable,) : list },
	"memoryview" : None, #TODO
	"object" : { () : object }, 
	"property" : property, #TODO
	"reversed" : { (str,) : reversed, (list,) : reversed },
	"set" : { () : None, (collections.Iterable,) : None }, #TODO
	"slice" : { (int,) : slice, (int, int) : slice, (int, int, int) : slice },
	"str" : { (object,) : str }, 
	"tuple" : { () : tuple, (collections.Iterable,) : tuple },
	"type" : { (object,) : type },
	}

mutatingTypeCastBuiltInFunctions = {
	"bytearray" : { () : list },
	"classmethod" : None,
	"file" : None,
	"staticmethod" : None, #TOOD
	"super" : None
	}

builtInNames = [ "None", "True", "False", "NotImplemented", "Ellipsis" ] + \
	list(staticTypeCastBuiltInFunctions.keys()) + list(mutatingTypeCastBuiltInFunctions.keys())

staticBuiltInFunctions = {	
	"abs" : { (int,) : int, (float,) : float }, 
	"all" : { (collections.Iterable,) : bool }, 
	"any" : { (collections.Iterable,) : bool }, 
	"bin" : { (int,) : str }, 
	"callable" : { (object,) : bool },
	"chr" : { (int,) : str }, 
	"cmp" : { (object, object) : int },
	"coerce" : tuple, #TODO
	"compile" : { (str, str, str) : ast, (ast, str, str) : ast },
	"dir" : { () : list },
	"divmod" : { (int, int) : tuple, (int, float) : tuple,
				 (float, int) : tuple, (float, float) : tuple },
	"filter" : { (types.FunctionType, collections.Iterable) : list },
	"getattr" : None, 
	"globals" : dict, 
	"hasattr" : bool, #TODO
	"hash" : int, 
	"hex" : str, 
	"id" : int, #TODO
	"isinstance" : { (None, None) : bool }, 
	"issubclass" : bool, #TODO
	"iter" : { (collections.Iterable,) : None, (None, object) : None },
	"len" : { (str,) : int, (tuple,) : int, (list,) : int, (dict,) : int },
	"locals" : dict, 
	"map" : { (None, collections.Iterable) : list }, #TODO
	"max" : { (collections.Iterable,) : None },
	"min" : { (collections.Iterable,) : None },
	"oct" : { (int,) : str },
	"ord" : { (str,) : int },
	"pow" : { (int, int) : int, (int, float) : float,
			  (float, int) : float, (float, float) : float },
	"print" : None, 
	"range" : { (int,) : list, (int, int) : list, (int, int, int) : list }, 
	"repr" : {(object,) : str },
	"round" : { (int,) : float, (float,) : float, (int, int) : float, (float, int) : float },
	"sorted" : { (collections.Iterable,) : list },
	"sum" : { (collections.Iterable,) : None },
	"vars" : dict, #TODO
	"zip" : { () : list, (collections.Iterable,) : list}
	}

mutatingBuiltInFunctions = {
	"__import__" : None,
	"apply" : None,
	"delattr" : { (object, str) : None }, 
	"eval" : { (str,) : None },
	"execfile" : None,
	"format" : None, 
	"input" : { () : None, (object,) : None }, 
	"intern" : str, #TOOD
	"next" : { () : None, (None,) : None },
	"open" : None,
	"raw_input" : { () : str, (object,) : str },
	"reduce" : None, 
	"reload" : None, 
	"setattr" : None
	}

builtInSafeFunctions = [
	"abs", "all", "any", "bin", "bool", "cmp", "len",
	"list", "max", "min", "pow", "repr", "round", "slice", "str", "type"
	]


exceptionClasses = [
	"ArithmeticError", 
	"AssertionError", 
	"AttributeError", 
	"BaseException", 
	"BufferError", 
	"BytesWarning", 
	"DeprecationWarning", 
	"EOFError", 
	"EnvironmentError", 
	"Exception", 
	"FloatingPointError", 
	"FutureWarning", 
	"GeneratorExit", 
	"IOError", 
	"ImportError", 
	"ImportWarning",
	"IndentationError", 
	"IndexError", 
	"KeyError", 
	"KeyboardInterrupt", 
	"LookupError", 
	"MemoryError", 
	"NameError",
	"NotImplementedError", 
	"OSError", 
	"OverflowError", 
	"PendingDeprecationWarning", 
	"ReferenceError", 
	"RuntimeError", 
	"RuntimeWarning", 
	"StandardError",
	"StopIteration", 
	"SyntaxError", 
	"SyntaxWarning", 
	"SystemError", 
	"SystemExit", 
	"TabError",
	"TypeError", 
	"UnboundLocalError", 
	"UnicodeDecodeError", 
	"UnicodeEncodeError", 
	"UnicodeError", 
	"UnicodeTranslateError", 
	"UnicodeWarning", 
	"UserWarning", 
	"ValueError", 
	"Warning", 
	"ZeroDivisionError", 

	"WindowsError", "BlockingIOError", "ChildProcessError", 
	"ConnectionError", "BrokenPipeError", "ConnectionAbortedError", 
	"ConnectionRefusedError", "ConnectionResetError", "FileExistsError", 
	"FileNotFoundError", "InterruptedError", "IsADirectoryError", "NotADirectoryError", 
	"PermissionError", "ProcessLookupError", "TimeoutError", 
	"ResourceWarning", "RecursionError", "StopAsyncIteration" ]

builtInFunctions = dict(list(staticBuiltInFunctions.items()) + \
	list(mutatingBuiltInFunctions.items()) + \
	list(staticTypeCastBuiltInFunctions.items()) + \
	list(mutatingTypeCastBuiltInFunctions.items()))

# All string functions do not mutate the caller, they return copies instead
builtInStringFunctions = {
	"capitalize" : { () : str }, 
	"center" : { (int,) : str, (int, str) : str }, 
	"count" : { (str,) : int, (str, int) : int, (str, int, int) : int },
	"decode" : { () : str }, 
	"encode" : { () : str }, 
	"endswith" : { (str,) : bool },
	"expandtabs" : { () : str, (int,) : str },
	"find" : { (str,) : int, (str, int) : int, (str, int, int) : int },
	"format" : { (list, list) : str },
	"index" : { (str,) : int, (str,int) : int, (str,int,int) : int },
	"isalnum" : { () : bool }, 
	"isalpha" : { () : bool },
	"isdecimal" : { () : bool }, 
	"isdigit" : { () : bool }, 
	"islower" : { () : bool },
	"isnumeric" : { () : bool }, 
	"isspace" : { () : bool }, 
	"istitle" : { () : bool },
	"isupper" : { () : bool }, 
	"join" : { (collections.Iterable,) : str, (collections.Iterable,str) : str },
	"ljust" : { (int,) : str },
	"lower" : { () : str }, 
	"lstrip" : { () : str, (str,) : str },
	"partition" : { (str,) : tuple }, 
	"replace" : { (str, str) : str, (str, str, int) : str },
	"rfind" : { (str,) : int, (str,int) : int, (str,int,int) : int }, 
	"rindex" : { (str,) : int }, 
	"rjust" : { (int,) : str },
	"rpartition" : { (str,) : tuple }, 
	"rsplit" : { () : list }, 
	"rstrip" : { () : str },
	"split" : { () : list, (str,) : list, (str, int) : list }, 
	"splitlines" : { () : list },
	"startswith" : { (str,) : bool },
	"strip" : { () : str, (str,) : str }, 
	"swapcase" : { () : str }, 
	"title" : { () : str },
	"translate" : { (str,) : str }, 
	"upper" : { () : str },
	"zfill" : { (int,) : str }
	}

safeStringFunctions = [ 
	"capitalize", "center", "count", "endswith", "expandtabs", "find",
	"isalnum", "isalpha", "isdigit", "islower", "isspace", "istitle",
	"isupper", "join", "ljust", "lower", "lstrip", "partition", "replace",
	"rfind", "rjust", "rpartition", "rsplit", "rstrip", "split", "splitlines",
	"startswith", "strip", "swapcase", "title", "translate", "upper", "zfill",
	"isdecimal", "isnumeric"]

mutatingListFunctions = {
	"append" : { (object,) : None },
	"extend" : { (list,) : None }, 
	"insert" : { (int, object) : None },
	"remove" : { (object,) : None },
	"pop" : { () : None, (int,) : None },
	"sort" : { () : None },
	"reverse" : { () : None }
	}

staticListFunctions = {
	"index" : { (object,) : int, (object,int) : int, (object,int,int) : int }, 
	"count" : { (object,) : int, (object,int) : int, (object,int,int) : int }
	}

safeListFunctions = [ "append", "extend", "insert", "count", "sort", "reverse"]

builtInListFunctions = dict(list(mutatingListFunctions.items()) + list(staticListFunctions.items()))

staticDictFunctions = { 
	"get" : { (object,) : object, (object, object) : object }, 
	"items" : { () : list }
	}

builtInDictFunctions = staticDictFunctions

mathFunctions = {
	"ceil" : { (int,) : float, (float,) : float }, 
	"copysign" : { (int, int) : float, (int, float) : float,
				   (float, int) : float, (float, float) : float },
	"fabs" : { (int,) : float, (float,) : float }, 
	"factorial" : { (int,) : int, (float,) : int },
	"floor" : { (int,) : float, (float,) : float },
	"fmod" : { (int, int) : float, (int, float) : float, 
			   (float, int) : float, (float, float) : float },
	"frexp" : int, 
	"fsum" : int, #TODO
	"isinf" : { (int,) : bool, (float,) : bool }, 
	"isnan" : { (int,) : bool, (float,) : bool },
	"ldexp" : int, 
	"modf" : tuple, 
	"trunc" : None, #TODO
	"exp" : { (int,) : float, (float,) : float }, 
	"expm1" : { (int,) : float, (float,) : float },
	"log" : { (int,) : float, (float,) : float, 
			  (int,int) : float, (int,float) : float, 
			  (float, int) : float, (float, float) : float },
	"log1p" : { (int,) : float, (float,) : float },
	"log10" : { (int,) : float, (float,) : float },
	"pow" : { (int, int) : float, (int, float) : float, 
			  (float, int) : float, (float, float) : float },
	"sqrt" : { (int,) : float, (float,) : float }, 
	"acos" : { (int,) : float, (float,) : float },
	"asin" : { (int,) : float, (float,) : float }, 
	"atan" : { (int,) : float, (float,) : float },
	"atan2" : { (int,) : float, (float,) : float }, 
	"cos" : { (int,) : float, (float,) : float },
	"hypot" : { (int, int) : float, (int, float) : float, 
				(float, int) : float, (float, float) : float },
	"sin" : { (int,) : float, (float,) : float }, 
	"tan" : { (int,) : float, (float,) : float },
	"degrees" : { (int,) : float, (float,) : float }, 
	"radians" : { (int,) : float, (float,) : float },
	"acosh" : int, 
	"asinh" : int, 
	"atanh" : int, 
	"cosh" : int, 
	"sinh" : int, 
	"tanh" : int,#TODO
	"erf" : int, 
	"erfc" : int, 
	"gamma" : int, 
	"lgamma" : int #TODO
	}

safeMathFunctions = [ 
	"ceil", "copysign", "fabs", "floor", "fmod", "isinf", 
	"isnan", "exp", "expm1", "cos", "hypot", "sin", "tan", 
	"degrees", "radians" ]

randomFunctions = { 
	"seed" : { () : None, (collections.Hashable,) : None }, 
	"getstate" : { () : object },
	"setstate" : { (object,) : None }, 
	"jumpahead" : { (int,) : None }, 
	"getrandbits" : { (int,) : int },
	"randrange" : { (int,) : int, (int, int) : int, (int, int, int) : int },
	"randint" : { (int, int) : int }, 
	"choice" : { (collections.Iterable,) : object },
	"shuffle" : { (collections.Iterable,) : None, 
				  (collections.Iterable, types.FunctionType) : None },
	"sample" : { (collections.Iterable, int) : list }, 
	"random" : { () : float },
	"uniform" : { (float, float) : float }
	}

futureFunctions = {
	"nested_scopes" : None,
	"generators" : None,
	"division" : None,
	"absolute_import" : None,
	"with_statement" : None,
	"print_function" : None,
	"unicode_literals" : None
	}

copyFunctions = {
	"copy" : None,
	"deepcopy" : None
}

timeFunctions = { 
	"clock" : { () : float }, 
	"time" : { () : float }
	}

errorFunctions = { 
	"AssertionError" : { (str,) : object }
	}

allStaticFunctions = dict(list(staticBuiltInFunctions.items()) + list(staticTypeCastBuiltInFunctions.items()) + \
							list(builtInStringFunctions.items()) + list(staticListFunctions.items()) + \
							list(staticDictFunctions.items()) + list(mathFunctions.items()))

allMutatingFunctions = dict(list(mutatingBuiltInFunctions.items()) + list(mutatingTypeCastBuiltInFunctions.items()) + \
							list(mutatingListFunctions.items()) + list(randomFunctions.items()) + list(timeFunctions.items()))

allPythonFunctions = dict(list(allStaticFunctions.items()) + list(allMutatingFunctions.items()))

safeLibraryMap = { "string" : [ "ascii_letters", "ascii_lowercase", "ascii_uppercase", 
							"digits", "hexdigits", "letters", "lowercase", "octdigits", 
							"punctuation", "printable", "uppercase", "whitespace", 
							"capitalize", "expandtabs", "find", "rfind", "count", 
							"lower", "split", "rsplit", "splitfields", "join", 
							"joinfields", "lstrip", "rstrip", "strip", "swapcase", 
							"upper", "ljust", "rjust", "center", "zfill", "replace"],
				"math" : [	"ceil", "copysign", "fabs", "floor", "fmod", 
							"frexp", "fsum", "isinf", "isnan", "ldexp", "modf", "trunc", "exp", 
							"expm1", "log", "log1p", "log10", "sqrt", "acos", "asin", 
							"atan", "atan2", "cos", "hypot", "sin", "tan", "degrees", "radians", 
							"acosh", "asinh", "atanh", "cosh", "sinh", "tanh", "erf", "erfc", 
							"gamma", "lgamma", "pi", "e" ],
				"random" : [ ],
				"__future__" : ["nested_scopes", "generators", "division", "absolute_import",
							"with_statement", "print_function", "unicode_literals"] }

libraryMap = { "string" : [ "ascii_letters", "ascii_lowercase", "ascii_uppercase", 
							"digits", "hexdigits", "letters", "lowercase", "octdigits", 
							"punctuation", "printable", "uppercase", "whitespace", 
							"capwords", "maketrans", "atof", "atoi", "atol", "capitalize", 
							"expandtabs", "find", "rfind", "index", "rindex", "count", 
							"lower", "split", "rsplit", "splitfields", "join", 
							"joinfields", "lstrip", "rstrip", "strip", "swapcase", 
							"translate", "upper", "ljust", "rjust", "center", "zfill", 
							"replace", "Template", "Formatter" ],
				"math" : [	"ceil", "copysign", "fabs", "factorial", "floor", "fmod", 
							"frexp", "fsum", "isinf", "isnan", "ldexp", "modf", "trunc", "exp", 
							"expm1", "log", "log1p", "log10", "pow", "sqrt", "acos", "asin", 
							"atan", "atan2", "cos", "hypot", "sin", "tan", "degrees", "radians", 
							"acosh", "asinh", "atanh", "cosh", "sinh", "tanh", "erf", "erfc", 
							"gamma", "lgamma", "pi", "e" ],
				"random" : ["seed", "getstate", "setstate", "jumpahead", "getrandbits",
							"randrange", "randrange", "randint", "choice", "shuffle", "sample",
							"random", "uniform", "triangular", "betavariate", "expovariate", 
							"gammavariate", "gauss", "lognormvariate", "normalvariate", 
							"vonmisesvariate", "paretovariate", "weibullvariate", "WichmannHill", 
							"whseed", "SystemRandom" ],
				"__future__" : ["nested_scopes", "generators", "division", "absolute_import",
							"with_statement", "print_function", "unicode_literals"] }

libraryDictMap = { "string" : builtInStringFunctions,
					"math" : mathFunctions,
					"random" : randomFunctions,
					"__future__" : futureFunctions,
					"copy" : copyFunctions }

typeMethodMap = {"string" : ["capitalize", "center", "count", "decode", "encode", "endswith", 
							"expandtabs", "find", "format", "index", "isalnum", "isalpha",
							"isdigit", "islower", "isspace", "istitle", "isupper", "join",
							"ljust", "lower", "lstrip", "partition", "replace", "rfind",
							"rindex", "rjust", "rpartition", "rsplit", "rstrip", "split",
							"splitlines", "startswith", "strip", "swapcase", "title",
							"translate", "upper", "zfill"],
				"list" : [ 	"append", "extend", "count", "index", "insert", "pop", "remove",
							"reverse", "sort"],
				"set" : [	"isdisjoint", "issubset", "issuperset", "union", "intersection",
							"difference", "symmetric_difference", "update", "intersection_update",
							"difference_update", "symmetric_difference_update", "add",
							"remove", "discard", "pop", "clear"],
				"dict" : [	"iter", "clear", "copy", "fromkeys", "get", "has_key", "items",
							"iteritems", "iterkeys", "itervalues", "keys", "pop", "popitem",
							"setdefault", "update", "values", "viewitems", "viewkeys", 
							"viewvalues"] }

astNames = {
		ast.Module : "Module", ast.Interactive : "Interactive Module", 
		ast.Expression : "Expression Module", ast.Suite : "Suite",

		ast.FunctionDef : "Function Definition",
		ast.ClassDef : "Class Definition", ast.Return : "Return",
		ast.Delete : "Delete", ast.Assign : "Assign",
		ast.AugAssign : "AugAssign", ast.For : "For",
		ast.While : "While", ast.If : "If", ast.With : "With",
		ast.Raise : "Raise",
		ast.Try : "Try", ast.Assert : "Assert",
		ast.Import : "Import", ast.ImportFrom : "Import From",
		ast.Global : "Global", ast.Expr : "Expression",
		ast.Pass : "Pass", ast.Break : "Break", ast.Continue : "Continue",

		ast.BoolOp : "Boolean Operation", ast.BinOp : "Binary Operation",
		ast.UnaryOp : "Unary Operation", ast.Lambda : "Lambda",
		ast.IfExp : "Ternary", ast.Dict : "Dictionary", ast.Set : "Set",
		ast.ListComp : "List Comprehension", ast.SetComp : "Set Comprehension",
		ast.DictComp : "Dict Comprehension", 
		ast.GeneratorExp : "Generator", ast.Yield : "Yield",
		ast.Compare : "Compare", ast.Call : "Call",
		ast.Num : "Number", ast.Str : "String", ast.Bytes : "Bytes", 
		ast.NameConstant : "Name Constant",
		ast.Attribute : "Attribute",
		ast.Subscript : "Subscript", ast.Name : "Name", ast.List : "List",
		ast.Tuple : "Tuple",

		ast.Load : "Load", ast.Store : "Store", ast.Del : "Delete",
		ast.AugLoad : "AugLoad", ast.AugStore : "AugStore",
		ast.Param : "Parameter",

		ast.Ellipsis : "Ellipsis", ast.Slice : "Slice",
		ast.ExtSlice : "ExtSlice", ast.Index : "Index",

		ast.And : "And", ast.Or : "Or", ast.Add : "Add", ast.Sub : "Subtract",
		ast.Mult : "Multiply", ast.Div : "Divide", ast.Mod : "Modulo",
		ast.Pow : "Power", ast.LShift : "Left Shift",
		ast.RShift : "Right Shift", ast.BitOr : "|", ast.BitXor : "^",
		ast.BitAnd : "&", ast.FloorDiv : "Integer Divide",
		ast.Invert : "Invert", ast.Not : "Not", ast.UAdd : "Unsigned Add",
		ast.USub : "Unsigned Subtract", ast.Eq : "==", ast.NotEq : "!=",
		ast.Lt : "<", ast.LtE : "<=", ast.Gt : ">", ast.GtE : ">=",
		ast.Is : "Is", ast.IsNot : "Is Not", ast.In : "In",
		ast.NotIn : "Not In",

		ast.comprehension: "Comprehension",
		ast.ExceptHandler : "Except Handler", ast.arguments : "Arguments", ast.arg : "Argument",
		ast.keyword : "Keyword", ast.alias : "Alias", ast.withitem : "With item"
		}