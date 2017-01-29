class SyntaxEdit:
	line = -1
	col = -1
	totalCol = -1
	editType = None
	text = ""
	newText = ""

	def __init__(self, line, col, totalCol, editType, text, newText=None):
		self.line = line
		self.col = col
		self.totalCol = totalCol
		self.editType = editType
		self.text = text
		if newText != None:
			self.newText = newText

	def __repr__(self):
		return self.editType + " Edit: " + repr(self.text) + ((" - " + repr(self.newText)) if self.newText != "" else "") + \
			" : (" + str(self.line) + ", " + str(self.col) + ", " + str(self.totalCol) + ")"

	def __cmp__(self, other):
		if not isinstance(other, SyntaxEdit):
			return cmp("SyntaxEdit", type(other))
		for field in ["editType", "line", "col", "totalCol", "text", "newText"]:
			if getattr(self, field) != getattr(other, field):
				return cmp(getattr(self, field), getattr(other, field))
		return 0

	def textDiff(self):
		if self.editType in ["deindent", "-"]:
			return len(self.text)
		elif self.editType in ["indent", "+"]:
			return -len(self.text)
		else:
			return len(self.text) - len(self.newText)