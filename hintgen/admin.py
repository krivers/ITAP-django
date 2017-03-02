from django.contrib import admin

from .models import *

# Inlines

class StudentsInline(admin.TabularInline):
    model = Student

class ProblemsInline(admin.TabularInline):
    model = Course.problems.through

class TestcasesInline(admin.TabularInline):
    model = Testcase

class SourceStateInline(admin.TabularInline):
    model = SourceState


# Admins

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('year', 'semester', 'name')
    inlines = [
        ProblemsInline,
        StudentsInline,
    ]

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('course', 'name', 'condition', 'id')
    inlines = [
        SourceStateInline,
    ]

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('name',)
    inlines = [
        TestcasesInline,
    #    SourceStateInline,
    ]

@admin.register(Hint)
class HintAdmin(admin.ModelAdmin):
    list_display = ('level', 'message', 'id')
    #inlines = [
    #    SourceStateInline,
    #]

@admin.register(Testcase)
class TestcaseAdmin(admin.ModelAdmin):
    list_display = ('problem', 'id')

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('problem', 'score', 'id')

@admin.register(SourceState)
class SourceStateAdmin(admin.ModelAdmin):
    list_display = ('problem', 'student', 'score', 'id')

@admin.register(CleanedState)
class CleanedStateAdmin(admin.ModelAdmin):
    list_display = ('problem', 'count', 'score', 'id')

@admin.register(AnonState)
class AnonStateAdmin(admin.ModelAdmin):
    list_display = ('problem', 'count', 'score', 'id')


@admin.register(CanonicalState)
class CanonicalStateAdmin(admin.ModelAdmin):
    list_display = ('problem', 'count', 'score', 'id')
