import copy, ctypes, imp, multiprocessing, os, random, io, sys, threading, time
from ..tools import log
from ..paths import TEST_PATH

done = False
msg_length = 400

def timerDone():
	global done
	done = True

def manageException(e, errors, input, output, actual):
	if type(e) == AssertionError:
		i = repr(input)
		i = i if len(i) < 100 else i[:96] + "...]"
		i = i[1:] if (i[0] == 'u' and i[1] == "'" and i[-1] == "'") else i
		o = repr(output)
		o = o if len(o) < 100 else o[:97] + "..."
		o = o[1:] if (o[0] == 'u' and o[1] == "'" and o[-1] == "'") else o
		a = repr(actual)
		a = a if len(a) < 100 else a[:97] + "..."
		errors.append("Failed assertion: given input (" + i[1:-1] + "), expected output " + o + ", actual output " + a ) # 364
	else:
		i = repr(input)
		i = i if len(i) < 100 else i[:97] + "..."
		emsg = str(e)
		emsg = emsg if len(emsg) < 100 else emsg[:97] + "..."
		errors.append("Test function with input (" + i[1:-1] + ") broke with error: " + emsg) # 245

def checkCopy(f, input):
	cp = copy.deepcopy(input)
	f(*cp)
	return cp == input

def load_file(tmpFile, tmpFull):
	failed = False
	# Then try to load the function
	try:
		mod = imp.load_source(tmpFile, tmpFull + ".py")
	except Exception as e:
		mod = None
		failed = True
	return mod, failed

def textToFunction(s):
	if s.loadedFun != None:
		return s.loadedFun
	instructorFunctions = s.problem.given_code
	# Create a file that can be loaded, with the function in it
	tmpFile = "tmp" + str(random.randint(0,100000))
	tmpPath = TEST_PATH + "tmp"
	tmpFull = tmpPath + "/" + tmpFile
	tmpCache = tmpPath + "/" + "__pycache__" + "/" + tmpFile
	try:
		f = open(tmpFull + ".py", "w")
	except:
		s.feedback = "ERROR: could not write file, please change permissions in the test/tmp folder"
		return None
	# Set this up to look like Python 3
	#f.write("from __future__ import (absolute_import, division, print_function)\n")
	if len(instructorFunctions) != 0:
		f.write(instructorFunctions + "\n\n")
	f.write(s.code)
	f.close()

	# Try loading the file in a timed thread in case the file calls infinitely-looping code
	p = multiprocessing.Process(target=load_file, args=(tmpFile, tmpFull))
	result = run_in_timer(p, 0.1)
	if result != "Success":
		log("testHarness\ttextToFunction\tTimer problem: " + result + "\n" + s.code, "bug")
		s.feedback = result
		return None
	else:
		out = sys.stdout
		err = sys.stderr
		sys.stdout = io.StringIO()
		sys.stderr = io.StringIO()
		mod, failed = load_file(tmpFile, tmpFull)
		sys.stdout = out
		sys.stderr = err

	# Clean up the extra files
	if os.path.exists(tmpFull + ".py"):
		os.remove(tmpFull + ".py")
	if os.path.exists(tmpFull + ".pyc"):
		os.remove(tmpFull + ".pyc")
	for version in range(10): # Python 3 caches in a separate folder and includes the version number
		name = tmpCache + ".cpython-3" + str(version) + ".pyc"
		if os.path.exists(name):
			os.remove(name)
	
	if failed:
		s.feedback = "ERROR: could not load function, possibly due to compiler error in instructorFunctions"
		return None

	# Load the resulting function from the file. It will have references to all necessary helpers
	if hasattr(mod, s.problem.name):
		loaded = getattr(mod, s.problem.name)
		s.loadedFun = loaded
	else:
		s.feedback = "ERROR: could not find required function in code"
		return None

	return s.loadedFun

def __genericTest__(f, input, output):
	errors = []
	answer = None
	input_copy = copy.deepcopy(input)
	try:
		answer = f(*input)
		if type(output) == float:
			assert(abs(answer - output) < 0.001)
		else:
			assert(answer == output)
	except Exception as e:
		manageException(e, errors, input_copy, output, answer)
	return errors

def runFunction(s, tests, score, feedback=None):
	f = textToFunction(s) # first, load the function
	for i in range(len(tests)):
		test = tests[i]
		if test.test_extra == "check_copy":
			inp = [f] + [test.input]
		elif test.test_extra == "":
			inp = test.input
		else:
			log("testHarness\trunFunction\tDid not recognize special function " + test.test_extra, "bug")
			return

		input_copy = copy.deepcopy(inp)
		errors = __genericTest__(f, inp, test.output)
		if len(errors) == 0: # if no problems occurred
			score.value = score.value + 1
			inp = repr(input_copy)
			inp = inp if len(inp) < 100 else inp[:97] + "..."
			inp = inp[1:] if (inp[0] == 'u' and inp[1] == "'" and inp[-1] == "'") else inp
			o = repr(test.output)
			o = o if len(o) < 100 else o[:97] + "..."
			o = o[1:] if (o[0] == 'u' and o[1] == "'" and o[-1] == "'") else o
			s = "Test passed on input (" + inp[1:-1] + "), expected output " + o + "\n" # 240
		else:
			s = errors[0] + "\n"
		if feedback != None:
			for j in range(len(s)):
				feedback[i*msg_length + j] = ord(s[j]) # add the string into the array

def run_in_timer(proc, timerTime):
	global done
	out = sys.stdout
	err = sys.stderr
	sys.stdout = io.StringIO()
	sys.stderr = io.StringIO()
	timer = threading.Timer(timerTime, timerDone)
	timeout = False
	try:
		proc.start()
		timer.start()
		while (proc.is_alive()) and (not done):
			continue
		timer.cancel()
		# If the process is still running, kill it
		if proc.is_alive():
			timeout = True
			#log("testHarness\tscore\tInfinite loop?", "bug")
			try:
				proc.terminate()
				time.sleep(0.01)
				if proc.is_alive():
					os.system('kill -9 ' + str(proc.pid))
			except:
				log("testHarness\tscore\tThread is still alive!", "bug")
			while proc.is_alive():
				time.sleep(0.01)
		sys.stdout = out
		sys.stderr = err
		done = False
	except Exception as e:
		log("testHarness\tscore\tBroken process: " + str(e), "bug")
		return "Broken Process"
	if timeout:
		return "Infinite loop! Code timed out after " + str(timerTime) + " seconds"
	else:
		return "Success"

def score(s, tests, returnFeedback=False):
	# Note that now, infinite loops will break all test cases that come after that. We're OK with this as long as we order test cases properly.
	if not hasattr(s, "loadedFun"):
		s.loadedFun = None
		s.loadedFun = textToFunction(s)
	f = s.loadedFun

	if f == None:
		return (0, s.feedback) if returnFeedback else 0

	score = multiprocessing.Value(ctypes.c_float, 0.0, lock=False)
	if returnFeedback:
		# Allocate 250 chars for each feedback line
		feedback = multiprocessing.Array(ctypes.c_int, msg_length * len(tests), lock=False)
		p = multiprocessing.Process(target=runFunction, args=(s, tests, score, feedback))
	else:
		p = multiprocessing.Process(target=runFunction, args=(s, tests, score))
	
	test_result = run_in_timer(p, 0.1)
	if test_result != "Success":
		log("testHarness\tscore\tTimer problem: " + test_result, "bug")
		result = 0
		msg = test_result
	else:
		if returnFeedback:
			msg = ""
			for i in range(len(tests)):
				j = 0
				while j < msg_length and feedback[i*msg_length + j] != 0:
					msg += chr(int(feedback[i*msg_length + j]))
					j += 1
		result = score.value / len(tests)
	return (result, msg) if returnFeedback else result

