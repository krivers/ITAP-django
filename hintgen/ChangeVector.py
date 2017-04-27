import ast, copy
from .astTools import compareASTs, deepcopy
from .display import printFunction
from .tools import log

class ChangeVector:
	start = None
	path = None
	oldSubtree = None
	newSubtree = None

	def __init__(self, path, oldSubtree, newSubtree, start=None):
		self.start = start
		self.path = path
		self.oldSubtree = oldSubtree
		self.newSubtree = newSubtree

	def __repr__(self):
		oldStr = printFunction(self.oldSubtree, 0) if isinstance(self.oldSubtree, ast.AST) else repr(self.oldSubtree)
		newStr = printFunction(self.newSubtree, 0) if isinstance(self.newSubtree, ast.AST) else repr(self.newSubtree)
		return oldStr + " - " + newStr + " : " + str(self.path)

	def __cmp__(self, other):
		if not isinstance(other, ChangeVector):
			return -1
		c1 = cmp(self.path, other.path)
		if c1 != 0:
			return c1
		else:
			c2 = compareASTs(self.oldSubtree, other.oldSubtree)
			if c2 != 0:
				return c2
			else:
				c3 = compareASTs(self.newSubtree, other.newSubtree)
				if c3 != 0:
					return c3
				else:
					return compareASTs(self.start, other.start)

	def deepcopy(self):
		path = self.path[:] if self.path != None else None
		c = ChangeVector(path, deepcopy(self.oldSubtree), deepcopy(self.newSubtree), start=deepcopy(self.start))
		return c

	def createMapDict(self, mapDict, treeSpot):
		# the 'pos' element holds a list where positions map to original positions.
		# so if we have the list [ 0, 3, 4 ], then the first line is in the original place,
		# but the second and third lines were deleted, so 3 and 4 have moved in their palces.
		mapDict["len"] = len(treeSpot)
		mapDict["pos"] = list(range(len(treeSpot)))
		for i in mapDict["pos"]:
			mapDict[i] = { }

	def updateTree(self, treeSpot, mapDict, path=None):
		# Update the positions in the path to account for the mapDict
		if path == None:
			path = self.path
		curKey = "start"
		for i in range(len(path)-1, 0, -1):
			move = path[i]
			mapDict = mapDict[curKey]
			if type(move) == tuple:
				if move[0] not in mapDict:
					mapDict[move[0]] = {}
				curKey = move[0] # No trouble here
				treeSpot = getattr(treeSpot, move[0])
			elif type(move) == int:
				if "pos" not in mapDict: # set up data for original position and length
					self.createMapDict(mapDict, treeSpot)
				realMove = mapDict["pos"].index(move) 
				path[i] = realMove # update the change path! This is the key action!
				curKey = move # use the original here, as keys aren't changed in the mapDict repr
				treeSpot = treeSpot[realMove]
		mapDict = mapDict[curKey]
		return treeSpot, mapDict

	def update(self, newStart, mapDict): 
		# WARNING: mapDict will be modified!
		self.start = newStart
		treeSpot, mapDict = self.updateTree(newStart, mapDict)

		# Update locations in the last position
		location = self.path[0]
		if type(treeSpot) == list and "pos" not in mapDict:
			self.createMapDict(mapDict, treeSpot)

		if type(location) == int and type(treeSpot) == list:
			self.path[0] = mapDict["pos"].index(location)

	def traverseTree(self, t, path=None):
		if path == None:
			path = self.path
		treeSpot = t
		for i in range(len(path)-1, 0, -1):
			move = path[i]
			if type(move) == tuple:
				if hasattr(treeSpot, move[0]):
					treeSpot = getattr(treeSpot, move[0])
				else:
					log("Change Vector\ttraverseTree\t\tMissing attr: " + str(move[0]), "bug")
					return -99
			elif type(move) == int:
				if type(treeSpot) == list:
					if move >= 0 and move < len(treeSpot):
						treeSpot = treeSpot[move]
					else:
						log("Change Vector\ttraverseTree\t\tMissing position: " + str(move) + "," + str(treeSpot), "bug")
						return -99
				else:
					log("Change Vector\ttraverseTree\t\tNot a list: " + str(treeSpot), "bug")
					return -99

			else: # wat?
				log("Change Vector\ttraverseTree\t\tBad Path: " + str(move), "bug")
				return -99
		return treeSpot

	def applyChange(self):
		tree = deepcopy(self.start)
		treeSpot = self.traverseTree(tree)
		if treeSpot == -99:
			return None

		# Make the change in the last position
		location = self.path[0]
		if type(location) == tuple and hasattr(treeSpot, location[0]):
			oldSpot = getattr(treeSpot, location[0])
			# Make life easier for ourselves when applying multiple changes at once
			if self.newSubtree != None and oldSpot != None:
				if hasattr(oldSpot, "lineno"):
					self.newSubtree.lineno = oldSpot.lineno
				if hasattr(oldSpot, "col_offset"):
					self.newSubtree.col_offset = oldSpot.col_offset
			setattr(treeSpot, location[0], self.newSubtree)
			# SPECIAL CASE. If we're changing the variable name, get rid of originalId
			if type(treeSpot) == ast.Name and location[0] == "id":
				treeSpot.originalId = None
			elif type(treeSpot) == ast.arg and location[0] == "arg":
				treeSpot.originalId = None
		elif type(location) == int and type(treeSpot) == list:
			if hasattr(treeSpot[location], "lineno"):
				self.newSubtree.lineno = treeSpot[location].lineno
			if hasattr(treeSpot[location], "col_offset"):
				self.newSubtree.col_offset = treeSpot[location].col_offset
			# Need to swap out whatever is in this location
			if location >= 0 and location < len(treeSpot):
				treeSpot[location] = self.newSubtree
			else:
				log("ChangeVector\tapplyChange\tDoesn't fit in list: " + str(location), "bug")
		else:
			log("ChangeVector\tapplyChange\t\tBroken at: " + str(location), "bug")
		return tree

	def isReplaceVector(self):
		return not (isinstance(self, SubVector) or isinstance(self, SuperVector) or isinstance(self, AddVector) or isinstance(self, DeleteVector) or isinstance(self, SwapVector) or isinstance(self, MoveVector))

class SubVector(ChangeVector):
	# This class represents a vector where the value is a subexpression of the needed value

	def __cmp__(self, other):
		if (not isinstance(other, ChangeVector)) or isinstance(other, SuperVector) or \
			isinstance(other, AddVector) or isinstance(other, DeleteVector) or \
			isinstance(other, SwapVector) or isinstance(other, MoveVector):
			return -1
		if not isinstance(other, SubVector):
			return 1
		return ChangeVector.__cmp__(self, other)

	def __repr__(self):
		oldStr = printFunction(self.oldSubtree, 0) if isinstance(self.oldSubtree, ast.AST) else repr(self.oldSubtree)
		newStr = printFunction(self.newSubtree, 0) if isinstance(self.newSubtree, ast.AST) else repr(self.newSubtree)
		return "Sub: " + oldStr + " - " + newStr + " : " + str(self.path)

	def deepcopy(self):
		path = self.path[:] if self.path != None else None
		c = SubVector(path, deepcopy(self.oldSubtree), deepcopy(self.newSubtree), start=deepcopy(self.start))
		return c

class SuperVector(ChangeVector):
	# This class represents a vector where the value contains the needed value as a subexpression

	def __cmp__(self, other):
		if (not isinstance(other, ChangeVector)) or isinstance(other, AddVector) or \
			isinstance(other, DeleteVector) or isinstance(other, SwapVector) or \
			isinstance(other, MoveVector):
			return -1
		if not isinstance(other, SuperVector):
			return 1
		return ChangeVector.__cmp__(self, other)

	def __repr__(self):
		oldStr = printFunction(self.oldSubtree, 0) if isinstance(self.oldSubtree, ast.AST) else repr(self.oldSubtree)
		newStr = printFunction(self.newSubtree, 0) if isinstance(self.newSubtree, ast.AST) else repr(self.newSubtree)
		return "Super: " + oldStr + " - " + newStr + " : " + str(self.path)

	def deepcopy(self):
		path = self.path[:] if self.path != None else None
		c = SuperVector(path, deepcopy(self.oldSubtree), deepcopy(self.newSubtree), start=deepcopy(self.start))
		return c

class AddVector(ChangeVector):
	# This class represents where lines are added to a list

	def __cmp__(self, other):
		if (not isinstance(other, ChangeVector)) or isinstance(other, DeleteVector) or \
			isinstance(other, SwapVector) or isinstance(other, MoveVector):
			return -1
		if not isinstance(other, AddVector):
			return 1
		return ChangeVector.__cmp__(self, other)

	def __repr__(self):
		oldStr = printFunction(self.oldSubtree, 0) if isinstance(self.oldSubtree, ast.AST) else repr(self.oldSubtree)
		newStr = printFunction(self.newSubtree, 0) if isinstance(self.newSubtree, ast.AST) else repr(self.newSubtree)
		return "Add: " + oldStr + " - " + newStr + " : " + str(self.path)

	def deepcopy(self):
		path = self.path[:] if self.path != None else None
		c = AddVector(path, deepcopy(self.oldSubtree), deepcopy(self.newSubtree), start=deepcopy(self.start))
		return c

	def applyChange(self):
		tree = deepcopy(self.start)
		treeSpot = self.traverseTree(tree)
		if treeSpot == -99:
			return None

		# Make the change in the last position
		location = self.path[0]
		if type(treeSpot) == list:
			# Add the new line
			treeSpot.insert(location, self.newSubtree)
		else:
			log("AddVector\tapplyChange\t\tBroken at: " + str(location), "bug")
			return None
		return tree

	def update(self, newStart, mapDict): 
		# WARNING: mapDict will be modified!
		self.start = newStart
		treeSpot, mapDict = self.updateTree(newStart, mapDict)

		# Update locations in the last position
		location = self.path[0]
		if "pos" not in mapDict:
			self.createMapDict(mapDict, treeSpot)

		# Update based on the original position
		if location != mapDict["len"]:
			if location in mapDict["pos"]:
				location = mapDict["pos"].index(location)
			else:
				if location < mapDict["len"]:
					# Find the previous location and put this after it
					i = len(mapDict["pos"]) - 1
					while mapDict["pos"][i] == -1 and i >= 0:
						i -= 1
					if i >= 0:
						i += 1
						location = i
					else:
						log("AddVector\tupdate\t\tMissing position: " + str(location) + "," + str(mapDict["pos"]), "bug")
						return
		else: # if it IS equal to the length, put it in the back
			location = len(mapDict["pos"])

		self.path[0] = location # make sure to update!

		# Add the new line
		mapDict["pos"].insert(location, -1)

class DeleteVector(ChangeVector):
	# This class represents a change where lines are removed from a list
	def __cmp__(self, other):
		if (not isinstance(other, ChangeVector)) or isinstance(other, SwapVector) or \
			isinstance(other, MoveVector):
			return -1
		if not isinstance(other, DeleteVector):
			return 1
		return ChangeVector.__cmp__(self, other)

	def __repr__(self):
		oldStr = printFunction(self.oldSubtree, 0) if isinstance(self.oldSubtree, ast.AST) else repr(self.oldSubtree)
		newStr = printFunction(self.newSubtree, 0) if isinstance(self.newSubtree, ast.AST) else repr(self.newSubtree)
		return "Delete: " + oldStr + " - " + newStr + " : " + str(self.path)

	def deepcopy(self):
		path = self.path[:] if self.path != None else None
		c = DeleteVector(path, deepcopy(self.oldSubtree), deepcopy(self.newSubtree), start=deepcopy(self.start))
		return c

	def applyChange(self):
		tree = deepcopy(self.start)
		treeSpot = self.traverseTree(tree)
		if treeSpot == -99:
			return None

		# Make the change in the last position
		location = self.path[0]
		if type(treeSpot) == list:
			# Remove the old line
			if location < len(treeSpot):
				del treeSpot[location]
			else:
				log("DeleteVector\tapplyChange\t\tBad location: " + str(location) + "\t" + str(self.oldSubtree), "bug")
				return None
		else:
			log("DeleteVector\tapplyChange\t\tBroken at: " + str(location), "bug")
			return None
		return tree

	def update(self, newStart, mapDict):
		# WARNING: mapDict will be modified!
		self.start = newStart
		treeSpot, mapDict = self.updateTree(newStart, mapDict)

		# Update locations in the last position
		location = self.path[0]
		if "pos" not in mapDict:
			self.createMapDict(mapDict, treeSpot)

		# Update based on the original position
		location = mapDict["pos"].index(location)

		self.path[0] = location # make sure to update!

		# Remove the old line
		mapDict["pos"].pop(location)

class SwapVector(ChangeVector):
	# This class represents a change where two lines are swapped
	oldPath = newPath = None

	def __cmp__(self, other):
		if (not isinstance(other, ChangeVector)) or isinstance(other, MoveVector):
			return -1
		if not isinstance(other, SwapVector):
			return 1
		return ChangeVector.__cmp__(self, other)

	def __repr__(self):
		oldStr = printFunction(self.oldSubtree, 0) if isinstance(self.oldSubtree, ast.AST) else repr(self.oldSubtree)
		newStr = printFunction(self.newSubtree, 0) if isinstance(self.newSubtree, ast.AST) else repr(self.newSubtree)
		if self.oldPath != None:
			return "Swap: " + oldStr + " : " + str(self.oldPath) + "\n" + \
							  newStr + " : " + str(self.newPath)
		else:
			return "Swap: " + oldStr + " - " + newStr + " : " + str(self.path)

	def deepcopy(self):
		path = self.path[:] if self.path != None else None
		c = SwapVector(path, deepcopy(self.oldSubtree), deepcopy(self.newSubtree), start=deepcopy(self.start))
		c.oldPath = self.oldPath[:] if self.oldPath != None else None
		c.newPath = self.newPath[:] if self.newPath != None else None
		return c

	def applyChange(self):
		tree = deepcopy(self.start)

		if self.oldPath == None:
			treeSpot = self.traverseTree(tree)
			if treeSpot == -99:
				return None

			if type(treeSpot) == list and self.oldSubtree < len(treeSpot) and \
			   self.newSubtree < len(treeSpot):
				(treeSpot[self.oldSubtree], treeSpot[self.newSubtree]) = (treeSpot[self.newSubtree], treeSpot[self.oldSubtree])
			else:
				log("SwapVector\tapplyChange\t\tBroken at: " + str(treeSpot), "bug")
				return None
		else:
			oldTreeSpot = self.traverseTree(tree, path=self.oldPath)
			newTreeSpot = self.traverseTree(tree, path=self.newPath)
			if oldTreeSpot == -99 or newTreeSpot == -99:
				return None

			if type(self.oldPath[0]) == int:
				tmpOldValue = oldTreeSpot[self.oldPath[0]]
			else:
				tmpOldValue = getattr(oldTreeSpot, self.oldPath[0][0])

			if type(self.newPath[0]) == int:
				tmpNewValue = newTreeSpot[self.newPath[0]]
			else:
				tmpNewValue = getattr(newTreeSpot, self.newPath[0][0])

			if type(self.oldPath[0]) == int:
				oldTreeSpot[self.oldPath[0]] = tmpNewValue
			else:
				setattr(oldTreeSpot, self.oldPath[0][0], tmpNewValue)

			if type(self.newPath[0]) == int:
				newTreeSpot[self.newPath[0]] = tmpOldValue
			else:
				setattr(newTreeSpot, self.newPath[0][0], tmpOldValue)
		return tree

	def update(self, newStart, mapDict): 
		# WARNING: mapDict will be modified!
		self.start = newStart

		if "moved" in mapDict:
			mapDict["moved"] += [self.oldSubtree, self.newSubtree]
		else:
			mapDict["moved"] = [self.oldSubtree, self.newSubtree]

		if self.oldPath == None:
			treeSpot, mapDict = self.updateTree(newStart, mapDict)
			if "pos" not in mapDict:
				self.createMapDict(mapDict, treeSpot)

			# Update based on the original position
			self.oldSubtree = mapDict["pos"].index(self.oldSubtree)
			self.newSubtree = mapDict["pos"].index(self.newSubtree)

			(mapDict["pos"][self.oldSubtree], mapDict["pos"][self.newSubtree]) = (mapDict["pos"][self.newSubtree], mapDict["pos"][self.oldSubtree])
		else:
			oldTreeSpot, oldMapDict = self.updateTree(newStart, mapDict, path=self.oldPath)
			newTreeSpot, newMapDict = self.updateTree(newStart, mapDict, path=self.newPath)
			if type(oldTreeSpot) == int:
				if "pos" not in oldMapDict:
					self.createMapDict(oldMapDict, oldTreeSpot)
				self.oldSubtree = oldMapDict["pos"].index(self.oldSubtree)
			if type(newTreeSpot) == int:
				if "pos" not in newMapDict:
					self.createMapDict(newMapDict, newTreeSpot)
				self.newSubtree = newMapDict["pos"].index(self.newSubtree)
			if type(oldTreeSpot) == type(newTreeSpot) == int:
				(oldMapDict["pos"][self.oldSubtree], newMapDict["pos"][self.newSubtree]) = (newMapDict["pos"][self.newSubtree], oldMapDict["pos"][self.oldSubtree])

	def getSwapees(self):
		if self.oldPath == None:
			treeSpot = self.traverseTree(self.start)
			if type(treeSpot) == list and self.oldSubtree < len(treeSpot) and \
				self.newSubtree < len(treeSpot):
				return (treeSpot[self.oldSubtree], treeSpot[self.newSubtree])
			else:
				log("SwapVector\tgetSwapees\tBroken: \n" + printFunction(treeSpot, 0) + "," + printFunction(self.oldSubtree, 0) + "," + printFunction(self.newSubtree, 0) + "\n" + printFunction(self.start, 0), "bug")
		else:
			oldTreeSpot = self.traverseTree(self.start, path=self.oldPath)
			newTreeSpot = self.traverseTree(self.start, path=self.newPath)
			if type(self.oldPath[0]) == int and type(oldTreeSpot) == list and self.oldPath[0] < len(oldTreeSpot):
				oldValue = oldTreeSpot[self.oldPath[0]]
			elif type(self.oldPath[0]) == tuple and hasattr(oldTreeSpot, self.oldPath[0][0]):
				oldValue = getattr(oldTreeSpot, self.oldPath[0][0])
			else:
				log("SwapVector\tgetSwapees\tBroken oldValue")
				oldValue = None

			if type(self.newPath[0]) == int and type(newTreeSpot) == list and self.newPath[0] < len(newTreeSpot):
				newValue = newTreeSpot[self.newPath[0]]
			elif type(self.newPath[0]) == tuple and hasattr(newTreeSpot, self.newPath[0][0]):
				newValue = getattr(newTreeSpot, self.newPath[0][0])
			else:
				log("SwapVector\tgetSwapees\tBroken newValue")
				newValue = None

			return (oldValue, newValue)
		return (None, None)

	def getSwapeePaths(self):
		if oldPath == None:
			return (self.path, self.path)
		else:
			return (self.oldPath, self.newPath)

class MoveVector(ChangeVector):
	# This class represents a change where one line is moved somewhere else in the list

	def __cmp__(self, other):
		if not isinstance(other, ChangeVector):
			return -1
		if not isinstance(other, MoveVector):
			return 1
		return ChangeVector.__cmp__(self, other)

	def __repr__(self):
		oldStr = printFunction(self.oldSubtree, 0) if isinstance(self.oldSubtree, ast.AST) else repr(self.oldSubtree)
		newStr = printFunction(self.newSubtree, 0) if isinstance(self.newSubtree, ast.AST) else repr(self.newSubtree)
		return "Move: " + oldStr + " - " + newStr + " : " + str(self.path)

	def deepcopy(self):
		path = self.path[:] if self.path != None else None
		c = MoveVector(path, deepcopy(self.oldSubtree), deepcopy(self.newSubtree), start=deepcopy(self.start))
		return c

	def applyChange(self):
		tree = deepcopy(self.start)
		treeSpot = self.traverseTree(tree)
		if treeSpot == -99:
			return None

		if type(treeSpot) == list and self.oldSubtree < len(treeSpot) and self.newSubtree < len(treeSpot):
			# We'll remove the item from the tree, then put it back in
			item = treeSpot.pop(self.oldSubtree)
			treeSpot.insert(self.newSubtree, item)
		else:
			log("MoveVector\tapplyChange\t\tBroken at: " + str(treeSpot), "bug")
			return None
		return tree

	def update(self, newStart, mapDict):
		# WARNING: mapDict will be modified!
		self.start = newStart
		treeSpot, mapDict = self.updateTree(newStart, mapDict)

		if "moved" in mapDict:
			mapDict["moved"].append(self.oldSubtree)
		else:
			mapDict["moved"] = [self.oldSubtree]

		if "pos" not in mapDict:
			self.createMapDict(mapDict, treeSpot)

		# Update based on the original position.
		if self.oldSubtree not in mapDict["pos"]:
			log("MoveVector\tupdate\t\tCan't find old subtree: " + str(self.oldSubtree) + "," + str(mapDict["pos"]), "bug")
			return

		if self.newSubtree in mapDict["moved"]:
			nextPos = self.newSubtree + 1
			while (mapDict["len"] < nextPos) and (nextPos in mapDict["moved"] or nextPos not in mapDict["pos"]):
				nextPos += 1
			if nextPos >= mapDict["len"]:
				log("ChangeVector\tMoveVector\tupdate\tBad Position!! " + str(self) + ";" + str(mapDict), "bug")
			else:
				self.newSubtree = nextPos
		else:
			if self.newSubtree not in mapDict["pos"]:
				if self.newSubtree < min(mapDict["pos"]):
					self.newSubtree = min(mapDict["pos"]) # just go to the lowest position
				elif self.newSubtree > max(mapDict["pos"]):
					self.newSubtree = max(mapDict["pos"]) # go to the highest position
				else:
					higher = self.newSubtree
					while higher not in mapDict["pos"]:
						higher += 1
					self.newSubtree = higher # go to the next line, as the better place to insert
		self.oldSubtree = mapDict["pos"].index(self.oldSubtree)
		self.newSubtree = mapDict["pos"].index(self.newSubtree)
		index = mapDict["pos"].pop(self.oldSubtree)
		mapDict["pos"].insert(self.newSubtree, index)

	def getItems(self):
		treeSpot = self.traverseTree(self.start)
		return (treeSpot[self.oldSubtree], treeSpot[self.newSubtree])