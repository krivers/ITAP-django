import os, random, sys
from .parser import parser, lexer
from .parser.stateList import stateList
from .parser.sameTokens import sameTokens, tokenReverseDict
from .SyntaxEdit import SyntaxEdit
from .tools import log
from .paths import TEST_PATH

# columns fix 									fixed
# get rid of subprocesses						Not-fixed
# else if -> elif 								fixed
# open paranthesis 								Not-fixed
# unclosed paranthesis                          Not-fixed
# unclosed string 								Not-fixed
# illegal character 							Temp-fix : Delete character

# finds the TOKENS value, for e.g. COMMA -> , Reads from SameTokens.py
def tokenReverse(token):
	if token in tokenReverseDict.keys():
		return tokenReverseDict[token]
	elif token in ["", "()", "):", "():"]: # special case
		return token
	else:
		log("lexerSyntaxHint\ttokenReverse\tCOULD NOT REVERSE " + str(token), filename="bug")
		return token

# places the token replacement logically before the token "token"
def beforeReplacement(replacement, token, filename, realText=None):
	with open(filename, "r") as f:
		content = f.read()
	lines = content.split("\n")
	tokenType = token[0]
	tokenName = token[1]
	tokenRow = token[2]
	tokenCol = find_column(content if realText == None else realText, token)
	index = token[3]

	# Special cases
	if tokenType in ["ENDMARKER", "DEDNET"] or index == len(content): # col is at the end
		tokenCol = len(lines[tokenRow-1])
	elif lines[tokenRow-1][:tokenCol-2].strip() == "":
		# If whitespace immediately precedes the text, we might need to put the token before the \n
		tokenRow -= 1
		tokenCol = len(lines[tokenRow-1])
		index = len("\n".join(lines[:tokenRow])) # end of the line
	else:
		if replacement in [" ", "\n", "\\n"]:
			pass
		else:
			if index + 1 < len(content) and content[index+1] not in [" ", "\t", "\n"]: # put a space after it
				replacement += " "
			if content[index-1] not in [" ", "\t", "\n"]: # put a space before it
				replacement = " " + replacement
	content = content[:index] + replacement + content[index:]
	with open(filename, "w") as f:
		f.write(content)
	return (index, tokenRow, tokenCol, "", replacement)

# replaces a token with the replacement token and stores in the file
def doReplacement(replacement, token, filename, realText=None):
	with open(filename, "r") as f:
		content = f.read()
	lines = content.split("\n")
	tokenType = token[0]
	tokenName = token[1]
	tokenRow = token[2]
	tokenCol = find_column(content if realText == None else realText, token)
	index = token[3]

	# Some special cases
	# Sometimes the code gets confused about the end
	if tokenType == "ENDMARKER" or index == len(content):
		replacedText = ""
	elif tokenType == "DEDENT": # To replace a dedent, we must add a space!
		replacement = replacement + " "
		replacedText = ""
	elif tokenType == "NEWLINE":
		if index >= len(content):
			log("lexerSyntaxHint\tdoReplacement\tBad index: " + \
					  repr(token) + "\n" + repr(content) + "\n" + repr(realText), filename="bug")
		replacedText = content[index] # just the newline
	else:
		if index + len(tokenName) > len(content):
			log("lexerSyntaxHint\tdoReplacement\tBad index: " + \
					  repr(token) + "\n" + repr(content) + "\n" + repr(realText), filename="bug")
		# Don't mess with blanks
		if replacement in [" ", "\n", "\\n"]:
			pass
		elif replacement == "":
			if content[index-1] in [" ", "\t", "\n"] or \
				(index + 1 < len(content) and content[index+1] in [" ", "\t", "\n"]):
				pass
			else:
				replacement = " "
		else:
			if index + len(tokenName) < len(content) and \
				content[index+len(tokenName)] not in [" ", "\t", "\n"]:
				replacement += " "
			if content[index-1] not in [" ", "\t", "\n"]:
				replacement = " " + replacement
		replacedText = content[index:index + len(tokenName)]
	content = content[:index] + replacement + content[index + len(replacedText):]
	with open(filename, "w") as f:
		f.write(content)
	return (index, tokenRow, tokenCol, replacedText, replacement)

def applyWhitespaceHints(hints, code):
	# Should maybe switch to using the apply method in getSyntaxHint
	offset = 0
	for hint in hints:
		col = hint.totalCol + offset
		if hint.editType in ["indent", "+"]:
			code = code[:col] + hint.text + code[col:]
			offset -= len(hint.text)
		elif hint.editType in ["deindent", "-"]:
			code = code[:col] + code[col + len(hint.text):]
			offset += len(hint.text)
		else:
			code = code[:col] + hint.newText + code[col + len(hint.text):]
			offset += len(hint.text) - len(hint.newText)
	return code

def find_column(input, token):
    last_cr = input.rfind('\n', 0, token[3])
    if last_cr < 0:
        last_cr = 0
    column = (token[3] - last_cr) + 1
    return column

# Checks to see if different paren types are used
def neededParens(filename):
	with open(filename, "r") as f:
		content = f.read()

	parenPairs = [ ("(", "RPAREN"), ("[", "RSQB"), ("{", "RBRACE") ]
	parensRequired = []
	for pair in parenPairs:
		if content.count(pair[0]) > 0:
			parensRequired.append(pair[1])
	return parensRequired

# removes or adds paranthesis as required
def addParens(replacements, filename):
	l = neededParens(filename)
	for item in l:
		if item not in replacements:
			replacements.append(item)
	replacements.append("()")

# assigns priority to some tokens - is this needed now that we sort replacements before picking one?
def tokenPriority(token, replacements):
	if token[0] == "EQUAL":
		if "EQEQUAL" in replacements:			# increases the priority of == if =
			i = replacements.index("EQEQUAL")
			replacements.pop(i)
			replacements.insert(0, "EQEQUAL")

def findStates(tokenDump):
	# Find the error states in the dump
	with open(tokenDump, "r") as f:
		txt = f.read()

	l = txt.split("\n\n")
	for i in range(len(l)):
		if "ERROR" in l[i]:
			tokenIndex = l[i].find("LexToken(") + len("LexToken(")
			tokenEndIndex = l[i].find(")\n", tokenIndex)
			errorToken = l[i][tokenIndex:tokenEndIndex]
			states = []
			j = i
			while errorToken in l[j]:
				lines = l[j].split("\n")
				states.append(int(lines[0].split(":")[1].strip()))
				j -= 1
			return states
	return []

# reduces the number of replacements
def refineReplacements(token, tokenDump, filename):
	states = findStates(tokenDump)
	replacements = set()
	for state in states:
		replacements |= stateList[state]

	addedTokens = set()
	for temp in replacements:
		for sameToken in sameTokens:
			if temp in sameTokens[sameToken]:
				addedTokens |= set(sameTokens[sameToken])
	replacements = list(replacements | addedTokens)

	if "PASS" not in replacements:
		replacements.append("PASS") # to deal with cases where we just need filler

	tokenPriority(token, replacements)
	addParens(replacements, filename)
	if "COLON" in replacements:
		replacements += ["():", "):"] # common combos
	return replacements

def runParser(filename, dumpFile, realText=None):
	# Run the parser to determine where the errors are
	hints = []
	try:
		with open(filename, "r") as f:
			currentText = f.read()
		txt = realText if realText != None else currentText
		lines = txt.split("\n")
		(output, dump) = parser.runLexer(currentText, dumpFile)
		if output.strip() == "":
			return [], [] # no errors!
	except Exception as e:
		log("lexerSyntaxHint\trunParser\tBroken parse: " + str(e), filename="bug")
		return "ERROR", []

	outputLines = output.strip().split("\n")
	i = 0
	while i < len(outputLines):
		if outputLines[i] == "":
			outputLines.pop(i)
			continue
		outputLines[i] = outputLines[i].replace("\\t", "\t").replace("~newline", "\n").strip().split(",")
		for j in range(len(outputLines[i])):
			outputLines[i][j] = outputLines[i][j].replace("~comma", ",")
		if len(outputLines[i]) < 4:
			log("lexerSyntaxHint\trunParser\tUneven error?: " + repr(outputLines[i]), filename="bug")
		else: # make the row and index ints
			outputLines[i][2] = int(outputLines[i][2])
			outputLines[i][3] = int(outputLines[i][3])
		i += 1

	i = 0
	while i < len(outputLines) and outputLines[i][0] in ["FIXWHITESPACE", "ILLEGAL", "INDENT", "DEINDENT"]:
		output = outputLines[i]
		rows = output[2]
		totalCol = len("\n".join(lines[:rows-1]) + ("\n" if rows > 1 else ""))
		if output[0] == "DEINDENT":
			spaceType = output[1][1:-1] # get rid of quotes
			if totalCol >= len(txt):
				log("lexerSyntaxHint\trunParser\tBad index: " + \
						  str(totalCol) + "\n" + repr(txt), filename="bug")
			# Find the col
			col = 0
			while totalCol < len(txt) and txt[totalCol] != spaceType[0]:
				col += 1
				totalCol += 1
			if totalCol == len(txt):
				log("lexerSyntaxHint\trunParser\tBad spacetype: " + \
						  repr(spaceType) + "," + str(totalCol) + "\n" + repr(txt), filename="bug")
			hints.append(SyntaxEdit(rows, col, totalCol, "deindent", spaceType))
		elif output[0] == "INDENT":
			spaceType = output[1][1:-1] # get rid of quotes
			if totalCol >= len(txt):
				log("lexerSyntaxHint\trunParser\tBad index: " + \
						  str(totalCol) + "\n" + repr(txt), filename="bug")
			hints.append(SyntaxEdit(rows, 0, totalCol, "indent", spaceType))
		elif output[0] == "FIXWHITESPACE":
			l = output[1][1:-1].split(";") # get rid of quotes. We know that the old and new txt will be separated by ;
			oldTxt, newTxt = l[0], l[1]
			if totalCol >= len(txt):
				log("lexerSyntaxHint\trunParser\tBad index: " + \
						  str(totalCol) + "\n" + repr(txt), filename="bug")
			# Find the col
			col = 0
			while totalCol < len(txt) and txt[totalCol:totalCol+len(oldTxt)] != oldTxt:
				totalCol += 1
				col += 1
			if totalCol == len(txt):
				log("lexerSyntaxHint\trunParser\tBad spacetype: " + \
						  repr(oldTxt) + "," + repr(newTxt) + "," + str(totalCol) + "\n" + repr(txt), filename="bug")
			hints.append(SyntaxEdit(rows, col, totalCol, "+-", oldTxt, newTxt))
		else: # elif output[0] == "ILLEGAL":
			colLength = output[3]
			if rows - 1 >= len(lines):
				log("lexerSyntaxHint\trunParser\tBad index: " + \
						  str(rows) + "\n" + repr(txt), filename="bug")
			# Find the location if it isn't accurate
			if colLength >= len(lines[rows-1]) or lines[rows-1][colLength] != output[1]:
				colLength = lines[rows-1].find(output[1])
				if colLength == -1:
					log("lexerSyntaxHint\trunParser\tCouldn't find illegal token " + \
							  repr(output[1]), filename="bug")
			hints.append(SyntaxEdit(rows, colLength, totalCol + colLength, "-", output[1]))
		i += 1

	# We've turned the whitespace edits into hints, so remove them as errors
	outputLines = outputLines[i:]
	if len(outputLines) > 0: # small fixes
		if outputLines[0][0] == "ENDMARKER":
			outputLines[0][1] = ""
			outputLines[0][3] = len("\n".join(lines[:outputLines[0][2]+1])) # end of the file
		elif outputLines[0][0] == "DEDENT": # do not confuse with deindent!
			outputLines[0][1] = ""
			if outputLines[0][3] < 0:
				outputLines[0][3] = len("\n".join(lines[:outputLines[0][2]])) + 1
			else:
				outputLines[0][3] = len(txt) # this is a signal for the end of the file
		elif outputLines[0][3] <= 0:
			log("lexerSyntaxHint\trunParser\tBAD OUTPUT: " + repr(outputLines[0]), filename="bug")
	return outputLines, hints

def removeComments(filename):
	# Remove the comments from the file, but keep track of their positions
	with open(filename, "r") as f:
		content = f.read()
	lines = content.split("\n")
	commentLines = [0] * len(lines)
	for i in range(len(lines)):
		inString = False
		for j in range(len(lines[i])):
			if lines[i][j] in ['"', "'"]:
				inString = not inString
			if lines[i][j] == "#" and not inString:
				commentLines[i] = len(lines[i][j:])
				lines[i] = lines[i][:j]
				break
	with open(filename, "w") as f:
		f.write("\n".join(lines))
	return commentLines

# Makes a transition from else-if to elif
def removeElseIf(filename):
	hints = []
	content = ""
	with open(filename, "r") as f:
		content = f.read()
	content = content.split("\n")
	newContent = []
	for i in range(len(content)):
		newLine = content[i]
		if "else if" in newLine:
			newLine = newLine.replace("else if", "elif")
			columnNo = newLine.find("elif")
			totalCol = len("\n".join(content[:i]) + ("\n" if i > 0 else "")) + columnNo
			hints.append(SyntaxEdit(i + 1, columnNo, totalCol, "+-", "else if", "elif"))
		newContent.append(newLine)
	with open(filename, "w") as f:
		f.write("\n".join(newContent))
	return hints

def formatHint(row, col, index, oldText, newText):
	# Add deindent/indent edit types
	newHint = SyntaxEdit(row, col, index, "+-", oldText, newText)
	if newText == "":
		newHint.editType = "deindent" if oldText in [" ", "\t"] else "-"
	elif oldText == "":
		newHint.editType = "indent" if newText in [" ", "\t"] else "+"
		newHint.text = newText
		newHint.newText = ""
	return newHint

def checkIfIsBroken(oldToken, errors, oldText, newText, replacementType, txt):
	# Check to see if the given hint is 'broken', ie, it won't actually help
	# Return whether it's broken AND, if not, the location of the new error
	if errors == "ERROR": # broken code
		return True, -1
	elif len(errors) == 0: # this fixes everything!
		return False, len(txt)
	else:
		newToken = errors[0]
		# Check if it doesn't move the error at all
		if oldToken[3] > 0 and newToken[3] > 0 and abs(oldToken[3] - newToken[3]) <= (2 + len(newText)):
			# Special case for missing end parentheses- these won't move the error, but they're still needed
			if (oldToken[0] == newToken[0] == "DEDENT") and \
				((replacementType == "RPAREN" and txt.count("(") > txt.count(")")) or \
				 (replacementType == "RSQB" and txt.count("[") > txt.count("]")) or \
				 (replacementType == "RBRACE" and txt.count("{") > txt.count("}"))):
				return False, newToken[3]
			return True, -1
		# ENDMARKER/DEDENT/INDENT have weird locations and need to be checked specially
		elif oldToken[0] == newToken[0] and oldToken[2] == newToken[2] and \
			 oldToken[0] in ["ENDMARKER", "DEDENT"]:
			return True, -1
		# Also, if a newline is added and moves the error to the beginning of the next line, that isn't helpful
		elif oldToken[0] == newToken[0] and oldToken[2] == newToken[2] + 1 and \
			 oldText == "" and newText == "\n":
			return True, -1
		# Removing newlines also doesn't generally help
		elif oldToken[2] == newToken[2] and oldText == "\n" and newText == "":
			return True, -1
		# Here we're just messing with earlier indentation
		elif oldToken[2] == newToken[2] and newToken[0] in ["DEDENT", "INDENT"] and newToken[3] == 0:
			return True, -1
		# Here we're just creating an error at the new token
		elif oldToken[2] == newToken[2] and oldToken[0] in ["ENDMARKER", "DEDENT", "INDENT"] and \
			 replacementType == newToken[0]:
			return True, -1
		# Otherwise, all's good!
		else:
			return False, newToken[3]

def checkHint(outputFile, dumpFile):
	# try running the hint to see if it fixes things. keep running until we've moved past whitespace hints.
	allHints = []
	needsChecking = True
	with open(outputFile, "r") as f:
		currentCode = f.read()
	while True:
		errors, hints = runParser(outputFile, dumpFile)
		currentCode = applyWhitespaceHints(hints, currentCode)
		allHints += hints
		with open(outputFile, "w") as f:
			f.write(currentCode)
		if len(hints) == 0:
			break
	return (errors, hints, currentCode)

def processHints(f, hint, replacement, token, outputFile, dumpFile, editedText, commentLines):
	# Try applying the replacement to see if it fixes the code
	replacementText = tokenReverse(replacement)
	(index, rowNo, columnNo, replacedText, addedText) = f(replacementText, token, outputFile, realText=editedText)
	(errors, hints, currentCode) = checkHint(outputFile, dumpFile)
	isBroken, i = checkIfIsBroken(token, errors, replacedText, addedText, replacement, editedText)
	i += len(replacedText) - len(addedText) + sum([h.textDiff() for h in hints])
	if not isBroken: # this is a feasible hint!
		newHint = formatHint(rowNo, columnNo, index, replacedText, addedText)
		if len(hints) > 0 or len(errors) != 0: # doesn't fix everything OR requires multiple edits
			hint.append(([newHint] + hints, i, errors[0] if len(errors) > 0 else None, currentCode))
		else: # this hint is perfect! use it at once!
			clearFiles(outputFile, dumpFile)
			return fixHint(newHint, commentLines), True
	return hint, False

def clearFiles(outputFile, dumpFile):
	# Remove the files now that we're done with them
	if os.path.exists(outputFile):
		os.remove(outputFile)
	if os.path.exists(dumpFile):
		os.remove(dumpFile)

def fixHint(hint, commentLines):
	hint.totalCol += sum(commentLines[:hint.line-1]) # get location in original text
	return [hint]

def getLexerSyntaxHint(filename):
	rand = str(random.randint(0,100000))
	outputFile = TEST_PATH + "tmp/output_" + rand + ".py"	# make these unique across submissions
	dumpFile = TEST_PATH + "tmp/dump2_" + rand

	# Keep track of the original text
	with open(filename, "r") as i, open(outputFile, "w") as o:
		originalText = i.read()
		o.write(originalText)

	# Remove comments, but keep track of where they are
	commentLines = removeComments(outputFile)
	with open(outputFile, "r") as i:
		editedText = i.read()

	# Fix 'else if' error (why is this a special case?)
	hints = removeElseIf(outputFile)
	if len(hints) > 0:
		clearFiles(outputFile, dumpFile)
		return fixHint(hints[0], commentLines)

	# Get the location of the current error
	errors, hints = runParser(outputFile, dumpFile, realText=editedText)

	if len(hints) > 0: # Immediately return whitespace hints
		clearFiles(outputFile, dumpFile)
		return fixHint(hints[0], commentLines)
	elif errors == "ERROR": # something broke- get us out of here!
		clearFiles(outputFile, dumpFile)
		return None
	elif errors == []: # Our parser didn't find the error
		log("lexerSyntaxHint\tgetSyntaxLexerHint\tError not located " + \
				  "\n" + originalText, filename="bug") 
		clearFiles(outputFile, dumpFile)
		return None
	else:
		token = errors[0]

	# These are tokens we haven't added to the parser yet
	if token[0] in ["WS", "WITH", "EXEC", "DEL", "BINARYNUMBER", 
					"RAWSTRING", "INUMBER", "LAMBDA", "RAISE", "HEXADECIMALNUMBER", 
					"OCTALNUMBER", "STRINGUNCLOSED", "YIELD", "AT", "UNICODESTRING"]:
		log("lexerSyntaxHint\tgetLexerSyntaxHint\tUnlexed token: " + token[0], filename="bug")

	# Find the set of possible replacements
	replacements = refineReplacements(token, dumpFile, outputFile)
	foundHints = []

	# 1. Empty Replacement
	foundHints, returnNow = processHints(doReplacement, foundHints, "", token, 
										 outputFile, dumpFile, editedText, commentLines)
	if returnNow:
		return foundHints

	for replacement in replacements:
		# 2. Insert Before
		with open(outputFile, "w") as o:
			o.write(editedText)
		foundHints, returnNow = processHints(beforeReplacement, foundHints, replacement, token, 
											 outputFile, dumpFile, editedText, commentLines)
		if returnNow:
			return foundHints

		# 3. Do-replacement
		with open(outputFile, "w") as o:
			o.write(editedText)
		foundHints, returnNow = processHints(doReplacement, foundHints, replacement, token, 
											 outputFile, dumpFile, editedText, commentLines)
		if returnNow:
			return foundHints

	if len(foundHints) > 0: # If we found a hint
		# Sort based on how much further the error has moved
		bestHint = sorted(foundHints, cmp=lambda x, y : y[1] - x[1])
		clearFiles(outputFile, dumpFile)
		# Get the first hint of the best hint combination
		return fixHint(bestHint[0][0][0], commentLines)
	else:
		log("lexerSyntaxHint\tgetLexerSyntaxHint\tCould not find a fix for error at token " + \
				  repr(token) + "\n" + originalText, filename="bug")
		clearFiles(outputFile, dumpFile)
		return None

if __name__=="__main__":
	print(getLexerSyntaxHint(sys.argv[1],sys.argv[2]))