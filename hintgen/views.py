from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
import json
from .models import *
from .getHint import get_hint

"""
TESTING
Use the following code to test the hint/feedback functions:

from django.test import Client
import json
c = Client()
course_id = 1
problem_id = 4
data = {'student_id' : 'tester', 'code' : "def canDrinkAlcohol(age, isDriving):\n    return age > 21 and not isDriving\n" }
response = c.post('/hintgen/hint/' + str(course_id) + '/' + str(problem_id) + '/', data=data)
"""

# Create your views here.
def index(request):
    return HttpResponse("Hello, world. You've reached the hint generation index!")

def unpack_code_json(request, course_id, problem_id):
    # request_body = request.body.decode('utf-8')
    # if len(request_body) == 0:
    #     return HttpResponseBadRequest("Empty request body; need to include a json object")
    # data = json.loads(request_body)
    data = request.POST
    if 'code' not in data:
        return HttpResponseBadRequest("Need to include a reference to 'code' in the json object")

    if 'student_id' not in data:
        return HttpResponseBadRequest("Need to include a reference to 'student_id' in the json object")

    course = Course.objects.filter(id=course_id)
    if len(course) != 1:
        return HttpResponseBadRequest("No course exists with that ID")
    course = course[0]

    problem = Problem.objects.filter(id=problem_id)
    if len(problem) != 1:
        return HttpResponseBadRequest("No problem exists with that ID")
    problem = problem[0]

    student = Student.objects.filter(name=data["student_id"])
    if len(student) == 0:
        # We haven't seen this student before, but it's okay; we can add them
        student = Student(course=course, name=data["student_id"])
        student.save()
    elif len(student) > 1:
        # Multiple students with the same name! Uh oh.
        return HttpResponseBadRequest("Could not disambiguate student ID; please modify database")
    else:
        student = student[0]

    data["course"] = course
    data["problem"] = problem
    data["student"] = student
    # Clean up return carriages
    data["code"] = data["code"].replace("\r\n", "\n").replace("\n\r", "\n").replace("\r", "\n")
    return data

"""
Test the given code and generate feedback for it.

USAGE
In the url, map:
    course_id -> the course ID for this submission
    problem_id -> the problem ID for this submission
In the request content, include a json object mapping:
    student_id -> the student ID for this submission
    code -> the code being submitted

RETURNS
A json object mapping:
    score -> the resulting score for this submission
    feedback -> the resulting feedback message for this submission
"""
def feedback(request, course_id, problem_id):
    data = unpack_code_json(request, course_id, problem_id)

    if isinstance(data, HttpResponse):
        return data

    code_state = SourceState(code=data["code"], problem=data["problem"], 
                             student=data["student"], count=1)

    code_state = run_tests(code_state)
    result_object = { "score" : code_state.score, "feedback" : code_state.feedback }
    return HttpResponse(json.dumps(result_object))

"""
Given code, generate a hint for that code.

USAGE
In the url, map:
    course_id -> the course ID for this submission
    problem_id -> the problem ID for this submission
In the request content, include a json object mapping:
    student_id -> the student ID for this submission
    code -> the code being submitted

RETURNS
A json object mapping:
    hint_message -> a string containing the resulting hint message
    hint_type -> the type of hint that was generated
    line -> the line number the hint occurs on
    col -> the column number the hint occurs on
"""
def hint(request, course_id, problem_id):
    data = unpack_code_json(request, course_id, problem_id)

    if isinstance(data, HttpResponse):
        return data

    code_state = SourceState(code=data["code"], problem=data["problem"], 
                             student=data["student"], count=1)

    code_state = get_hint(code_state)
    result_object = { "hint_message" : code_state.hint.message, "line" : code_state.hint.line,
                      "col" : code_state.hint.col, "hint_type" : code_state.hint.level }
    return HttpResponse(json.dumps(result_objecct))

def unpack_problem_json(request):
    data = json.loads(request.body.decode('utf-8'))
    if "name" not in data:
        return HttpResponseBadRequest("Need to include a reference to 'name' in the json object")
    if "courses" not in data:
        return HttpResponseBadRequest("Need to include a reference to 'courses' in the json object")
    if "tests" not in data:
        return HttpResponseBadRequest("Need to include a reference to 'tests' in the json object")
    if "solution_code" not in data:
        return HttpResponseBadRequest("Need to include a reference to 'solution_code' in the json object")

    courses = []
    for c in data["courses"]:
        course = Course.objects.filter(id=c)
        if len(course) != 1:
            return HttpResponseBadRequest("No course exists with the ID " + str(c))
        courses.append(course[0])
    data["courses"] = courses
    return data

"""
Sets up a problem which can then be used for feedback and hint generation.

USAGE
Request data should be a json object which includes the maps:
    name -> a string representing the name of the problem (what the function should be called)
    courses -> a list of course IDs you want to associate this problem with. The courses should already exist in the system
    tests -> a list of dictionaries, where each dictionary contains test case info:
        input -> a string which, when evaluated with eval(), turns into a tuple containing arguments
        output -> a string which, when evaluated with eval(), turns into the value that the function should return, given input
        extra -> optional. if extra is mapped to "check_copy", the test case will check to make sure that the input isn't modified
    solution_code -> a string containing a code solution to the problem. Must pass all the given test cases!
    arguments -> optional. a dictionary that maps function names to lists of the argument types they expect (represented as strings). If the argument type can vary, it can be represented with "None"
    given_code -> optional. a string containing given code that is provided and should be included when testing a student's submission.

RETURNS
A json object mapping:
    problem_id -> the problem's new ID
"""
def setup_problem(request):
    data = unpack_problem_json(request)

    if isinstance(data, HttpResponse):
        return data

    problem = Problem(name=data["name"])
    if "arguments" in data:
        problem.arguments = str(data["arguments"])
    else:
        problem.arguments = "{ }"
    
    if "given_code" in data:
        problem.given_code = data["given_code"]

    problem.courses.add(*data["courses"])
    problem.save()

    # Set up new test cases
    tests = data["tests"]
    test_objects = []
    for test in tests:
        if "input" not in test:
            problem.delete()
            return HttpResponseBadRequest("Input missing from one or more test cases")
        if "output" not in test:
            problem.delete()
            return HttpResponseBadRequest("Output missing from one or more test cases")
        t = Testcase(problem=problem, test_input=test["input"], test_output=test["output"])
        if "extra" in test:
            t.test_extra = test["extra"]
        test_objects.append(t)
    for t in test_objects:
        t.save()

    # Set up teacher solution
    admin = Student.objects.get(id=1) # admin account
    teacher_solution = SourceState(code=data["solution_code"], problem=problem, 
                                   count=1, student=admin)
    teacher_solution = run_tests(teacher_solution)
    if teacher_solution.score != 1:
        feedback = teacher_solution.feedback
        problem.delete()
        for test in test_objects:
            test.delete()
        teacher_solution.delete()
        return HttpResponseBadRequest("The provided solution does not pass the provided test cases. Please try again. Failing feedback: " + feedback)

    return HttpResponse(json.dumps({ "problem_id" : problem.id }))