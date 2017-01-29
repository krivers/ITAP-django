# improve lexer to handle number/floating type, this will lead to improvement in the parser too.. better leave it for later
import tokenize
from .lex import TOKEN, LexToken, lex
from ..tools import log

NO_INDENT = 0
MAY_INDENT = 1
MUST_INDENT = 2

keywordlist = [
		'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 
		'del', 'elif', 'else', 'except', 'exec', 'finally', 'for', 
		'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'not', 
		'or', 'pass', 'print', 'raise', 'return', 'try', 'while', 
		'with', 'yield'
		]

tokens = []
RESERVED = {}
for keyword in keywordlist:
	name = keyword.upper()
	RESERVED[keyword] = name
	tokens.append(name)

tokens = tuple(tokens) + (
		'EQEQUAL','NOTEQUAL','LESSEQUAL','LEFTSHIFT','GREATEREQUAL',
		'RIGHTSHIFT','PLUSEQUAL','MINEQUAL','STAREQUAL','SLASHEQUAL','PERCENTEQUAL',
		'STARSTAR','SLASHSLASH','STARSTAREQUAL','SLASHSLASHEQUAL',
		'COLON','COMMA','SEMI','PLUS','MINUS','STAR','SLASH','VBAR','AMPER','LESS',
		'GREATER','EQUAL','DOT','PERCENT','BACKQUOTE','CIRCUMFLEX','TILDE',	'AT',
	    'LPAREN', 
	    'RPAREN',
	    'LBRACE', 'RBRACE',
	    'LSQB', 'RSQB',
		'NEWLINE',
		'INUMBER','FNUMBER',
		'BINARYNUMBER','OCTALNUMBER','HEXADECIMALNUMBER', 
		'NUMBER',
		'INDENT', 'DEDENT',
		'TRIPLESTRING', 'STRING', 
		'RAWSTRING','UNICODESTRING',
		'NAME','WS',
		'ENDMARKER', 'STRINGUNCLOSED'
	)

# Regular expression rules for simple tokens
t_EQEQUAL = r'=='
t_NOTEQUAL =  r'!='
t_LESSEQUAL = r'<='
t_LEFTSHIFT = r'<<'
t_GREATEREQUAL = r'>='
t_RIGHTSHIFT  = r'>>'
t_PLUSEQUAL = r'\+='
t_MINEQUAL = r'-='
t_STAREQUAL = r'\*='
t_SLASHEQUAL = r'/='
t_PERCENTEQUAL = r'%='
t_STARSTAR = r'\*\*'
t_SLASHSLASH = r'//'
t_STARSTAREQUAL = r'\*\*='
t_SLASHSLASHEQUAL = r'//='

t_COLON = r':'
t_COMMA = r','
t_SEMI  = r';'
t_PLUS  = r'\+'
t_MINUS = r'-'
t_STAR  = r'\*'
t_SLASH = r'/'
t_VBAR  = r'\|'
t_AMPER = r'&'
t_LESS  = r'<'
t_GREATER = r'>'
t_EQUAL = r'='
t_DOT  = r'\.'
t_PERCENT = r'%'
t_BACKQUOTE  = r'`'
t_CIRCUMFLEX = r'\^'
t_TILDE = r'~'
t_AT = r'@'

def newToken(newType, lineno, lexpos):
	tok = LexToken()
	tok.type = newType
	tok.value = None
	tok.lineno = lineno
	tok.lexpos = lexpos
	return tok

def t_LPAREN(t):
	r"\("
	t.lexer.parenthesisCount+=1
	return t

def t_RPAREN(t):
	r"\)"
	t.lexer.parenthesisCount-=1
	return t

def t_LBRACE(t):
	r"\{"
	t.lexer.parenthesisCount+=1
	return t

def t_RBRACE(t):
	r"\}"
	t.lexer.parenthesisCount-=1
	return t

def t_LSQB(t):
	r"\["
	t.lexer.parenthesisCount+=1
	return t

def t_RSQB(t):
	r"\]"
	t.lexer.parenthesisCount-=1
	return t

#ignore comments in source code
def t_comment(t):
	r"[ ]*\043[^\n]*"
	pass

@TOKEN(tokenize.Imagnumber)
def t_INUMBER(t):
    return t

@TOKEN(tokenize.Floatnumber)
def t_FNUMBER(t):
    return t

# FP number above integers
def t_BINARYNUMBER(t):
	r'0[bB]([0-1]+)'
	return t

def t_OCTALNUMBER(t):
	r'0[oO]([0-7]+)'
	return t

def t_HEXADECIMALNUMBER(t):
	r'0[xX]([0-9a-fA-F]+)'
	return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)    
    return t

def t_TRIPLESTRING(t):
	r'"{3}([\s\S]*?"{3}) | \'{3}([\s\S]*?\'{3})'
	return t

def t_RAWSTRING(t):
	r'[rR](\"(\\.|[^\"\n]|(\\\n))*\") | [rR](\'(\\.|[^\'\n]|(\\\n))*\')'
	return t

def t_UNICODESTRING(t):
	r'[uU](\"(\\.|[^\"\n]|(\\\n))*\") | [uU](\'(\\.|[^\'\n]|(\\\n))*\')'
	return t

def t_STRING(t):
	r'(\"(\\.|[^\"\n]|(\\\n))*\") | (\'(\\.|[^\'\n]|(\\\n))*\')'
	return t

def t_STRINGUNCLOSED(t):
	r'\"[^\"\n]*'	# removed $ from the end check if required
	log("lexer\tt_STRINGUNCLOSED\t" + repr(t), filename="bug")
	print("UNCLOSEDSTRING" + "," + str(t.value) + "," + str(t.lineno) + "," + str(t.lexpos))
	t.lexer.skip(1)

def t_continueLine(t):
	r'\\(\n)+'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.type = "NEWLINE"
    if (t.lexer.parenthesisCount == 0):
    	return t

def t_NAME(t):
	r"[a-zA-Z_][a-zA-Z0-9_]*"
	t.type = RESERVED.get(t.value, "NAME")
	return t

# Error handling rule
def find_column(i, lineno):
    last_cr = i.rfind('\n',0,lineno)
    if last_cr < 0:
        last_cr = 0
    column = (lineno - last_cr) + 1
    return column

def t_error(t):
    print("ILLEGAL" + "," + str(t.value[0]) + "," + str(t.lineno) + "," + str(t.lexpos))
    t.lexer.skip(1)

# REFERENCE: https://docs.python.org/2/reference/lexical_analysis.html
# WHITESPACE
def t_WS(t):
	r" [ \t\f]+ "
	value = t.value
	value = value.rsplit("\f", 1)[-1]
	pos = 0
	# Getting rid of this so we can give specific whitespace hints for spaces vs. tabs
	#while True:
	#	pos = value.find("\t")
	#	if pos == -1:
	#		break
	#	n = 8 - (pos % 8)								# Convert each \t to 8 spaces (Python Documentation)
	#	value = value[:pos] + " "*n + value[pos+1:]
	t.value = value
	if t.lexer.atLineStart and t.lexer.parenthesisCount == 0:
		return t

def INDENT(lineno, lexpos):
	return newToken("INDENT", lineno, lexpos)
def DEDENT(lineno, lexpos):
	return newToken("DEDENT", lineno, lexpos)

# From Python 2 documentation:
# The indentation levels of consecutive lines are used to generate INDENT and DEINDENT tokens, 
# using a stack, as follows.
# Before the first line of the file is read, a single zero is pushed on the stack; 
# this will never be popped off again. The numbers pushed on the stack will always 
# be strictly increasing from bottom to top. At the beginning of each logical line, 
# the line's indentation level is compared to the top of the stack. If it is equal, 
# nothing happens. If it is larger, it is pushed on the stack, and one INDENT token 
# is generated. If it is smaller, it must be one of the numbers occurring on the stack; 
# all numbers on the stack that are larger are popped off, and for each number popped 
# off a DEINDENT token is generated. At the end of the file, a DEINDENT token is generated 
# for each number remaining on the stack that is larger than zero.

def identifyIndenations(lexer, token_stream):
	lexer.atLineStart = atLineStart = True
	indent = NO_INDENT
	saw_colon = False
	for token in token_stream:
		token.atLineStart = atLineStart
		if token.type == "COLON":
			atLineStart = False
			indent = MAY_INDENT
			token.must_indent = False
		elif token.type == "NEWLINE":
			atLineStart = True
			if indent == MAY_INDENT:
				indent = MUST_INDENT  			# MUST INDENT
			token.must_indent = False
		elif token.type == "WS":
			if not token.atLineStart:
				log("lexer\tidentifyIndentations\tToken not at line start: " + repr(token), filename="bug")
				assert token.atLineStart == True
			atLineStart = True
			token.must_indent = False
		else:
			token.must_indent = (indent == MUST_INDENT)
			atLineStart = False
			indent = NO_INDENT

		yield token
		lexer.atLineStart = atLineStart

def assignIndentations(token_stream):
	levels = [[0, 0, None]]
	token = None
	spacedepth = tabdepth = 0
	lastSeenWhitespace = False
	secondClassConstructs = ["FOR", "WHILE", "TRY", "EXCEPT"]

	for token in token_stream:
		if token.type == "WS":
			if tabdepth != 0:
				log("lexer\tassignIndentations\tTab Depth not 0: " + repr(token.__dict__), filename="bug")
			if spacedepth != 0:
				log("lexer\tassignIndentations\tSpace Depth not 0: " + repr(token.__dict__), filename="bug")
			assert tabdepth == 0 and spacedepth == 0

			#spaces = token.value.replace("\t", "")
			#tabs = token.value.replace(" ", "")
			spaces = token.value.split("\t")
			tabs = token.value.split(" ")
			if len(spaces) > 1 and len(tabs) > 1: # at least one of each
				if levels[-1][0] > 0 or levels[-1][1] == 0: # use spaces if there are already spaces or neither have been established
					for j in range(len(tabs)):
						if tabs[j] != "":
							oldTxt = tabs[j]
							break
					newTxt = "        " * len(oldTxt)
				else: # use tabs if there are already tabs
					for j in range(len(spaces)):
						if spaces[j] != "":
							oldTxt = spaces[j]
							break
					newTxt = "\t" * ((len(oldTxt) + 7) // 8) # turn 8 spaces into a tab, but also turn leftover space into a tab
				print("FIXWHITESPACE" + "," + '"' + oldTxt + ";" + newTxt + '"' + "," + str(token.lineno) + "," + str(token.lexpos))
				break
			tabdepth = sum([len(x) for x in tabs])
			spacedepth = sum([len(x) for x in spaces])
			lastSeenWhitespace = True
		elif token.type == "NEWLINE":
			spacedepth = tabdepth = 0
			if not (lastSeenWhitespace or token.atLineStart):
				yield token
		else:
			lastSeenWhitespace = False
			if token.must_indent:
				i = len(levels)-1
				lastLevel = levels[i]
				if lastLevel[0] == lastLevel[1] == spacedepth == tabdepth == 0:
					txt = "    "
					print("INDENT" + "," + repr(txt) + "," + str(token.lineno) + "," + str(token.lexpos))
					break
				elif (lastLevel[0] != 0 and spacedepth <= lastLevel[0]):
					if tabdepth > 0:
						tabtxt = "\t" * tabdepth
						spacetxt = " " * (lastLevel[0] - spacedepth + 1)
						print("FIXWHITESPACE" + "," + '"' + tabtxt + ";" + spacetxt + '"' + "," + str(token.lineno) + "," + str(token.lexpos))
					else:
						txt = " " * (lastLevel[0] - spacedepth + 1)
						print("INDENT" + "," + repr(txt) + "," + str(token.lineno) + "," + str(token.lexpos))
					break
				elif (lastLevel[1] != 0 and tabdepth <= lastLevel[1]):
					if spacedepth > 0:
						spacetxt = " " * spacedepth
						tabtxt = "\t" * (lastLevel[1] - tabdepth + 1)
						print("FIXWHITESPACE" + "," + '"' + spacetxt + ";" + tabtxt + '"' + "," + str(token.lineno) + "," + str(token.lexpos))
					else:
						txt = "\t" * (lastLevel[1] - tabdepth + 1)
						print("INDENT" + "," + repr(txt) + "," + str(token.lineno) + "," + str(token.lexpos))
					break
				else:
					levels.append([spacedepth, tabdepth, token.type])
					yield INDENT(token.lineno, 0)
			elif token.atLineStart:
				l = len(levels)
				i = l - 1
				if token.type in ["ELSE"]:
					while i > 0 and levels[i][2] not in (["IF"] + secondClassConstructs):
						i -= 1
					if i != l - 1:
						levels[i][2] = "ELSE"
						for j in range(i+1, l):
							yield DEDENT(token.lineno, -100)
							levels.pop()
				elif token.type in ["ELIF"]:
					while i > 0 and levels[i][2] != "IF":
						i -= 1
					if i != l - 1:
						for j in range(i+1, l):
							yield DEDENT(token.lineno, -100)
							levels.pop()
				lastLevel = levels[i]
				if spacedepth == lastLevel[0] and tabdepth == lastLevel[1]:
					if token.type == "IF": # keep track of most recently seen construct
						levels[-1][2] = "IF"
					elif token.type in secondClassConstructs and \
						 levels[-1][2] not in (["IF"] + secondClassConstructs):
						levels[-1][2] = token.type
				elif spacedepth > lastLevel[0]:
					if tabdepth < lastLevel[1]:
						spacetxt = " " * (spacedepth - lastLevel[0])
						tabtxt = "\t" * (lastLevel[1] - tabdepth)
						print("FIXWHITESPACE" + "," + '"' + spacetxt + ";" + tabtxt + '"' + "," + str(token.lineno) + "," + str(token.lexpos))
					else:
						txt = " " * (spacedepth - lastLevel[0])
						print("DEINDENT" + "," + repr(txt) + "," + str(token.lineno) + "," + str(token.lexpos))
					break
				elif tabdepth > lastLevel[1]:
					if spacedepth < lastLevel[0]:
						tabtxt = "\t" * (tabdepth - lastLevel[1])
						spacetxt = " " * (lastLevel[0] - spacedepth)
						print("FIXWHITESPACE" + "," + '"' + tabtxt + ";" + spacetxt + '"' + "," + str(token.lineno) + "," + str(token.lexpos))
					else:
						txt = "\t" * (tabdepth - lastLevel[1])
						print("DEINDENT" + "," + repr(txt) + "," + str(token.lineno) + "," + str(token.lexpos))
					break
				else:
					for i in range(len(levels)-1, -1, -1):
						if levels[i][0] == spacedepth and levels[i][1] == tabdepth:
							if token.type not in ["ELSE", "ELIF"]:
								break
							elif (token.type == "ELSE" and levels[i][2] in (["IF"] + secondClassConstructs)):
								break
							elif (token.type == "ELIF" and levels[i][2] == "IF"):
								break
					else:
						# No matching depth found. Try indenting.
						txt = "\t" if spacedepth == lastLevel[0] else " "
						print("INDENT" + "," + repr(txt) + "," + str(token.lineno) + "," + str(token.lexpos))
						break

					if token.type == "IF": # keep track of most recently seen construct
						levels[i][2] = "IF"
					elif token.type in secondClassConstructs and \
						 levels[i][2] not in (["IF"] + secondClassConstructs):
						levels[i][2] = token.type
					l = len(levels)
					for z in range(i + 1, l):
						yield DEDENT(token.lineno, -100)
						levels.pop()
			yield token
	else:
		for z in range(1, len(levels)): # won't run if len(levels) = 1
			yield DEDENT(token.lineno, 0)

# This filter was in main() of previous lexer
def filter(lexer, addEndMarker = True):
	token_stream = iter(lexer.token, None)
	token_stream = identifyIndenations(lexer, token_stream)
	token_stream = assignIndentations(token_stream)
	tok = None
	for tok in token_stream:
		yield tok
	if addEndMarker:
		lineno = tok.lineno if hasattr(tok, "lineno") else 1
		yield newToken("ENDMARKER", lineno, -100)

# To merge ply's lexer with indent feature
# Built from previous main()
class G1Lexer(object): 
	def __init__(self):
		self.lexer = lex()
		self.token_stream = None

	def input(self, data, addEndMarker=True):
		self.lexer.parenthesisCount = 0
		data += "\n"
		self.lexer.input(data)
		self.token_stream = filter(self.lexer, addEndMarker)

	def token(self):
		try:
			return self.token_stream.next()
		except StopIteration:
			return None