import ast, traceback
from .testHarness import *
from ..display import *
from ..namesets import *
from ..models import *

loaded_pairs = { } # Keep track of pairs for efficiency

def test(s, forceRetest=False):
	"""A method for testing solution states, which returns a number between
		0 (totally wrong) and 1 (correct)"""
	if forceRetest:
		if hasattr(s, "loadedFun"):
			del s.loadedFun
		s.score = None
		s.feedback = ""
	if (s.score != None and s.feedback != ""):
		return s

	if s.tree != None:
		replaceHazards(s.tree)
		s.code = printFunction(s.tree, 0)

	# If necessary, load the tests
	if s.problem.id not in loaded_pairs:
		tests = s.problem.tests.all()
		for i in range(len(tests)):
			# Need to interpret from repr
			try:
				tests[i].input = eval(tests[i].test_input)
				tests[i].output = eval(tests[i].test_output)
			except:
				s.score = 0
				if not hasattr(tests[i], "input"):
					s.feedback = "Broken test case input: " + tests[i].test_input + "\nExpecting a tuple of values."
				else:
					s.feedback = "Broken test case output: " + tests[i].test_output + "\nExpecting a legal Python value."
				return s
		loaded_pairs[s.problem.id] = tests

	tests = loaded_pairs[s.problem.id]
	s.num_pairs = len(tests)
	try:
		ast.parse(s.code)
		s.score, s.feedback = score(s, tests, returnFeedback=True)
	except Exception as e: # if the code doesn't parse, create a compiler error message
		s.score = 0
		trace = traceback.format_exc()
		lines = trace.split("\n")
		lines = lines[lines.index("    return compile(source, filename, mode, PyCF_ONLY_AST)")+1:]
		s.feedback = "COMPILER ERROR:\n" + str("\n".join(lines))
	return s

def replaceHazards(a):
	if not isinstance(a, ast.AST):
		return
	for field in ast.walk(a):
		if type(a) == ast.Import:
			for i in range(len(a.names)):
				if a.names[i].name not in supportedLibraries:
					if not (a.names[i].name[0] == "r" and a.names[i].name[1] in "0123456789") and not ("NotAllowed" in a.names[i].name):
						a.names[i].name = a.names[i].name + "NotAllowed"
		elif type(a) == ast.ImportFrom:
			if a.module not in supportedLibraries:
				if not (a.module[0] == "r" and a.module[1] in "0123456789") and not ("NotAllowed" in a.module):
					a.module = a.module + "NotAllowed"
		elif type(a) == ast.Call:
			if type(a.func) == ast.Name and a.func.id in ["compile", "eval", "execfile", "file", "open", "__import__", "apply"]:
				a.func.id = a.func.id + "NotAllowed"
