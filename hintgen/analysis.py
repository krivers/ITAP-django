from .getHint import *

def clear_solution_space(problem, keep_starter=True):
    old_states = State.objects.filter(problem=problem.id)
    if len(old_states) > 1:
        # Clean out the old states
        starter_code = list(old_states)[0].code
        #log("Deleting " + str(len(old_states)) + " old states...", "bug")
        old_states.delete()

        if keep_starter:
            # But save the instructor solution!
            starter_state = SourceState(code=starter_code, problem=problem, count=1, student=Student.objects.get(id=1))
            starter_state = get_hint(starter_state)
            starter_state.save()
            problem.solution = starter_state
            problem.save()

stats_problem_set = [
                "all_three_chars", "any_divisible", "any_first_chars", 
                "any_lowercase", "can_drink_alcohol", "can_make_breakfast",
                "convert_to_degrees", "count_all_empty_strings", 
                "create_number_block", "factorial", "find_root", 
                "find_the_circle", "first_and_last", "get_extra_bagel", 
                "go_to_gym", "has_balanced_parentheses", "has_extra_fee", 
                "has_two_digits", "hello_world", "how_many_egg_cartons", 
                "is_even_positive_int", "is_leap_month", "is_prime", 
                "is_punctuation", "is_substring", "kth_digit", "last_index", 
                "list_of_lists", "multiply_numbers", "nearest_bus_stop", 
                "no_positive_even", "one_to_n", "over_nine_thousand", 
                "reduce_to_positive", "second_largest", "single_pig_latin", 
                "sum_all_even_numbers", "sum_of_digits", "sum_of_odd_digits", 
                "was_lincoln_alive", "wear_a_coat",  
                ]

def run_all_problems():
    problems = stats_problem_set
    for problem in problems:
        log("Running " + problem, "bug")
        import_code_as_states("hintgen/combined_data/"+problem+".csv", 1,
            problem, clear_space=True, run_profiler=False, run_hint_chain=False)

def test_solution_space():
    problems = stats_problem_set
    for problem in problems:
        for count in range(20):
            log("Running " + problem + " " + str(count), "bug")
            run_solution_space_improvement("hintgen/combined_data/" + problem + ".csv", problem, "random")
            os.rename(LOG_PATH + problem + "_" + "random" + ".csv", 
                      LOG_PATH + problem + "_" + "random" + "_" + str(count) + ".csv")


def run_all_spaces(keyword):
    problems = stats_problem_set
    for problem in problems:
        log("Running " + problem, "bug")
        run_solution_space_improvement("hintgen/combined_data/" + problem + ".csv", problem, keyword)

def run_canonical_space_reduction():
    problems = stats_problem_set
    log("problem\tnum_syntax_errors\tnum_semantic_errors\tnum_correct\t" + \
        "all_submissions\tall_source_states\tall_cleaned_states\tall_anon_states\tall_canonical_states\t" + \
        "correct_submissions\tcorrect_source_states\tcorrect_cleaned_states\tcorrect_anon_states\tcorrect_canonical_states\n", "bug")
    for problem_name in problems:
        problem = Problem.objects.get(name=problem_name)
        clear_solution_space(problem)
        exact_text = { }
        correct_exact_text = { }
        last_seen = { }

        table = parse_table("hintgen/combined_data/" + problem_name + ".csv")
        header = table[0]
        table = table[1:]
        student_index = header.index("student_id")
        code_index = header.index("fun")
        for i in range(len(table)):
            line = table[i]
            student_name = line[student_index]
            code = line[code_index]
            if i > 0 and student_name in last_seen and \
                last_seen[student_name] == code:
                continue # skip for now
            students = Student.objects.filter(name=student_name)
            if len(students) == 1:
                student = students[0]
            else:
                student = Student(course=course, name=student_name)
                student.save()

            state = SourceState(code=code, problem=problem, count=1, student=student)
            state = run_tests(state)
            state.save()
            last_seen[student_name] = code
            if state.tree != None:
                if code in exact_text:
                    exact_text[code] += 1
                else:
                    exact_text[code] = 1

                if state.score == 1:
                    if code in correct_exact_text:
                        correct_exact_text[code] += 1
                    else:
                        correct_exact_text[code] = 1
        for k in correct_exact_text:
            print(str(correct_exact_text[k]) + "\n" + k)

        source_states = SourceState.objects.filter(problem=problem)
        syntax_errors = source_states.filter(treeWeight__isnull=True)
        semantic_errors = source_states.filter(score__lt=1, treeWeight__isnull=False)
        correct_states = source_states.filter(score=1)

        cleaned_states = CleanedState.objects.filter(problem=problem, treeWeight__isnull=False)
        correct_cleaned_states = cleaned_states.filter(score=1)
        anon_states = AnonState.objects.filter(problem=problem, treeWeight__isnull=False)
        correct_anon_states = anon_states.filter(score=1)
        canonical_states = CanonicalState.objects.filter(problem=problem, treeWeight__isnull=False)
        correct_canonical_states = canonical_states.filter(score=1)

        log(problem_name + "\t" + str(len(syntax_errors)) + "\t" + str(len(semantic_errors)) + "\t" + str(len(correct_states)) + "\t" + \
            str(len(semantic_errors) + len(correct_states)) + "\t" + str(len(exact_text.keys())) + "\t" + str(len(cleaned_states)) + "\t" + str(len(anon_states)) + "\t" + str(len(canonical_states)) + "\t" + \
            str(len(correct_states)) + "\t" + str(len(correct_exact_text.keys())) + "\t" + str(len(correct_cleaned_states)) + "\t" + str(len(correct_anon_states)) + "\t" + str(len(correct_canonical_states)), "bug")

def import_code_as_states(f, course_id, problem_name, clear_space=False, run_profiler=False, run_hint_chain=False):
    if run_profiler:
        # Set up the profiler
        out = sys.stdout
        outStream = io.StringIO()
        sys.stdout = outStream
        pr = cProfile.Profile()
        pr.enable()

    course = Course.objects.get(id=course_id)
    problem = Problem.objects.get(name=problem_name)#course.problems.get(name=problem_name)

    if clear_space:
        clear_solution_space(problem)

    # Import a CSV file of code into the database
    table = parse_table(f)
    header = table[0]
    table = table[1:]
    results = ""
    for line in table:
        if line[0] == "0": # we already have the instructor solutions
            continue
        student_name = line[header.index("student_id")]
        students = Student.objects.filter(name=student_name)
        if len(students) == 1:
            student = students[0]
        else:
            student = Student(course=course, name=student_name)
            student.save()
        code = line[header.index("fun")]

        if run_hint_chain:
            start_time = time.time()
            result, step_count, syntax_edits, semantic_edits, start_state, goal_state = do_hint_chain(code, student, problem)
            end_time = time.time()
            results += str(line[header.index("id")]) + "\t" + str(start_state.score) + "\t" + str(end_time - start_time) + "\t" + \
                str(result) + "\t" + str(step_count) + "\t" + str(syntax_edits) + "\t" + str(semantic_edits) + "\n"
        else:
            start_time = time.time()
            state = SourceState(code=code, problem=problem, count=1, student=student)
            state = get_hint(state)
            state.save()
            end_time = time.time()
            results += str(line[header.index("id")]) + "\t" + str(state.score) + "\t" + str(end_time - start_time) + "\n"

    filename = LOG_PATH + problem_name + "_" + ("chain" if run_hint_chain else "results") + ".log"
    with open(filename, "w") as f:
        f.write(results)

    if run_profiler:
        # Check the profiler results
        sys.stdout = out
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        with open(LOG_PATH + problem_name + "_profile.log", "w") as f:
            f.write(outStream.getvalue() + s.getvalue())
    print('\a')

def generate_space(table, problem, keyword):
    # First, clear the solution space
    clear_solution_space(problem, keep_starter=False)

    header = table[0]
    starter = table[1]
    table = table[2:]

    # Add back in the starter code
    starter_state = SourceState(code=starter[header.index("fun")], problem=problem, count=1, student=Student.objects.get(id=1))
    starter_state = get_hint(starter_state)
    starter_state.save()
    problem.solution = starter_state
    problem.save()

    if keyword == "optimal":
        for line in table:
            code_id = line[header.index("id")]
            student_name = line[header.index("student_id")]
            students = Student.objects.filter(name=student_name)
            if len(students) == 1:
                student = students[0]
            else:
                student = Student(course=Course.objects.get(id=1), name=student_name)
                student.save()
            code = line[header.index("fun")]
            if int(code_id) % 10 == 0:
                log("Generating space: " + code_id, "bug")
            # Now for each piece of code, find the distance between that piece of code and the starter goal
            state = SourceState(code=code, problem=problem, count=1, student=student)
            state = get_hint(state)
            state.save()

def run_solution_space_improvement(f, problem_name, keyword):
    problem = Problem.objects.get(name=problem_name)
    table = parse_table(f)
    generate_space(table, problem, keyword)

    last_state = State.objects.latest('id')
    all_info = "id,correct_states,all_states,syntax_edit_weight,edit_weight,state_weight,goal_weight\n"
    correct_states = 1
    all_states = 1

    if keyword == "optimal":
        all_states = len(SourceState.objects.filter(problem=problem))
        correct_states = len(SourceState.objects.filter(problem=problem, score=1))

    header = table[0]
    table = table[2:]

    if keyword == "random":
        random.shuffle(table)

    for i in range(len(table)):
        line = table[i]
        code_id = line[header.index("id")]
        student_name = line[header.index("student_id")]
        students = Student.objects.filter(name=student_name)
        if len(students) == 1:
            student = students[0]
        else:
            student = Student(course=Course.objects.get(id=1), name=student_name)
            student.save()
        code = line[header.index("fun")]
        if i % 10 == 0:
            log("Checking distance: " + str(i), "bug")

        result, step_count, syntax_edits, semantic_edits, start_state, goal_state = do_hint_chain(code, student, problem)
        start_weight = diffAsts.getWeight(start_state)
        goal_weight = diffAsts.getWeight(goal_state) if goal_state != None else -1
        goal_code = goal_state.code if goal_state != None else ""
        all_info += str(code_id) + "," + str(correct_states) + "," + \
                    str(all_states) + "," + str(syntax_edits) + \
                    "," + str(semantic_edits) + "," + str(start_weight) + \
                    "," + str(goal_weight) + "," + '"' + start_state.code + \
                    '"' + "," + '"' + goal_code + '"' + "," + "\n"

        if keyword == "random":
            # Update the counts
            if start_state.score == 1:
                correct_states += 1
            all_states += 1
        else:
            # And after that, clear out all new states, unless we're building a space
            new_states = State.objects.filter(id__gt=last_state.id)
            new_states.delete()

    with open(LOG_PATH + problem_name + "_" + keyword + ".csv", "w") as f:
        f.write(all_info)
    print('\a')