import ast, sys, io, pstats, cProfile, time, random, os
from .canonicalize import getAllImports, runGiveIds, anonymizeNames, getCanonicalForm, propogateMetadata, propogateNameMetadata
from .path_construction import diffAsts, generateNextStates
from .individualize import mapEdit
from .generate_message import formatHints
from .getSyntaxHint import getSyntaxHint, applyChanges

from .test import test
from .display import printFunction
from .astTools import deepcopy, tree_to_str, str_to_tree
from .tools import log, parse_table
from .paths import LOG_PATH

from .models import *
from .ChangeVector import *
from .SyntaxEdit import *

def check_repeating_edits(state, allEdits, printedStates):
	# First check for infinitely-looping edits
	# If we've seen this exact change before, it's a loop
	if isinstance(state.edit[0], ChangeVector):
		if state.edit in allEdits:
			s = "REPEATING EDITS"
			log(s + "\n" + printedStates, "bug")
			return s
	elif isinstance(state.edit[0], SyntaxEdit):
		if len(allEdits) > 0:
			current = state.edit[0]
			prev = allEdits[-1][0]
			if not isinstance(prev, SyntaxEdit):
				log("getHint\tcheck_repeating_edits\tSyntax hint after semantic hint?\n" + 
					str(allEdits) + "\n" + str(state.edit), "bug")
				log(printedStates, "bug")
			else:
				# If we're adding and then deleting the same thing, it's a loop
				if current.editType == "-" and prev.editType == "+" and \
					current.line == prev.line and current.col == prev.col and \
					current.text == prev.text and current.newText == prev.newText:
					s = "REPEATING EDITS"
					log(s + "\n" + printedStates, "bug")
					return s
	else:
		log("Unknown edit type?" + repr(state.edit[0]), filename="bug")

def do_hint_chain(code, user, problem, interactive=False):
	orig_state = state = SourceState(code=code, problem=problem, count=1, student=user)
	failedTests = True
	stepCount = editCount = chrCount = 0
	cutoff = 20
	printedStates = "************************"
	allEdits = []
	# Keep applying hints until either the state is correct or
	# you've reached the cutoff. The cap is there to cut off infinite loops.
	while stepCount < cutoff:
		stepCount += 1
		printedStates += "State: \n" + state.code + "\n"
		state = get_hint(state, hint_level="next_step")
		if state.goal != None:
			printedStates += "Goal: \n" + state.goal.code + "\n"

		if hasattr(state, "edit") and state.edit != None and len(state.edit) > 0:
			printedStates += state.hint.message + "\n" + str(state.edit) + "\n"

			repeatingCheck = check_repeating_edits(state, allEdits, printedStates)
			if repeatingCheck != None:
				return repeatingCheck, chrCount, editCount, orig_state, None

			if isinstance(state.edit[0], ChangeVector):
				editCount += diffAsts.getChangesWeight(state.edit, False)
				newTree = state.tree
				for e in state.edit:
					e.start = newTree
					newTree = e.applyChange()

				if newTree == None:
					s = "EDIT BROKE"
					log(s + "\n" + printedStates, "bug")
					return s, chrCount, editCount, orig_state, None
				newFun = printFunction(newTree)
			else: # Fixing a syntax error
				newFun = applyChanges(state.code, state.edit)
				chrCount += sum(len(c.text) + len(c.newText) for c in state.edit)

			allEdits.append(state.edit)
			state = SourceState(code=newFun, problem=problem, count=1, student=user)
		elif state.score != 1:
			s = "NO NEXT STEP"
			log(s + "\n" + printedStates, "bug")
			log("Scores: " + str(state.score) + "," + str(state.goal.score), "bug")
			log("Feedback: " + str(state.feedback) + "," + str(state.goal.feedback), "bug")
			log("DIFF: " + str(diffAsts.diffAsts(state.tree, state.goal.tree)), "bug")
			return s, chrCount, editCount, orig_state, None
		else: # break out when the score reaches 1
			break
		if interactive:
			input("")

	if state.score == 1:
		if stepCount == 1:
			s = "Started Correct"
		else: # Got through the hints! Woo!
			s = "Success"
	else: # These are the bad cases
		state = None # no goal state!
		if stepCount >= cutoff:
			s = "TOO LONG"
			log(s + "\n" + printedStates, "bug")
		else:
			s = "BROKEN"
			log(s + "\n" + printedStates, "bug")
	return s, chrCount, editCount, orig_state, state


def clear_solution_space(problem, keep_starter=True):
	old_states = State.objects.filter(problem=problem.id)
	if len(old_states) > 1:
		# Clean out the old states
		starter_code = list(old_states)[0].code
		log("Deleting " + str(len(old_states)) + " old states...", "bug")
		old_states.delete()

		if keep_starter:
			# But save the instructor solution!
			starter_state = SourceState(code=starter_code, problem=problem, count=1, student=Student.objects.get(id=1))
			starter_state = get_hint(starter_state)
			starter_state.save()
			problem.solution = starter_state
			problem.save()

def run_all_problems():
	problems = ["allDigitsOccurIn", "automatedReadabilityIndex", "bridgeBidScore",
				"canDrinkAlcohol", "charCount", "circleArea", "combineAllLists",
				"convertToDegrees", "digitOccursIn", "factorial", "findRoot",
				"findTheCircle", "friendOfFriends", "hasBalancedParentheses",
				"hasConsecutiveDigits", "hasTwoDigits", "invertDictionary",
				"isEvenPositiveInt", "isFactorial", "isFactorialPrime",
				"isHappyNumber", "isLegalTriangle", "isLetterOrDigit",
				"isPrime", "isRotation", "kthDigit", "mostAnagrams", 
				"nearestBusStop", "nthFactorialPrime", "nthHappyNumber",
				"onlyOneTrue", "onlyTwoTrue", "overNineThousand",
				"parseStringToTable", "sameDigits", "sensibleTemperatureAverage",
				"sentenceCount", "simplePigLatin", "squareIfNumber", "stockChange",
				"sumOfSquaresOfDigits", "treasureHunt", "withinFive", "wordCount"]
	for problem in problems:
		log("Running " + problem, "bug")
		import_code_as_states("hintgen/data/"+problem+".csv", 1,
			problem, clear_space=True, run_profiler=True)

def test_solution_space(problems):
	for problem in problems:
		for count in range(20):
			log("Running " + problem + " " + str(count), "bug")
			run_solution_space_improvement("hintgen/combined_data/" + problem + ".csv", problem, "random")
			os.rename(LOG_PATH + problem + "_" + "random" + ".csv", 
					  LOG_PATH + problem + "_" + "random" + "_" + str(count) + ".csv")


def run_all_spaces(keyword):
	problems = ["all_three_chars", "any_divisible", "any_first_chars", 
				"any_lowercase", "can_make_breakfast", "can_drink_alcohol", 
				"convert_to_degrees", "count_all_empty_strings", 
				"create_number_block", "factorial", "find_root", 
				"find_the_circle", "first_and_last", "get_extra_bagel", 
				"go_to_gym", "has_extra_fee", "has_balanced_parentheses", 
				"has_two_digits", "hello_world", "how_many_egg_cartons", 
				"is_leap_month", "is_even_positive_int", "is_prime", 
				"is_punctuation", "is_substring", "kth_digit", "last_index", 
				"list_of_lists", "multiply_numbers", "nearest_bus_stop", 
				"no_positive_even", "one_to_n", "over_nine_thousand", 
				"reduce_to_positive", "second_largest", "single_pig_latin", 
				"sum_all_even_numbers", "sum_of_odd_digits", "sum_of_digits", 
				"was_lincoln_alive", "wear_a_coat"
				]
	for problem in problems:
		log("Running " + problem, "bug")
		run_solution_space_improvement("hintgen/combined_data/" + problem + ".csv", problem, keyword)

def import_code_as_states(f, course_id, problem_name, clear_space=False, run_profiler=False, run_hint_chain=False):
	if run_profiler:
		# Set up the profiler
		out = sys.stdout
		outStream = io.StringIO()
		sys.stdout = outStream
		pr = cProfile.Profile()
		pr.enable()

	course = Course.objects.get(id=course_id)
	problem = course.problems.get(name=problem_name)

	if clear_space:
		clear_solution_space(problem)

	# Import a CSV file of code into the database
	table = parse_table(f)
	header = table[0]
	table = table[1:]
	results = ""
	for line in table:
		if line[0] == "0": # we already have the instructor solutions
			continue
		student_name = line[header.index("student_id")]
		students = Student.objects.filter(name=student_name)
		if len(students) == 1:
			student = students[0]
		else:
			student = Student(course=course, name=student_name)
			student.save()
		code = line[header.index("fun")]

		if run_hint_chain:
			results = do_hint_chain(code, student, problem)
			log(student_name + ": " + str(results[0]), "bug")
		else:
			start_time = time.time()
			state = SourceState(code=code, problem=problem, count=1, student=student)
			state = get_hint(state)
			state.save()
			end_time = time.time()
			results += str(state.id) + "\t" + str(state.score) + "\t" + str(end_time - start_time) + "\n"

	filename = LOG_PATH + problem_name + "_" + ("chain" if run_hint_chain else "results") + ".log"
	with open(filename, "w") as f:
		f.write(results)

	if run_profiler:
		# Check the profiler results
		sys.stdout = out
		pr.disable()
		s = io.StringIO()
		ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
		ps.print_stats()
		with open(LOG_PATH + problem_name + "_profile.log", "w") as f:
			f.write(outStream.getvalue() + s.getvalue())
	print('\a')

def generate_space(table, problem, keyword):
	# First, clear the solution space
	clear_solution_space(problem, keep_starter=False)

	header = table[0]
	starter = table[1]
	table = table[2:]

	# Add back in the starter code
	starter_state = SourceState(code=starter[header.index("fun")], problem=problem, count=1, student=Student.objects.get(id=1))
	starter_state = get_hint(starter_state)
	starter_state.save()
	problem.solution = starter_state
	problem.save()

	if keyword == "optimal":
		for line in table:
			code_id = line[header.index("id")]
			student_name = line[header.index("student_id")]
			students = Student.objects.filter(name=student_name)
			if len(students) == 1:
				student = students[0]
			else:
				student = Student(course=Course.objects.get(id=1), name=student_name)
				student.save()
			code = line[header.index("fun")]
			if int(code_id) % 10 == 0:
				log("Generating space: " + code_id, "bug")
			# Now for each piece of code, find the distance between that piece of code and the starter goal
			state = SourceState(code=code, problem=problem, count=1, student=student)
			state = get_hint(state)
			state.save()

def run_solution_space_improvement(f, problem_name, keyword):
	problem = Problem.objects.get(name=problem_name)
	table = parse_table(f)
	generate_space(table, problem, keyword)

	last_state = State.objects.latest('id')
	all_info = "id,correct_states,all_states,syntax_edit_weight,edit_weight,state_weight,goal_weight\n"
	correct_states = 1
	all_states = 1

	if keyword == "optimal":
		all_states = len(SourceState.objects.filter(problem=problem))
		correct_states = len(SourceState.objects.filter(problem=problem, score=1))

	header = table[0]
	table = table[2:]

	if keyword == "random":
		random.shuffle(table)

	for i in range(len(table)):
		line = table[i]
		code_id = line[header.index("id")]
		student_name = line[header.index("student_id")]
		students = Student.objects.filter(name=student_name)
		if len(students) == 1:
			student = students[0]
		else:
			student = Student(course=Course.objects.get(id=1), name=student_name)
			student.save()
		code = line[header.index("fun")]
		if i % 10 == 0:
			log("Checking distance: " + str(i), "bug")

		result, syntax_edits, semantic_edits, start_state, goal_state = do_hint_chain(code, student, problem)
		start_weight = diffAsts.getWeight(start_state)
		goal_weight = diffAsts.getWeight(goal_state) if goal_state != None else -1
		goal_code = goal_state.code if goal_state != None else ""
		all_info += str(code_id) + "," + str(correct_states) + "," + \
					str(all_states) + "," + str(syntax_edits) + \
					"," + str(semantic_edits) + "," + str(start_weight) + \
					"," + str(goal_weight) + "," + '"' + start_state.code + \
					'"' + "," + '"' + goal_code + '"' + "," + "\n"

		if keyword == "random":
			# Update the counts
			if start_state.score == 1:
				correct_states += 1
			all_states += 1
		else:
			# And after that, clear out all new states, unless we're building a space
			new_states = State.objects.filter(id__gt=last_state.id)
			new_states.delete()

	with open(LOG_PATH + problem_name + "_" + keyword + ".csv", "w") as f:
		f.write(all_info)
	print('\a')

def find_example_solutions(s, goals):
	most_common = [None, -1]
	furthest = [None, -1]
	closest = [None, 2]

	for g in goals:
		dist, _ = diffAsts.distance(s, g)
		if dist != 0:
			if g.count > most_common[1]:
				most_common = [g, g.count]
			if dist > furthest[1]:
				furthest = [g, dist]
			if dist < closest[1]:
				closest = [g, dist]
	if most_common[0] == None:
		examples = []
	else:
		examples = [most_common[0]]
		if furthest[0].code != most_common[0].code:
			examples.append(furthest[0])
		if closest[0].code != furthest[0].code and closest[0].code != most_common[0].code:
			examples.append(closest[0])
	return examples

def generate_cleaned_state(source_state):
	# First level of abstraction: convert to an AST and back. Cleans the code by removing comments, whitespace, etc.
	cleaned_code = printFunction(source_state.tree)
	prior_cleaned = list(CleanedState.objects.filter(problem=source_state.problem, code=cleaned_code))
	if len(prior_cleaned) == 0:
		cleaned_state = CleanedState(code=cleaned_code, problem=source_state.problem, 
									 score=source_state.score, count=1, 
									 feedback=source_state.feedback)
		cleaned_state.tree_source = source_state.tree_source
		cleaned_state.treeWeight = source_state.treeWeight
	elif len(prior_cleaned) == 1:
		cleaned_state = prior_cleaned[0]
		cleaned_state.count += 1
		if cleaned_code != cleaned_state.code:
			log("getHint\tgenerate_cleaned_state\tCode mismatch: \n" + cleaned_state.code + "\n" + cleaned_code, "bug")
	else:
		log("getHint\tgenerate_cleaned_state\tDuplicate code entries in cleaned: " + cleaned_code, "bug")
	cleaned_state.tree = source_state.tree
	cleaned_state = test(cleaned_state, forceRetest=True)
	if cleaned_state.score != source_state.score:
		log("getHint\tgenerate_cleaned_state\tScore mismatch: " + \
			str(source_state.score) + "," + str(cleaned_state.score) + "\n" + \
			source_state.code + "\n" + cleaned_state.code, "bug")
	return cleaned_state

def generate_anon_state(cleaned_state, given_names):
	# Mid-level: just anonymize the variable names TODO variableMap
	orig_tree = deepcopy(cleaned_state.tree)
	runGiveIds(orig_tree)
	anon_tree = deepcopy(orig_tree)
	anon_tree = anonymizeNames(anon_tree, given_names)
	if cleaned_state.count > 1 and cleaned_state.anon != None:
		anon_state = cleaned_state.anon
	else:
		anon_code = printFunction(anon_tree)
		prior_anon = list(AnonState.objects.filter(problem=cleaned_state.problem, code=anon_code))
		if len(prior_anon) == 0:
			anon_state = AnonState(code=anon_code, problem=cleaned_state.problem, 
								   score=cleaned_state.score, count=1,
								   feedback=cleaned_state.feedback) 
			anon_state.treeWeight = diffAsts.getWeight(anon_tree)
		else:
			if len(prior_anon) > 1:
				log("getHint\tgenerate_anon_state\tDuplicate code entries in anon: " + anon_code, "bug")
			anon_state = prior_anon[0]
			anon_state.count += 1
	anon_state.tree = anon_tree
	anon_state.tree_source = tree_to_str(anon_tree)
	anon_state = test(anon_state, forceRetest=True)
	if anon_state.score != cleaned_state.score:
		log("getHint\tgenerate_anon_state\tScore mismatch: " + \
			str(cleaned_state.score) + "," + str(anon_state.score) + "\n" + \
			cleaned_state.code + "\n" + anon_state.code, "bug")
	anon_state.orig_tree = orig_tree
	anon_state.orig_tree_source = tree_to_str(orig_tree)
	return anon_state

def generate_canonical_state(cleaned_state, anon_state, given_names):
	# Second level of abstraction: canonicalize the AST. Gets rid of redundancies.
	args = eval(anon_state.problem.arguments)
	orig_tree = deepcopy(cleaned_state.tree)
	runGiveIds(orig_tree)
	if type(args) != dict:
		log("getHint\tgenerate_canonical_state\tBad args format: " + anon_state.problem.arguments, "bug")
		args = { }
	if anon_state.count > 1 and anon_state.canonical != None:
		canonical_state = anon_state.canonical
		canonical_state.orig_tree = orig_tree
		canonical_state.orig_tree_source = tree_to_str(canonical_state.orig_tree)
		canonical_state.tree = deepcopy(canonical_state.orig_tree)
		canonical_state = getCanonicalForm(canonical_state, given_names, args)
	else:
		canonical_state = CanonicalState(code=cleaned_state.code, problem=cleaned_state.problem,
										 score=cleaned_state.score, count=1, 
										 feedback=cleaned_state.feedback)
		canonical_state.orig_tree = orig_tree
		canonical_state.orig_tree_source = tree_to_str(canonical_state.orig_tree)
		canonical_state.tree = deepcopy(canonical_state.orig_tree)
		canonical_state = getCanonicalForm(canonical_state, given_names, args)
		canonical_state = test(canonical_state, forceRetest=True)
		if canonical_state.score != cleaned_state.score:
			log("getHint\tgenerate_canonical_state\tScore mismatch: " + str(cleaned_state.score) + "," + str(canonical_state.score) + "\n" + cleaned_state.code + "\n" + canonical_state.code, "bug")
		prior_canon = list(CanonicalState.objects.filter(problem=cleaned_state.problem, code=canonical_state.code))
		if len(prior_canon) == 0:
			canonical_state.tree_source = tree_to_str(canonical_state.tree)
			canonical_state.treeWeight = diffAsts.getWeight(canonical_state.tree)
		else:
			if len(prior_canon) > 1:
				log("getHint\tgenerate_canonical_state\tDuplicate code entries in canon: " + canonical_state.code, "bug")
			prev_tree = canonical_state.tree
			canonical_state = prior_canon[0]
			canonical_state.count += 1
			canonical_state.tree = prev_tree
			canonical_state.orig_tree = orig_tree
			canonical_state.orig_tree_source = tree_to_str(orig_tree)

	return canonical_state

def generate_states(source_state, given_names):
	# Convert to cleaned, anonymous, and canonical states

	cleaned_state = generate_cleaned_state(source_state)
	cleaned_state.save()
	anon_state = generate_anon_state(cleaned_state, given_names)
	anon_state.save()
	canonical_state = generate_canonical_state(cleaned_state, anon_state, given_names)
	canonical_state.save()

	source_state.cleaned = cleaned_state
	cleaned_state.anon = anon_state
	anon_state.canonical = canonical_state

	return (cleaned_state, anon_state, canonical_state)

def save_states(source, cleaned, anon, canonical):
	for s in [anon, canonical]:
		g = s.goal
		if g != None:
			g.save()
			s.goal = g
		next_chain = [s]
		while s.next != None:
			s = s.next
			next_chain.append(s)
		for i in range(len(next_chain)-1, 0, -1):
			n = next_chain[i]
			g = n.goal
			if g != None:
				if g.goal != None:
					log("getHint\tsave_states\tWeird goal goal: " + str(g.score) + "," + g.code, "bug")
					log("getHint\tsave_states\tWeird goal goal: " + str(g.goal.score) + "," + g.goal.code, "bug")
				g.save()
				n.goal = g
			n.save()
			next_chain[i-1].next = n

	if source.hint != None:
		source.hint.save()
	canonical.save()
	anon.save()
	cleaned.save()
	source.save()

def test_code(source_state):
	# Parse the code, get tree and treeWeight
	try:
		source_state.tree = ast.parse(source_state.code)
		source_state.tree_source = tree_to_str(source_state.tree)
		source_state.treeWeight = diffAsts.getWeight(source_state.tree)
	except Exception as e:
		# Couldn't parse
		source_state.tree = None

	# Test the code, get score and feedback
	source_state = test(source_state)
	return source_state

def run_tests(source_state):
	source_state = test_code(source_state)

	args = eval(source_state.problem.arguments)
	given_code = ast.parse(source_state.problem.given_code)
	imports = getAllImports(source_state.tree) + getAllImports(given_code)
	inp = imports + (list(args.keys()) if type(args) == dict else [])
	given_names = [str(x) for x in inp]

	(cleaned_state, anon_state, canonical_state) = generate_states(source_state, given_names)
	save_states(source_state, cleaned_state, anon_state, canonical_state)
	return source_state

def get_hint(source_state, hint_level="default"):
	source_state = test_code(source_state)

	# If we can't parse their solution, use a simplified version of the algorithm with textual edits
	if source_state.tree == None:
		return getSyntaxHint(source_state, "syntax_" + hint_level)

	args = eval(source_state.problem.arguments)
	given_code = ast.parse(source_state.problem.given_code)
	imports = getAllImports(source_state.tree) + getAllImports(given_code)
	inp = imports + (list(args.keys()) if type(args) == dict else [])
	given_names = [str(x) for x in inp]

	# Setup the correct states we need for future work
	goals = list(AnonState.objects.filter(problem=source_state.problem, score=1)) + \
			list(CanonicalState.objects.filter(problem=source_state.problem, score=1))
	for goal in goals:
		goal.tree = str_to_tree(goal.tree_source)

	(cleaned_state, anon_state, canonical_state) = generate_states(source_state, given_names)

	states = list(AnonState.objects.filter(problem=source_state.problem)) + \
			 list(CanonicalState.objects.filter(problem=source_state.problem))

	if source_state.score == 1:
		examples = find_example_solutions(source_state, goals)
		hint = Hint(level="examples")
		hint.message = "Your solution is already correct!"
		if len(examples) > 0:
			hint.message += " If you're interested, here are some other correct solutions:\n"
			for example in examples:
				hint.message += "<b>" + example.code + "</b>\n\n"
		hint.save()
		source_state.hint = hint
	else:
		# Determine the hint level
		if hint_level == "default":
			submissions = list(SourceState.objects.filter(student=source_state.student))
			if len(submissions) > 0 and submissions[-1].hint != None and submissions[-1].problem == source_state.problem and \
				submissions[-1].code == source_state.code:
				if submissions[-1].hint.level == "next_step":
					hint_level = "structure"
				elif submissions[-1].hint.level == "structure":
					hint_level = "half_steps"
				elif submissions[-1].hint.level in ["half_steps", "solution"]:
					hint_level = "solution"
				else:
					hint_level = "next_step"
			else:
				hint_level = "next_step"

		# If necessary, generate next/goal states for the anon and canonical states
		if anon_state.goal == None:
			generateNextStates.getNextState(anon_state, goals, states)
		else:
			# Is there a better goal available now?
			best_goal = generateNextStates.chooseGoal(anon_state, goals, states)
			if anon_state.goal != best_goal:
				generateNextStates.getNextState(anon_state, goals, states, best_goal)
		if canonical_state.goal == None:
			generateNextStates.getNextState(canonical_state, goals, states)
		else:
			# Is there a better goal available now?
			best_goal = generateNextStates.chooseGoal(canonical_state, goals, states)
			if canonical_state.goal != best_goal:
				generateNextStates.getNextState(canonical_state, goals, states, best_goal)

		# Then choose the best path to use
		anon_distance, _ = diffAsts.distance(anon_state, anon_state.goal, forceReweight=True)
		canonical_distance, _ = diffAsts.distance(canonical_state, canonical_state.goal, forceReweight=True)
		if anon_distance <= canonical_distance:
			used_state = anon_state
		else:
			used_state = canonical_state

		while True:
			if used_state.next == None:
				log("getHint\tget_hint\tCould not find next state for state " + str(used_state.id), "bug")
				break
			next_state = used_state.next
			if not hasattr(next_state, "tree"):
				next_state.tree = str_to_tree(next_state.tree_source)
			edit = diffAsts.diffAsts(used_state.tree, next_state.tree)
			edit, _ = generateNextStates.updateChangeVectors(edit, used_state.tree, used_state.tree)
			if not hasattr(used_state, "orig_tree"):
				if hasattr(used_state, "orig_tree_source") and used_state.orig_tree_source != "":
					used_state.orig_tree = str_to_tree(used_state.orig_tree_source)
				else:
					log("getHint\tgetHint\tWhy no orig_tree?!?!" + str(used_state), "bug")
			edit = mapEdit(used_state.tree, used_state.orig_tree, edit)
			if len(edit) == 0:
				if next_state.next != None:
					if not hasattr(next_state, "orig_tree") and \
					  (not hasattr(next_state, "orig_tree_source") or \
					   next_state.orig_tree_source == ""):
						log("Why no orig_tree?!?" + str(next_state), "bug")
						next_state.orig_tree = used_state.orig_tree
					used_state = next_state
					continue
				else:
					log("No edit found: " + str(used_state), "bug")
			hint = formatHints(used_state, edit, hint_level, used_state.orig_tree) # generate the right level of hint
			source_state.edit = edit
			source_state.hint = hint
			source_state.goal = used_state.goal
			break

	# Save all the states!
	save_states(source_state, cleaned_state, anon_state, canonical_state)
	return source_state

