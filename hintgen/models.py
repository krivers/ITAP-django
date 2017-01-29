from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=100)
    semester = models.CharField(max_length=50, blank=True)
    year = models.IntegerField()
    def __str__(self):
        return str(self.year) + " " + self.semester + ": " + self.name

    class Meta:
        ordering = ['-year', '-semester', 'name']

class Student(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name="students")
    name = models.CharField(max_length=100, blank=True)
    condition = models.CharField(max_length=50, blank=True)
    def __str__(self):
        if self.name != "":
            return self.name
        return "Student " + str(self.id)

class Problem(models.Model):
    courses = models.ManyToManyField(Course, related_name="problems")
    name = models.CharField(max_length=50)
    solution = models.ForeignKey('SourceState', on_delete=models.SET_NULL, related_name="+", blank=True, null=True)
    arguments = models.CharField(max_length=500) # should be interpreted by pickle
    given_code = models.TextField(blank=True) # should be interpreted by pickle
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Testcase(models.Model):
    problem = models.ForeignKey('Problem', on_delete=models.CASCADE, related_name="tests")
    test_input = models.TextField() # should be interpreted by pickle
    test_output = models.TextField() # should be interpreted by pickle
    test_extra = models.TextField(blank=True) # specific keywords specify extra tests. For example, 'checkCopy' checks if the input is modified
    def __str__(self):
        return "Test " + str(self.id) + " for " + str(self.problem)

    class Meta:
        ordering = ['problem', 'id']

class State(models.Model):
    code = models.TextField()
    problem = models.ForeignKey('Problem', on_delete=models.CASCADE, related_name="states")
    score = models.FloatField(blank=True, null=True)
    count = models.IntegerField(default=0)
    feedback = models.TextField(blank=True)
    tree_source = models.TextField(blank=True) # should be interpreted by pickle
    treeWeight = models.IntegerField(blank=True, null=True)
    next = models.ForeignKey('State', on_delete=models.SET_NULL, related_name="prev", blank=True, null=True)
    goal = models.ForeignKey('State', on_delete=models.SET_NULL, related_name="feeder", blank=True, null=True)
    def __str__(self):
        return str(self.problem) + " State " + str(self.id)

    class Meta:
        ordering = ['problem', 'id']

class SourceState(State):
    timestamp = models.DateTimeField(auto_now_add=True)
    student = models.ForeignKey('Student', on_delete=models.SET_NULL, related_name="code_states", blank=True, null=True)
    cleaned = models.ForeignKey('CleanedState', on_delete=models.SET_NULL, related_name="source_states", blank=True, null=True)
    hint = models.ForeignKey('Hint', on_delete=models.SET_NULL, related_name="code_state", blank=True, null=True)

class CleanedState(State):
    anon = models.ForeignKey('AnonState', on_delete=models.SET_NULL, related_name="cleaned_states", blank=True, null=True)

class AnonState(State):
    canonical = models.ForeignKey('CanonicalState', on_delete=models.SET_NULL, related_name="anon_states", blank=True, null=True)
    orig_tree_source = models.TextField(blank=True)

class CanonicalState(State):
    orig_tree_source = models.TextField(blank=True)

class Hint(models.Model):
    message = models.TextField(blank=True)
    level = models.CharField(max_length=50, blank=True, null=True)
    line = models.IntegerField(blank=True, null=True)
    col = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return str(self.level) + " " + str(self.id)

    class Meta:
        ordering = ['level', '-id']
