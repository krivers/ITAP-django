import ast, copy, difflib, os, random
from .tools import log, powerSet, fastPowerSet
from .astTools import structureTree
from .paths import TEST_PATH
from .display import printFunction
from .lexerSyntaxHint import getLexerSyntaxHint
from .SyntaxEdit import SyntaxEdit
from .models import SourceState, Hint

def smartSplit(code):
	tokens = []
	i = 0
	currentText = ""
	line = currentLine = 1
	col = currentCol = 1
	totalCol = currentTotalCol = 0
	while i < len(code):
		chr = code[i]
		if len(currentText) == 0:
			if chr == "\n" or chr == "\t" or chr == " ": # TODO: how to find the right number of columns for tabs?
				tokens.append([chr, line, col, totalCol])
			else:
				currentText = chr
				currentLine = line
				currentCol = col
				currentTotalCol = totalCol
		else:
			if chr == "\n" or chr == "\t" or chr == " ":
				tokens.append([currentText, currentLine, currentCol, currentTotalCol])
				tokens.append([chr, line, col, totalCol])
				currentText = ""
			else:
				currentText += chr
		col += 1
		totalCol += 1
		if chr == "\n":
			line += 1
			col = 1
		i += 1
	if currentText != "":
		tokens.append([currentText, currentLine, currentCol, currentTotalCol])
	return tokens

def getTextDiff(code1, code2):
	differ = difflib.Differ()
	changes = []
	codeTokens1 = smartSplit(code1)
	tokens1 = [t[0] for t in codeTokens1]
	codeTokens2 = smartSplit(code2)
	tokens2 = [t[0] for t in codeTokens2]
	dif = differ.compare(tokens1, tokens2)
	j = 0
	type = ""
	text = ""
	line = 0
	col = 0
	totalCol = 0
	for chr in dif:
		changeType = chr[0]
		changeChr = chr[2:]
		if changeType != type or (len(text) > 0 and text[-1] == "\n"):
			if text != "":
				changes.append(SyntaxEdit(line, col, totalCol, type, text))
			text = ""
			type = changeType
			if changeType in ["-", "+"]:
				text = changeChr
				if j < len(codeTokens1):
					line = codeTokens1[j][1]
					col = codeTokens1[j][2]
					totalCol = codeTokens1[j][3]
				else:
					line = codeTokens1[j-1][1]
					col = codeTokens1[j-1][2] + len(codeTokens1[j-1][0])
					totalCol = codeTokens1[j-1][3] + len(codeTokens1[j-1][0])
		else:
			if changeType in ["-", "+"]:
				text += changeChr
		if changeType in ["-", " "]:
			j += 1 # move forward in the codeTokens list
	if text != "":
		changes.append(SyntaxEdit(line, col, totalCol, type, text))
	return changes

def combineSameLocationChanges(changes):
	"""Destructively modifies changes"""
	j = 1
	while j < len(changes):
		# if possible, combine - and + changes at the same location into -+ changes
		if (changes[j-1].totalCol == changes[j].totalCol) and ((changes[j-1].editType + changes[j].editType) == "+-"):
			changes[j-1].editType = "-+"
			changes[j-1].newText = changes[j-1].text
			changes[j-1].text = changes[j].text
			changes[j:] = changes[j+1:]
		elif (changes[j-1].totalCol == changes[j].totalCol - len(changes[j-1].text)) and \
				(changes[j-1].editType + changes[j].editType) == "-+":
			changes[j-1].editType = "-+"
			changes[j-1].newText = changes[j].text
			changes[j:] = changes[j+1:]
		j += 1
	return changes

def combineSmartSyntaxEdits(changes):
	j = 1
	while j < len(changes):
		if j < 1:
			j = 1
			if len(changes) == 1:
				break
		if changes[j-1].totalCol == changes[j].totalCol:
			if changes[j-1].editType == changes[j].editType and changes[j-1].editType in ["indent", "deindent", "-"]:
				changes[j-1].text += changes[j].text
				changes.pop(j)
				continue
			elif changes[j-1].editType in ["deindent", "-"] and changes[j].editType in ["deindent", "-"]:
				changes[j-1].text += changes[j].text
				changes[j-1].editType = "-" # combining them, so it isn't deindent anymore
				changes.pop(j)
				j -= 1
				continue
			elif changes[j-1].editType in ["deindent", "-"] and changes[j].editType in ["indent", "+"]:
				changes[j-1].editType = "+-"
				changes[j-1].newText = changes[j].text
				changes.pop(j)
				continue
			elif changes[j-1].editType == "+-" and changes[j].editType in ["deindent", "-"]:
				if changes[j-1].newText == changes[j].text:
					changes[j-1].editType = "deindent" if changes[j-1].text.replace(" ", "").replace("\t", "") == "" else "-"
					changes[j-1].newText = ""
					changes.pop(j)
					j -= 1
					continue
				elif changes[j].text in changes[j-1].newText and changes[j-1].newText.find(changes[j].text) == 0:
					# the next edit is at the start- just remove it now
					changes[j-1].newText = changes[j-1].newText[len(changes[j].text):]
					changes.pop(j)
					continue
				elif changes[j-1].newText in changes[j].text and changes[j].text.find(changes[j-1].newText) == 0:
					changes[j-1].editType = "deindent" if changes[j-1].text.replace(" ", "").replace("\t", "") == "" else "-"
					changes[j].text = changes[j].text[len(changes[j-1].newText):]
					changes[j-1].newText = ""
					j -= 1
					continue
		elif changes[j-1].editType in ["+", "indent"] and changes[j].editType in ["+", "indent"]:
			if changes[j-1].totalCol + len(changes[j-1].text) == changes[j].totalCol:
				changes[j-1].text += changes[j].text
				changes[j-1].editType = "indent" if changes[j-1].text.replace(" ", "").replace("\t", "") == "" else "+"
				changes.pop(j)
				j -= 1
				continue
		elif changes[j-1].editType == "+-" and changes[j].editType in ["+", "indent"]:
			if changes[j-1].totalCol + len(changes[j-1].newText) - len(changes[j-1].text) + 1 == changes[j].totalCol:
				changes[j-1].newText += changes[j].text
				changes.pop(j)
				continue
			elif changes[j].editType == "indent" and changes[j-1].line == changes[j].line:
				if (changes[j-1].newText.strip(" ") == changes[j].text.strip(" ") == "") or \
				   (changes[j-1].newText.strip("\t") == changes[j].text.strip("\t") == ""):
					changes[j-1].newText += changes[j].text
					changes.pop(j)
					continue
		elif changes[j-1].editType == "+-" and changes[j].editType == "deindent" and changes[j-1].line == changes[j].line:
			# Special case: it's okay to combine if the +- merged text with the old text even if totalCol isn't the same
			# if we're just trimming whitespace
			if (changes[j-1].newText.strip(" ") == changes[j].text.strip(" ") == "") or \
			   (changes[j-1].newText.strip("\t") == changes[j].text.strip("\t") == ""):
				if len(changes[j-1].newText) == len(changes[j].text):
					changes[j-1].editType = "deindent" if changes[j-1].text.replace(" ", "").replace("\t", "") == "" else "-"
					changes[j-1].newText = ""
					changes.pop(j)
					j -= 1
					continue
				elif len(changes[j-1].newText) < len(changes[j].text):
					changes[j].text = changes[j].text[len(changes[j-1].newText):]
					changes[j-1].editType = "deindent" if changes[j-1].text.replace(" ", "").replace("\t", "") == "" else "-"
					changes[j-1].newText = ""
					j -= 1
					continue
				else:
					changes[j-1].newText = changes[j-1].newText[len(changes[j].text):]
					changes.pop(j)
					continue
		j += 1
	return changes

def getMinimalChanges(changes, code, cutoff=None):
	# Only do the power set if the # of changes is reasonable
	if len(changes) < 8:
		changesPowerSet = powerSet(changes)
	elif len(changes) < 50:
		changesPowerSet = fastPowerSet(changes)
	else: # too large, we can't even do the fast power set because it will overwhelm memory
		changesPowerSet = [changes]
	sortList = list(map(lambda x : (x, sum(len(item.text) + len(item.newText) for item in x)), changesPowerSet))
	if cutoff != None:
		sortList = list(filter(lambda x : x[1] < cutoff, sortList))
	sortList.sort(key=lambda x : x[1])
	usedChange = combineSameLocationChanges(changes)
	usedCode = applyChanges(code, usedChange)
	for (change, l) in sortList:
		change = combineSameLocationChanges(change)
		tmpSource = applyChanges(code, change)
		try:
			ast.parse(tmpSource)
			usedChange = change
			usedCode = tmpSource
			break
		except:
			pass
	return (usedChange, usedCode)

def applyChanges(code, changes):
	colOffset = 0
	for change in changes:
		totalCol = change.totalCol
		if totalCol < 0:
			log("getSyntaxHint\tapplyChanges\tBad totalCol: " + str(changes) + "\n" + code, "bug")
		changeType = change.editType
		changeText = change.text
		updatedTotal = totalCol + colOffset
		if changeType in ["-", "deindent"]:
			code = code[:updatedTotal] + code[updatedTotal + len(changeText):]
			colOffset -= len(changeText)
		elif changeType in ["+", "indent"]:
			code = code[:updatedTotal] + changeText + code[updatedTotal:]
			colOffset += len(changeText)
		elif changeType in ["-+", "+-"]:
			changeText2 = change.newText
			code = code[:updatedTotal] + changeText2 + code[updatedTotal + len(changeText):]
			colOffset = colOffset - len(changeText) + len(changeText2)
		else:
			log("getSyntaxHint\tapplyChanges\tMissing change type: " + str(changeType), filename="bug")
	return code

def generateEditHint(edit):
	hint = ""
	if edit.editType in ["-", "+"]:
		if "\t" in edit.text and edit.text.replace("\t", "") == "":
			text = str(len(edit.text)) + " tab" + ("s" if len(edit.text) > 1 else "")
		elif " " in edit.text and edit.text.replace(" ", "") == "":
			text = str(len(edit.text)) + " space" + ("s" if len(edit.text) > 1 else "")
		else:
			text = "\"" + edit.text + "\""
		hint += "On line " + str(edit.line) + " in column " + str(edit.col) + ", " + \
				("delete " if edit.editType == "-" else "add ") + "<b>" + text + "</b>"
	elif edit.editType in ["-+", "+-"]:
		if "\t" in edit.text and edit.text.replace("\t", "") == "":
			oldText = str(len(edit.text)) + " tab" + ("s" if len(edit.text) > 1 else "")
		elif " " in edit.text and edit.text.replace(" ", "") == "":
			oldText = str(len(edit.text)) + " space" + ("s" if len(edit.text) > 1 else "")
		else:
			oldText = "\"" + edit.text + "\""
		if "\t" in edit.newText and edit.newText.replace("\t", "") == "":
			newText = str(len(edit.newText)) + " tab" + ("s" if len(edit.newText) > 1 else "")
		elif " " in edit.text and edit.text.replace(" ", "") == "":
			newText = str(len(edit.newText)) + " space" + ("s" if len(edit.newText) > 1 else "")
		else:
			newText = "\"" + edit.newText + "\""
		hint += "On line " + str(edit.line) + " in column " + str(edit.col) + ", replace " + \
				"<b>" + oldText + "</b> with <b>" + newText + "</b>"
	elif edit.editType in ["deindent", "indent"]:
		length = len(edit.text)
		hint += "On line " + str(edit.line) + " in column " + str(edit.col) + \
				(" unindent " if edit.editType == "deindent" else " indent ") + "the code by " + \
				"<b>" + str(length) + " " + ("space" if edit.text[0] == " " else "tab") + ("s" if length > 1 else "") + "</b>"
	return hint

def generateHintText(hint_level, sourceState, bestChange, bestCode):
	if hint_level == "syntax_next_step":
		hint = "To help your code parse, make this change: " + generateEditHint(bestChange[0])
		hint += "\nIf you need more help, ask for feedback again."
	elif hint_level == "syntax_structure":
		# generate structure hint
		try:
			t = ast.parse(bestCode)
			structure = structureTree(t)
			hint = "To help your code parse, aim for the following code structure:\n<b>" + printFunction(structure, 0) + "</b>"
		except Exception as e:
			log("getSyntaxHint\tgenerateHintText\tCouldn't parse: " + str(e), "bug")
			hint = "Sorry, an error occurred."
		hint += "\nIf you need more help, ask for feedback again."
	elif hint_level == "syntax_half_steps":
		if len(bestChange)//2 > 1:
			numChanges = len(bestChange)//2
		else:
			numChanges = len(bestChange)
		# include half of the edits
		hint = "To help your code parse, make the following changes: \n"
		for i in range(numChanges):
			hint += generateEditHint(bestChange[i]) + "\n"
		hint += "\nIf you need more help, ask for feedback again."
	elif hint_level == "syntax_solution":
		hint = "Here is a new version of your program that should be able to compile: \n<b>" + bestCode + "</b>"
	else:
		log("getSyntaxHint\tgenerateHintText\tUnrecognized hint level: " + hint_level, "bug")
	return hint


def getSyntaxHint(source_state, hint_level):
	# First, try Aayush's approach
	# f = TEST_PATH + "tmp/temporarycode" + str(random.randint(0,100000)) + ".py"
	# currentCode = source_state.code
	# treeParses = False
	# allChanges = []
	# failedString = ""
	# while not treeParses and len(allChanges) < 10:
	# 	with open(f, "w") as tmp:
	# 		tmp.write(currentCode)
 
	# 	bestChange = getLexerSyntaxHint(f)
	# 	if bestChange == None or len(bestChange) == 0: #treeParses will still be False
	# 		if source_state.score == 1:
	# 			return
	# 		s = "No change found\n"
	# 		s += repr(currentCode) + "\n"
	# 		failedString += s
	# 		break
	# 	else:
	# 		bestCode = applyChanges(currentCode, bestChange)
	# 		s = repr(bestChange) + "\n" + repr(currentCode) + "\n" + repr(bestCode) + "\n"
	# 		try:
	# 			a = ast.parse(bestCode)
	# 			allChanges += bestChange
	# 			currentCode = bestCode
	# 			treeParses = True
	# 			s += "Successful parse!\n"
	# 			failedString += s
	# 		except Exception as e:
	# 			# you can do subtract/deindent multiple times, 
	# 			# but if you're changing/adding in the same location multiple times,
	# 			# while interchanging with something else, we have an infinite loop
	# 			if len(bestChange) == 1 and bestChange[0].editType not in ["-", "deindent"] and \
	# 				bestChange[0] in allChanges and bestChange[0] != allChanges[-1]:
	# 				s += "Infinite loop!\n"
	# 				failedString += s
	# 				break
	# 			else:
	# 				s += "Failed parse: " + str(e) + "\n"
	# 				failedString += s
	# 				allChanges += bestChange
	# 				currentCode = bestCode

	# if os.path.exists(f):
	# 	os.remove(f)
	treeParses = False
	if treeParses:
		bestChange = combineSmartSyntaxEdits(allChanges)
		bestCode = currentCode
	else:
		# If that fails, do the basic path construction approach
		allSources = SourceState.objects.filter(problem=source_state.problem).exclude(tree_source="")
		codes = list(set([state.code for state in allSources]))
		allChanges = []
		bestChange = None
		bestCode = None
		bestLength = None
		for state in codes:
			changes = getTextDiff(source_state.code, state)
			# Now generate all possible combinations of these changes
			(usedChange, usedCode) = getMinimalChanges(changes, source_state.code, cutoff=bestLength)
			l = sum(len(usedChange[i].text) + len(usedChange[i].newText) for i in range(len(usedChange)))
			if bestLength == None or l < bestLength:
				bestChange, bestCode, bestLength = usedChange, usedCode, l
				if bestLength == 1:
					break
		# Only apply one change at a time
		if bestChange == None: # no correct states available
			log("syntaxHint\tgetSyntaxHint\tNo parsing states in " + source_state.problem.name, "bug")
			hint = Hint(message="No parsing states found for this problem", level="syntax error")
			hint.save()
			source_state.hint = hint
			source_state.save()
			return source_state


	# Determine the hint level
	if hint_level == "syntax_default":
		submissions = list(SourceState.objects.filter(student=source_state.student))
		if len(submissions) > 0 and submissions[-1].hint != None and submissions[-1].problem == source_state.problem and \
			submissions[-1].code == source_state.code:
			prev_hint_level = submissions[-1].hint.level
			if "syntax" in prev_hint_level:
				if prev_hint_level == "syntax_next_step":
					hint_level = "syntax_structure"
				elif prev_hint_level == "syntax_structure":
					hint_level = "syntax_half_steps"
				elif prev_hint_level in ["syntax_half_steps", "syntax_solution"]:
					hint_level = "syntax_solution"
				else:
					hint_level = "syntax_next_step"
			else:
				hint_level = "syntax_next_step"
		else:
			hint_level = "syntax_next_step"

	message = generateHintText(hint_level, source_state, bestChange, bestCode)
	firstEdit = bestChange[0]
	hint = Hint(message=message, level=hint_level, line=firstEdit.line, col=firstEdit.col)
	hint.save()
	source_state.edit = bestChange
	source_state.hint = hint
	source_state.save()
	return source_state
