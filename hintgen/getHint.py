import ast
from .canonicalize import getAllImports, runGiveIds, anonymizeNames, getCanonicalForm, propogateMetadata, propogateNameMetadata
from .path_construction import diffAsts, generateNextStates
from .individualize import mapEdit
from .generate_message import formatHints
from .getSyntaxHint import getSyntaxHint

from .test import test
from .display import printFunction
from .astTools import deepcopy, tree_to_str, str_to_tree
from .tools import log, parse_table

from .models import *

# def hintLog(msg, user, problem, code, next=None, goal=None, hint=None):
# 	nextStr = repr(next) + "\t" if next != None else "\t"
# 	goalStr = repr(goal) + "\t" if goal != None else "\t"
# 	hintStr = repr(hint) if hint != None else ""
# 	log("getHint\t" + repr(msg) + "\t" + repr(user) + "\t" + repr(problem) + "\t" + \
# 			repr(code) + "\t" + nextStr + goalStr + hintStr + "\n")

# def doHintChain(code, user, problem, interactive=False):
# 	state = tools.load_state([("id", user + "_1"), ("fun", code)], problem)
# 	startState = state.deepcopy()
# 	state.fun = code
# 	failedTests = True
# 	stepCount = editCount = chrCount = 0
# 	cutoff = 60
# 	printedStates = "************************"
# 	allEdits = []
# 	# Keep applying hints until either the state is correct or
# 	# you've reached the cutoff. The cap is there to cut off infinite loops.
# 	while stepCount < cutoff:
# 		stepCount += 1
# 		printedStates += "State: \n" + state.fun + "\n"
# 		[hint, location, edit, goal] = getHint(state.fun, 
# 			user + "_" + str(stepCount), problem, includeLocation=True, 
# 			returnEdit=True, returnGoal=True, hintLevel=3)
# 		print hint
# 		if goal != None:
# 			printedStates += "Goal: \n" + goal + "\n"

# 		if edit != None and len(edit) > 0:
# 			# First check for infinitely-looping edits
# 			printedStates += hint + "\n" + str(edit) + "\n"
# 			# If we've seen this exact change before, it's a loop
# 			if isinstance(edit[0], ChangeVector):
# 				if edit in allEdits:
# 					s = "REPEATING EDITS"
# 					log(s + "\n" + printedStates, "bug")
# 					return s, stepCount, editCount, chrCount
# 			elif isinstance(edit[0], SyntaxEdit):
# 				if len(allEdits) > 0:
# 					current = edit[0]
# 					prev = allEdits[-1][0]
# 					# If we're adding and then deleting the same thing, it's a loop
# 					if current.editType == "-" and prev.editType == "+" and \
# 						current.line == prev.line and current.col == prev.col and \
# 						current.text == prev.text and current.newText == prev.newText:
# 						s = "REPEATING EDITS"
# 						log(s + "\n" + printedStates, "bug")
# 						return s, stepCount, editCount, chrCount
# 			else:
# 				log("Unknown edit type?" + repr(edit[0]), filename="bug")

# 			if isinstance(edit[0], ChangeVector):
# 				editCount += path_construction.diffAsts.getChangesWeight(edit, False)
# 				newTree = state.tree
# 				for e in edit:
# 					e.start = newTree
# 					newTree = e.applyChange()

# 				if newTree == None:
# 					s = "EDIT BROKE"
# 					log(s + "\n" + printedStates, "bug")
# 					return s, stepCount, editCount, chrCount
# 				newFun = display.printFunction(newTree, 0)
# 			else: # Fixing a syntax error
# 				newFun = getSyntaxHint.applyChanges(state.fun, edit)
# 				chrCount += sum(len(c.text) + len(c.newText) for c in edit)

# 			allEdits.append(edit)
# 			state = tools.load_state([("id", user + "_" + str(stepCount+1)), ("fun", newFun)], problem)
# 			state.fun = newFun
# 		elif state.score != 1:
# 			s = "NO NEXT STEP"
# 			log(s + "\n" + printedStates, "bug")
# 			return s, stepCount, editCount, chrCount
# 		else: # break out when the score reaches 1
# 			break
# 		if interactive:
# 			raw_input("")

# 	if state.score == 1:
# 		if stepCount == 1:
# 			s = "Started Correct"
# 		else: # Got through the hints! Woo!
# 			s = "Success"
# 	else: # These are the bad cases
# 		if stepCount >= cutoff:
# 			s = "TOO LONG"
# 			log(s + "\n" + printedStates, "bug")
# 		else:
# 			s = "BROKEN"
# 			log(s + "\n" + printedStates, "bug")
# 	return s, stepCount, editCount, chrCount

def import_code_as_states(f, course_id, problem_name):
	# Import a CSV file of code into the database
	course = Course.objects.get(id=course_id)
	problem = course.problems.get(name=problem_name)
	table = parse_table(f)
	header = table[0]
	table = table[1:]
	for line in table:
		print(line)
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
		state = SourceState(code=code, problem=problem, count=1, student=student)
		state = get_hint(state)
		state.save()

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
	else:
		log("getHint\tgenerate_cleaned_state\tDuplicate code entries in cleaned: " + cleaned_code, "bug")
	cleaned_state.tree = source_state.tree
	old_score = source_state.score
	cleaned_state = test(cleaned_state, forceRetest=True)
	if cleaned_state.score != old_score:
		log("getHint\tgenerate_cleaned_state\tScore mismatch: " + str(old_score) + "," + str(cleaned_state.score) + \
			"\n" + source_state.code + "\n" + cleaned_state.code, "bug")
	return cleaned_state

def generate_anon_state(cleaned_state, given_names):
	# Mid-level: just anonymize the variable names TODO variableMap
	if cleaned_state.count > 1 and cleaned_state.anon != None:
		anon_state = cleaned_state.anon
		anon_state.tree = str_to_tree(anon_state.tree_source)
		anon_state.orig_tree = str_to_tree(anon_state.orig_tree_source)
	else:
		orig_tree = deepcopy(cleaned_state.tree)
		runGiveIds(orig_tree)
		anon_tree = deepcopy(orig_tree)
		anon_tree = anonymizeNames(anon_tree, given_names)
		anon_code = printFunction(anon_tree)
		prior_anon = list(AnonState.objects.filter(problem=cleaned_state.problem, code=anon_code))
		if len(prior_anon) == 0:
			anon_state = AnonState(code=anon_code, problem=cleaned_state.problem, 
								   score=cleaned_state.score, count=1,
								   feedback=cleaned_state.feedback) 
			anon_state.tree_source = tree_to_str(anon_tree)
			anon_state.treeWeight = diffAsts.getWeight(anon_tree)
		elif len(prior_anon) == 1:
			anon_state = prior_anon[0]
			anon_state.count += 1
		else:
			log("getHint\tgenerate_anon_state\tDuplicate code entries in anon: " + anon_code, "bug")
		anon_state.tree = anon_tree
		anon_state.orig_tree = orig_tree
		anon_state.orig_tree_source = tree_to_str(orig_tree)
	return anon_state

def generate_canonical_state(cleaned_state, anon_state, given_names):
	# Second level of abstraction: canonicalize the AST. Gets rid of redundancies.
	args = eval(anon_state.problem.arguments)
	if anon_state.count > 1 and anon_state.canonical != None:
		canonical_state = anon_state.canonical
		canonical_state.tree = str_to_tree(canonical_state.tree_source)
		canonical_state.orig_tree = str_to_tree(canonical_state.orig_tree_source)
	else:
		canonical_state = CanonicalState(code=cleaned_state.code, problem=cleaned_state.problem,
										 score=cleaned_state.score, count=1, 
										 feedback=cleaned_state.feedback)
		orig_tree = deepcopy(cleaned_state.tree)
		runGiveIds(orig_tree)
		canonical_state.orig_tree = orig_tree
		canonical_state.orig_tree_source = tree_to_str(canonical_state.orig_tree)
		canonical_state.tree = deepcopy(canonical_state.orig_tree)
		canonical_state = getCanonicalForm(canonical_state, given_names, args)
		prior_canon = list(CanonicalState.objects.filter(problem=cleaned_state.problem, code=canonical_state.code))
		if len(prior_canon) == 0:
			canonical_state.tree_source = tree_to_str(canonical_state.tree)
			canonical_state.treeWeight = diffAsts.getWeight(canonical_state.tree)
		elif len(prior_canon) == 1:
			prev_tree = canonical_state.tree
			canonical_state = prior_canon[0]
			canonical_state.count += 1
			canonical_state.tree = prev_tree
			canonical_state.orig_tree = orig_tree
		else:
			log("getHint\tgenerate_canonical_state\tDuplicate code entries in canon: " + canonical_state.code, "bug")
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
					print(str(g.score) + "," + g.code)
					print(str(g.goal.score) + "," + g.goal.code)
				g.save()
				n.goal = g
			n.save()
			next_chain[i-1].next = n

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
	given_names = [str(x) for x in list(args.keys()) + imports]

	(cleaned_state, anon_state, canonical_state) = generate_states(source_state, given_names)
	save_states(source_state, cleaned_state, anon_state, canonical_state)
	return source_state

def get_hint(source_state, hintLevel=-1):
	source_state = test_code(source_state)

	# If we can't parse their solution, use a simplified version of the algorithm with textual edits
	if source_state.tree == None:
		return getSyntaxHint(source_state)

	args = eval(source_state.problem.arguments)
	given_code = ast.parse(source_state.problem.given_code)
	imports = getAllImports(source_state.tree) + getAllImports(given_code)
	given_names = [str(x) for x in list(args.keys()) + imports]

	(cleaned_state, anon_state, canonical_state) = generate_states(source_state, given_names)

	# Setup the correct states we need for future work
	goals = list(AnonState.objects.filter(problem=source_state.problem, score=1)) + \
			list(CanonicalState.objects.filter(problem=source_state.problem, score=1))
	for goal in goals:
		goal.tree = str_to_tree(goal.tree_source)
		#goal.tree = propogateMetadata(goal.tree, args, {}, [0]) # This shouldn't be necessary...
		#goal.tree = propogateNameMetadata(goal.tree, given_names)

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
			generateNextStates.getNextState(anon_state, goals)
		else:
			# Is there a better goal available now?
			best_goal = generateNextStates.chooseGoal(anon_state, goals)
			if anon_state.goal != best_goal:
				generateNextStates.getNextState(anon_state, goals, best_goal)
		if canonical_state.goal == None:
			generateNextStates.getNextState(canonical_state, goals)
		else:
			# Is there a better goal available now?
			best_goal = generateNextStates.chooseGoal(canonical_state, goals)
			if canonical_state.goal != best_goal:
				generateNextStates.getNextState(canonical_state, goals, best_goal)

		# Then choose the best path to use
		anon_distance, _ = diffAsts.distance(anon_state, anon_state.goal, forceReweight=True)
		canonical_distance, _ = diffAsts.distance(canonical_state, canonical_state.goal, forceReweight=True)
		if anon_distance >= canonical_distance:
			used_state = anon_state
		else:
			used_state = canonical_state

		while True:
			next_state = used_state.next
			if not hasattr(next_state, "tree"):
				next_state.tree = str_to_tree(next_state.tree_source)
			if not hasattr(next_state, "orig_tree") and next_state.orig_tree_source!="":
				next_state.orig_tree = str_to_tree(next_state.orig_tree_source)
			edit = diffAsts.diffAsts(used_state.tree, next_state.tree)
			edit, _ = generateNextStates.updateChangeVectors(edit, used_state.tree, used_state.tree)
			edit = mapEdit(used_state.tree, used_state.orig_tree, edit)
			if len(edit) == 0:
				if next_state.next != None:
					next_state = next_state.next
					continue
			hint = formatHints(used_state, edit, hint_level, used_state.orig_tree) # generate the right level of hint
			source_state.hint = hint
			break

	# Save all the states!
	save_states(source_state, cleaned_state, anon_state, canonical_state)
	return source_state

