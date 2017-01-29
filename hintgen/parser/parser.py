#!/usr/bin/python
import io, sys
from .yacc import yacc
from .lexer import tokens, G1Lexer # our lexer

# from tester import hintList
# file_input: (NEWLINE | stmt)* ENDMARKER
def p_file_input(p):
	"""file_input :	single_stmt ENDMARKER
	"""
# Our temporary symbol
def p_single_stmt(p):
	"""single_stmt	:	single_stmt NEWLINE
					|	single_stmt stmt
					|
	"""

# decorator: '@' dotted_name [ '(' [arglist] ')' ] NEWLINE
def p_decorator(p):
	"""decorator 	: AT module NEWLINE
					| AT module LPAREN RPAREN NEWLINE
					| AT module LPAREN arglist RPAREN NEWLINE
	"""
# decorators: decorator+
def p_decorators(p):
	"""decorators 	: decorator
					| decorator decorators
	"""

# decorated: decorators (classdef | funcdef)
def p_decorated(p):
	"""decorated 	: decorators classdef
					| decorators funcdef
	"""
# funcdef: [decorators] 'def' NAME parameters ':' suite
def p_funcdef(p):
    """funcdef		: DEF NAME parameters COLON suite
    """

# parameters: '(' [varargslist] ')'
def p_parameters(p):
	"""parameters	: LPAREN varargslist RPAREN
	"""

#varargslist: ( | fpdef ['=' test] (',' fpdef ['=' test])* [',']) 

def p_varargslist(p):
    """varargslist 	:
    				| fpdef EQUAL test fpdeflist COMMA
    				| fpdef EQUAL test fpdeflist
    				| fpdef fpdeflist COMMA
    				| fpdef fpdeflist
    """

def p_fpdeflist(p):
	"""fpdeflist 	:
					| fpdeflist COMMA fpdef
					| fpdeflist COMMA fpdef EQUAL test
	"""

# fpdef: NAME | '(' fplist ')'
def p_fpdef(p):
	"""fpdef 	: NAME 
				| LPAREN fplist RPAREN
	"""

# fplist: fpdef (',' fpdef)* [',']
def p_fplist(p):
	"""fplist 	: fpdef fplist1 COMMA
				| fpdef fplist1	
	"""
# our temp symbol
def p_fplist1(p):
	"""fplist1 	:
				| fplist1 COMMA fpdef
	"""

# stmt: simple_stmt | compound_stmt
def p_stmt(p):
	"""stmt 	: simple_stmt
				| compound_stmt
	"""

# simple_stmt: small_stmt (';' small_stmt)* [';'] NEWLINE
def p_simple_stmt(p):
	"""simple_stmt 	: small_stmts NEWLINE
					| small_stmts SEMI NEWLINE
	"""

# our temp symbol
def p_small_stmts(p):
	"""small_stmts 	: small_stmts SEMI small_stmt
					| small_stmt
	"""

# small_stmt: 	expr_stmt 	| print_stmt   	| del_stmt
#			  	pass_stmt 	| flow_stmt 	| assert_stmt|
#    			import_stmt | global_stmt 	| exec_stmt	
 
def p_small_stmt(p):
	"""small_stmt 	: flow_stmt
					| aug_stmt
					| print_stmt
					| pass_stmt
					| import_stmt
					| global_stmt
					| assert_stmt
					| del_stmt
					| exec_stmt
	"""


# expr_stmt: testlist (augassign testlist | ('=' testlist)*)
def p_aug_stmt(p):
	"""aug_stmt 	: testlist augassign testlist
					| assn_stmt
	"""

# our new symbol
def p_assn_stmt(p):
	"""assn_stmt 	: testlist
					| testlist EQUAL assn_stmt
	"""

# augassign: ('+=' | '-=' | '*=' | '/=' | '%=' | '**=' | '//=')
def p_augassign(p):
	"""augassign 	: PLUSEQUAL 
					| MINEQUAL 
					| STAREQUAL 
					| SLASHEQUAL 
					| PERCENTEQUAL 
					| STARSTAREQUAL 
					| SLASHSLASHEQUAL 
	"""



# print_stmt: 'print' [ test (',' test)* [','] ]
def p_print_stmt(p):
	"""print_stmt 	:	PRINT
					|	PRINT testlist
	"""

# pass_stmt: 'pass'
def p_del_stmt(p):
	"""del_stmt : DEL exprlist
	"""
# exec_stmt: 'exec' expr ['in' test [',' test]]
def p_exec_stmt(p):
	"""exec_stmt 	: EXEC expr 
					| EXEC expr IN testlist
	"""
def p_pass_stmt(p):
	"pass_stmt : PASS"

# flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt | yield_stmt
def p_flow_stmt(p):
	"""flow_stmt 	: break_stmt
					| continue_stmt
					| return_stmt
					| raise_stmt
					| yield_stmt
	"""

# break_stmt: 'break'
def p_break_stmt(p):
	"""break_stmt 	: BREAK
	"""

# continue_stmt: 'continue'
def p_continue_stmt(p):
	"""continue_stmt 	: CONTINUE
	"""

# return_stmt: 'return' [testlist]
def p_return_stmt(p):
	"""return_stmt 	:	RETURN 
					|	RETURN testlist
	"""

# raise_stmt: 'raise' [test [',' test [',' test]]]
def p_raise_stmt(p):
	"""raise_stmt 	: RAISE 
					| RAISE test 
					| RAISE test COMMA test 
					| RAISE test COMMA test COMMA test 
	"""
# yield_stmt: yield_expr
def p_yield_stmt(p):
	"""yield_stmt : yield_expr
	"""

# yield_expr: 'yield' [testlist]
def p_yield_expr(p):
	"""yield_expr 	: YIELD 
					| YIELD testlist
	"""
# import_stmt: 'import' NAME ['as' NAME]
# def p_import_stmt(p): 
# 	"""import_stmt 	:	IMPORT NAME
# 					|	IMPORT NAME AS NAME
# 					|	FROM NAME IMPORT NAME
# 	"""

# import_stmt     ::=  "import" module ["as" name] ( "," module ["as" name] )*
#                      | "from" relative_module "import" identifier ["as" name]
#                      ( "," identifier ["as" name] )*
#                      | "from" relative_module "import" "(" identifier ["as" name]
#                      ( "," identifier ["as" name] )* [","] ")"
#                      | "from" module "import" "*"      WILL CAUSE SHIFT/REDUCE CONFLICT
# module          ::=  (identifier ".")* identifier
# relative_module ::=  "."* module | "."+
# name            ::=  identifier

def p_import_stmt(p): 
	"""import_stmt 	:	IMPORT module modulelist
					|	IMPORT module AS NAME modulelist
					|	FROM relative_module IMPORT NAME identlist
					|	FROM relative_module IMPORT NAME AS NAME identlist
					|	FROM relative_module IMPORT LPAREN NAME commaidentlist RPAREN
					|	FROM relative_module IMPORT LPAREN NAME AS NAME identlist RPAREN 		
					|	FROM module IMPORT STAR
	"""	



def p_modulelist(p):
	"""modulelist 	:
					| COMMA module modulelist
					| COMMA module AS NAME modulelist
	"""


def p_identlist(p):
	"""identlist	: 
					| COMMA NAME identlist
					| COMMA NAME AS NAME identlist
	"""

def p_comaaidentlist(p):
	"""commaidentlist 	: 
						| COMMA
						| COMMA NAME commaidentlist
						| COMMA NAME AS NAME commaidentlist
	"""
def p_relative_module(p):
	"""relative_module 	: NAME
						| NAME DOT NAME
						| dotstar module
						| DOT dotplus
	"""

def p_dotplus(p):
	"""dotplus 	: 
				| DOT dotplus
	"""
 
def p_dotstar(p):
	"""dotstar 	: 
				| DOT dotstar 
	"""
def p_module(p):
	"""module 	: NAME 
				| NAME DOT NAME
	"""

# global_stmt: 'global' NAME (',' NAME)*
def p_global_stmt(p):
	"""global_stmt 	: GLOBAL NAME namelist
	"""
# our new symbol
def p_namelist(p):
	"""namelist 	: 
					| COMMA NAME namelist
	"""
# assert_stmt: 'assert' test [',' test]
def p_assert_stmt(p):
	"""assert_stmt 	: ASSERT testlist
	"""

# compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | funcdef | classdef | with_stmt | decorated
def p_compound_stmt(p):
	"""compound_stmt 	: if_stmt
						| for_stmt
						| while_stmt
						| try_stmt
						| funcdef
						| classdef
						| with_stmt
						| decorated
	"""

# if_stmt: 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
def p_if_stmt(p):
	"""if_stmt 	:	IF test COLON suite elif_list
				|	IF test COLON suite elif_list ELSE COLON suite
	"""


# our new symbol
def p_elif_list(p):
	"""elif_list 	:
					| ELIF test COLON suite elif_list
	"""
# error handling rules
# 
# def p_if_stmt_else(p):
# 	"""if_stmt : IF test COLON suite else_if_list 

# 				| IF test COLON suite else_if_list ELSE COLON suite
# 	"""
# 	hintList.append("ELSE-if error")
	

# def p_else_if_list(p):
# 	"""else_if_list : 
# 					| ELSE IF test COLON suite else_if_list

# 	"""
# 	hintList.append("ELSE-if error")

# while_stmt: 'while' test ':' suite ['else' ':' suite]
def p_while_stmt(p):
	"""while_stmt 	:	WHILE test COLON suite 
					|	WHILE test COLON suite ELSE COLON suite
	"""
# for_stmt: 'for' exprlist 'in' testlist ':' suite ['else' ':' suite]
# def p_for_stmt(p): 
# 	"""for_stmt 	:	FOR NAME namelist IN testlist COLON suite
# 					|	FOR NAME namelist IN testlist COLON suite ELSE COLON suite
# 	"""
def p_for_stmt(p): 
	"""for_stmt 	:	FOR targetlist IN testlist COLON suite
					|	FOR targetlist IN testlist COLON suite ELSE COLON suite
	"""
# try_stmt: 'try' ':' suite except_stmt except_list ['else' ':' suite] ['finally' ':' suite] | 'try' ':' 'finally' ':' suite
def p_try_stmt(p):
	"""try_stmt		:	TRY COLON suite except_stmt except_list
					|	TRY COLON suite except_stmt except_list ELSE COLON suite
					|	TRY COLON suite except_stmt except_list ELSE COLON suite FINALLY COLON suite
					|	TRY COLON suite except_stmt except_list FINALLY COLON suite
					|	TRY COLON suite FINALLY COLON suite
	"""


# except_list: except_stmt [NEWLINE except_list]
def p_except_list(p):
	"""except_list	:
					|	except_stmt except_list
	"""

# except_stmt: 'except' [name ['as' name]] ':' suite | 'except' name namelist ':' suite
def p_except_stmt(p):
	"""except_stmt	:	EXCEPT COLON suite
					|	EXCEPT NAME namelist COLON suite
					|	EXCEPT NAME AS NAME COLON suite
	"""

# with_stmt: 'with' with_item (',' with_item)*  ':' suite
def p_with_stmt(p):
	"""with_stmt 	: WITH with_item with_item_list COLON suite
	"""

def p_with_item_list(p):
	"""with_item_list 	: 
						| COMMA with_item with_item_list
	"""
# with_item: test ['as' expr]
def p_with_item(p):
	"""with_item 	: test 
					| test AS target
	"""

# suite: simple_stmt | NEWLINE INDENT stmt+ DEDENT
def p_suite(p):
	"""suite 	: simple_stmt
				| NEWLINE INDENT stmts DEDENT"""

# test: or_test ['if' or_test 'else' test]
def p_test(p):
	"""test 	: or_test
				| or_test IF or_test ELSE test
	"""

# or_test: and_test ('or' and_test)*
def p_or_test(p):
	"""or_test 	: and_test ortestlist
	"""

# our new symbol
def p_ortestlist(p):
	"""ortestlist 	:
					| OR and_test ortestlist
	"""

# and_test: not_test ('and' not_test)*
def p_and_test(p):
	"""and_test 	: not_test andtestlist
	"""

#our new symbol
def p_andtestlist(p):
	"""andtestlist 	:
					| AND not_test andtestlist
	"""

# not_test: 'not' not_test | comparison
def p_not_test(p):
	"""not_test 	: NOT not_test
					| comparison
	"""

# comparison: expr (comp_op expr)*
def p_comparision(p):
	"""comparison 	: expr compexprlist
	"""

# our new symbol
def p_compexprlist(p):
	"""compexprlist 	:
						| comp_op expr compexprlist
	"""

# comp_op: '<'|'>'|'=='|'>='|'<='|'!='|'in'|'not' 'in'|'is'|'is' 'not'
def p_comp_op(p):
	"""comp_op 	: LESS
				| GREATER
				| EQEQUAL
				| GREATEREQUAL
				| LESSEQUAL
				| NOTEQUAL
				| IN
				| NOT IN
				| IS
				| IS NOT
	"""

# expr: xor_expr ('|' xor_expr)*
def p_expr(p):
	"""expr 	: xor_expr xorexprlist
	"""

# our new symbol
def p_xorexprlist(p):
	"""xorexprlist 	:
					|	VBAR xor_expr xorexprlist
	"""

# xor_expr: and_expr ('^' and_expr)*
def p_xor_expr(p):
	"""xor_expr 	: and_expr andexprlist
	"""

# our new symbol
def p_andexprlist(p):
	"""andexprlist 	:
					| CIRCUMFLEX and_expr andexprlist
	"""

# and_expr: shift_expr ('&' shift_expr)*
def p_and_expr(p):
	"""and_expr 	: shift_expr shiftexprlist
	"""

# our new symbol
def p_shiftexprlist(p):
	"""shiftexprlist 	:
						| AMPER shift_expr shiftexprlist
	"""

# shift_expr: arith_expr (('<<'|'>>') arith_expr)*
def p_shift_expr(p):
	"""shift_expr 	: arith_expr arithexprlist
	"""

# our new symbol
def p_arithexprlist(p):
	"""arithexprlist 	:
						| LEFTSHIFT arith_expr arithexprlist
						| RIGHTSHIFT arith_expr arithexprlist
	"""

# arith_expr: term (('+'|'-') term)*
def p_arith_expr(p):
	"""arith_expr 	:	term termlist
	"""

# our new symbol
def p_termlist(p):
	"""termlist 	:
					| PLUS term termlist
					| MINUS term termlist
	"""

# term: factor (('*'|'/'|'%'|'//') factor)*
def p_term(p):
	"""term :	factor factorlist
	"""

# our new symbol
def p_factorlist(p):
	"""factorlist 	:
					| STAR factor factorlist
					| SLASH factor factorlist
					| PERCENT factor factorlist
					| SLASHSLASH factor factorlist
	"""

# factor: ('+'|'-'|'~') factor | power
def p_factor(p):
	"""factor 	: power
				| PLUS factor
				| MINUS factor
				| TILDE factor
	"""

# power: atom trailer* ['**' factor]
def p_power(p):
	"""power 	: atom trailerlist
				| atom trailerlist STARSTAR factor
				| NAME trailerlist
				| NAME trailerlist STARSTAR factor
	"""

# our new symbol
def p_trailerlist(p):
	"""trailerlist 	: 
					| trailer trailerlist
	"""

# atom: ('(' [yield_expr|testlist_comp] ')' |
#        '[' [listmaker] ']' |
#        '{' [dictorsetmaker] '}' |
#        '`' testlist1 '`' |
#        NAME | NUMBER | STRING+)

def p_atom(p):
	"""atom 	: LPAREN RPAREN
				| LPAREN testlist_comp RPAREN
				| LPAREN yield_expr RPAREN
				| LSQB RSQB
				| LSQB listmaker RSQB
				| LBRACE RBRACE
				| LBRACE dictorsetmaker RBRACE
				| BACKQUOTE testlist1 BACKQUOTE
				| NUMBER
				| FNUMBER
				| HEXADECIMALNUMBER
				| OCTALNUMBER
				| BINARYNUMBER
				| stringlist
	"""

# our new symbol
def p_stringlist(p):
	"""stringlist 	: STRING 
					| STRING stringlist
					| TRIPLESTRING
					| TRIPLESTRING stringlist
	"""

# listmaker: test ( list_for | (',' test)* [','] )
def p_listmaker(p):
	"""listmaker 	: testlist
					| test list_for
	"""


# testlist_comp: test (',' test)* [','] 
def p_testlist_comp(p):
	"""testlist_comp 	: testlist
	"""
# list_iter: list_for | list_if	
def p_list_iter(p):
	"""list_iter 	: list_for
					| list_if
	"""

# list_for: 'for' exprlist 'in' testlist_safe [list_iter]
def p_list_for(p):
	"""list_for 	: FOR targetlist IN testlist_safe
					| FOR targetlist IN testlist_safe list_iter
	"""

# list_if: 'if' old_test [list_iter]
def p_list_if(p):
	"""list_if 	: IF old_test
				| IF old_test list_iter
	"""
# testlist_safe: old_test [(',' old_test)+ [',']]
def p_testlist_safe(p):
	"""testlist_safe 	: old_test
						| old_test COMMA commaoldtest
	"""
def p_commaoldtest(p):
	"""commaoldtest 	: old_test
						| old_test COMMA commaoldtest
	"""

# old_test: or_test 
def p_old_test(p):
	"""old_test : or_test
	"""
# trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME
def p_trailer(p):
	"""trailer 	: LPAREN RPAREN
				| LPAREN arglist RPAREN
				| LSQB short_slice RSQB
				| LSQB slice_list RSQB
				| DOT NAME
	"""
# slices
# slicing          ::=  simple_slicing | extended_slicing
# simple_slicing   ::=  primary "[" short_slice "]"
# extended_slicing ::=  primary "[" slice_list "]"
# slice_list       ::=  slice_item ("," slice_item)* [","]
# slice_item       ::=  expression | proper_slice | ellipsis
# proper_slice     ::=  short_slice | long_slice
# short_slice      ::=  [lower_bound] ":" [upper_bound]
# long_slice       ::=  short_slice ":" [stride]
# lower_bound      ::=  expression
# upper_bound      ::=  expression
# stride           ::=  expression
# ellipsis         ::=  "..."


def p_slice_list(p):
	"""slice_list 	: slice_item slice_item_list
	"""

def p_slice_item_list(p):
	"""slice_item_list 	: 
						| COMMA
						| COMMA slice_item slice_item_list
	"""


def p_slice_item(p):
	"""slice_item 	: test
					| proper_slice
					| ellipsis
	"""
def p_proper_slice(p):
	"""proper_slice 	: short_slice
						| long_slice
	"""
def p_short_slice(p):
	"""short_slice 	: lower_bound COLON
					| lower_bound COLON upper_bound
					| COLON
					| COLON upper_bound
	"""

def p_long_slice(p):
	"""long_slice 	: short_slice COLON 
					| short_slice COLON stride
	"""
def p_lower_bound(p):
	"""lower_bound : test
	"""
def p_upper_bound(p):
	"""upper_bound 	: test
	"""
def p_stride(p):
	"""stride 	: test
	"""
def p_ellipsis(p):
	"""ellipsis 	: DOT DOT DOT
	"""

# exprlist: expr (',' expr)* [',']
def p_exprlist(p):
	"""exprlist 	: expr
					| expr COMMA
					| expr COMMA exprlist
	"""

# testlist: test (',' test)* [', ']
def p_testlist(p):
	"""testlist 	: test
					| test COMMA
					| test COMMA testlist
	"""


# dictorsetmaker: ( (test ':' test (comp_for | (',' test ':' test)* [','])) |
#                   (test (comp_for | (',' test)* [','])) )

def p_dictorsetmaker(p):
	"""dictorsetmaker 	: test COLON test comp_for
						| test comp_for
						| testcolonlist
						| testlist
	"""

# our new symbol
def p_testcolonlist(p):
	"""testcolonlist 	: test COLON test
						| test COLON test COMMA
						| test COLON test COMMA testcolonlist
	"""

# classdef: 'class' NAME ['(' [testlist] ')'] ':' suite
def p_classdef(p):
	"""classdef 	: CLASS NAME COLON suite
					| CLASS NAME LPAREN RPAREN COLON suite
					| CLASS NAME LPAREN testlist RPAREN COLON suite
	"""


# arglist: (argument ',')* (argument [',']
#                          |'*' test (',' argument)* [',' '**' test] 
#                          |'**' test)

def p_arglist(p):
	"""arglist 	: arglist1
				| arglist3 STAR test arglist2 COMMA STAR STAR test
				| arglist3 STAR test arglist2
				| arglist3 STAR STAR test
	"""

def p_arglist3(p):
	"""arglist3 	:
					| argument COMMA arglist3
	"""
def p_arglist2(p):
	"""arglist2 	: 
					| arglist2 COMMA argument
	"""


def p_arglist1(p):
	"""arglist1 	: argument
				| argument COMMA
				| argument COMMA arglist1
	"""

# argument: test [comp_for] | test '=' test
def p_argument(p):
	"""argument 	: test
					| test comp_for
					| test EQUAL test
	"""

# comp_iter: comp_for | comp_if
def p_comp_iter(p):
	"""comp_iter 	: comp_for
					| comp_if
	"""

# comp_for: 'for' exprlist 'in' or_test [comp_iter]
def p_comp_for(p):
	"""comp_for 	: FOR targetlist IN or_test
					| FOR targetlist IN or_test comp_iter
	"""

# comp_if: 'if' old_test [comp_iter]
def p_comp_if(p):
	"""comp_if 	: IF old_test
				| IF old_test comp_iter
	"""
# testlist1: test (',' test)*
def p_testlist1(p):
	"""testlist1 	: test
					| test COMMA testlist1
					
	"""

def p_stmts(p):
	"""stmts 	: stmts stmt
				| stmt"""

def p_targetlist(p):
	"""targetlist	: target
					| target COMMA
					| target COMMA targetlist
	"""

def p_target(p):
	"""target	: NAME
				| LPAREN targetlist RPAREN
				| LSQB RSQB
				| LSQB targetlist RSQB
				| atom trailerlist DOT NAME
				| atom trailerlist LSQB testlist RSQB
				| atom trailerlist LSQB slice_list RSQB
				| STAR target
	"""

def p_error(p):
	# Replace newline and comma because they're used for contextual purposes here
    print(str(p.type) + "," + str(p.value).replace("\n", "~newline").replace(",", "~comma") + \
    	  "," + str(p.lineno) + "," + str(p.lexpos))


class G1Parser(object):
	def __init__(self, mlexer=None):
		if mlexer is None:
			mlexer = G1Lexer()
		self.mlexer = mlexer
		self.parser = yacc(start="file_input", debug=True)

	def parse(self, code):
		self.mlexer.input(code)
		result = self.parser.parse(lexer=self.mlexer, debug=True)
		return result

def runLexer(code, dumpFile):
	tmpout, tmperr = sys.stdout, sys.stderr
	sys.stdout = outResult = io.StringIO()
	z = G1Parser()
	with open(dumpFile, "w") as e:
		sys.stderr = e
		root = z.parse(code)
		sys.stderr = tmperr
	error = ""
	with open(dumpFile, "r") as e:
		error = e.read()
	sys.stdout = tmpout
	return outResult.getvalue(), error

if __name__ == "__main__":
	z = G1Parser()
	with open(sys.argv[1], "r") as i:
		code = i.read()
	with open(sys.argv[3], "w") as e:
		sys.stderr = e
		root = z.parse(code)