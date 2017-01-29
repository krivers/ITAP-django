"""This is a file of useful functions used throughout the hint generation program"""
import time, os.path, ast, test, json
from .paths import *

def log(msg, filename="main", newline=True):
	txt = ""
	if newline:
		t = time.strftime("%d %b %Y %H:%M:%S")
		txt += t + "\t"
	txt += msg
	if newline:
		txt += "\n"
	f = open(LOG_PATH + filename + ".log", "a")
	f.write(txt)
	f.close()

def parse_table(filename):
	with open(filename, "r") as f:
		txt = f.read()
	return smart_parse(txt)

def smart_parse(t, sep=","):
	"""Parse a string into a 2d spreadsheet"""
	# First, fix stupid carriage return errors
	t = t.replace("\r\n", "\n").replace("\n\r", "\n").replace("\r", "\n")

	# A sheet is made of lines, which are made of tokens
	sheet, line, token = [], [], ""
	inString = False
	for i in range(len(t)):
		if t[i] == '"': 
			# Keep track of strings so they can be parsed correctly
			inString = not inString
			continue

		if (not inString) and (t[i] == sep):
			line.append(token)
			token = ""
		elif (not inString) and (t[i] == "\n"):
			if len(token) > 0:
				line.append(token)
				token = ""
			sheet.append(line)
			line = []
		else:
			token += t[i]

	# Catch any stragglers
	if len(token) > 0:
		line.append(token)
	if len(line) > 0:
		sheet.append(line)
	return sheet

def powerSet(l):
	if len(l) == 0:	return [[]]
	head = l[-1]
	rest = powerSet(l[:-1])
	newL = []
	for x in rest:
		newL.append(x)
		newL.append(x + [head])
	return newL

# Power Set for really large sets- just look at groups of 1, 2, n-1, and n-2
def fastPowerSet(changes, includeSmallSets=True):
	single, allButOne = [], []
	for i in range(len(changes)):
		if includeSmallSets:
			single.append([changes[i]])
		allButOne.append(changes[:i] + changes[i+1:])
	return single + allButOne

def isStrictSubset(s1, s2):
	"""A strict subset must be smaller than its superset"""
	if len(s1) == len(s2):	return False
	return isSubset(s1, s2)

def isSubset(s1, s2):
	"""Returns whether s1 is a subset of s2"""
	if len(s1) == 0:	return True
	if s1[0] in s2:
		i = s2.index(s1[0])
		return isSubset(s1[1:], s2[:i] + s2[i+1:])
	else:
		return False