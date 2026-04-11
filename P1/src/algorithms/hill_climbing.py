import random
from classes import Library


def cal_score(solution: list[Library], deadline: int) -> int:
    scanned_books = set()
    t = 0
    score = 0
    i = 0

    while i < len(solution):
        current_lib = solution[i]
        t += current_lib.sign_up_time

        if t >= deadline:
            break

        days_available = deadline - t
        total_scannable = days_available * current_lib.shipping_cap
        f_books = [b for b in current_lib.books if b.id not in scanned_books]
        newly_scanned = f_books[:total_scannable]
        scanned_books.update(book.id for book in newly_scanned)
        score += sum(b.score for b in newly_scanned)
        i += 1

    return score


def hill_climbing(libraries: list[Library], deadline: int, max_iter: int = 100, stop_requested=None):
    #Hill Climbing default , cria um vizinho e aceita se for melhor
    if not libraries:
        return [], 0

    cur = gen_first_random(libraries, deadline)
    cur_score = cal_score(cur, deadline)
    best = cur[:]
    best_score = cur_score

    for _ in range(max_iter):
        if stop_requested and stop_requested():
            break
        ngh = random_neighbor(cur)
        ngh_score = cal_score(ngh, deadline)

        if ngh_score > cur_score:
            cur = ngh
            cur_score = ngh_score

            if cur_score > best_score:
                best = cur[:]
                best_score = cur_score

    return best, best_score


def stochastic_hill_climbing(libraries: list[Library], deadline: int, it: int, candidates: int = 5, stop_requested=None):
    #Cria vários vizinhos  melhores e escolhe um atoa
    if not libraries:
        return [], 0

    cur = gen_first_random(libraries, deadline)
    cur_score = cal_score(cur, deadline)
    best = cur[:]
    best_score = cur_score

    for _ in range(it):
        if stop_requested and stop_requested():
            break
        uphill = []
        for _ in range(candidates):
            if stop_requested and stop_requested():
                break
            neighbor = random_neighbor(cur)
            neighbor_score = cal_score(neighbor, deadline)
            if neighbor_score > cur_score:
                uphill.append((neighbor, neighbor_score))

        if uphill:
            #Pega num vizinho melhor atoa
            cur, cur_score = random.choice(uphill)

            if cur_score > best_score:
                best = cur[:]
                best_score = cur_score

    return best, best_score


def first_choice_hill_climbing(libraries: list[Library], deadline: int, max_no_improvement: int = 100, stop_requested=None):
    #Gera vizinhos e aceita melhores , para quando nao haver mais melhorias 
    if not libraries:
        return [], 0

    cur = gen_first_random(libraries, deadline)
    cur_score = cal_score(cur, deadline)
    best = cur[:]
    best_score = cur_score

    no_improvement = 0

    while no_improvement < max_no_improvement:
        if stop_requested and stop_requested():
            break
        neighbor = random_neighbor(cur)
        neighbor_score = cal_score(neighbor, deadline)

        if neighbor_score > cur_score:
            cur = neighbor
            cur_score = neighbor_score
            no_improvement = 0 

            if cur_score > best_score:
                best = cur[:]
                best_score = cur_score
        else:
            no_improvement += 1

    return best, best_score


def random_restart_hill_climbing(libraries: list[Library], deadline: int, restarts: int = 10, max_iter: int = 1000, stop_requested=None):
    
    #Isto so corre o hill climbing varias vezes e escolhe o melhor
    global_best = None
    global_best_score = 0

    for _ in range(restarts):
        if stop_requested and stop_requested():
            break

        solution, score = hill_climbing(libraries, deadline, max_iter, stop_requested=stop_requested)

        if score > global_best_score:
            global_best = solution
            global_best_score = score

    return global_best, global_best_score


def insert_move(solution):
    neighbor = solution.copy()
    i, j = random.sample(range(len(neighbor)), 2)
    lib = neighbor.pop(i)
    neighbor.insert(j, lib)
    return neighbor


def reverse_segment(solution):
    neighbor = solution.copy()
    i, j = sorted(random.sample(range(len(neighbor)), 2))
    neighbor[i:j] = reversed(neighbor[i:j])
    return neighbor


def swap(solution: list[Library]) -> list[Library]:
    neighbor = solution.copy()
    idxa, idxb = random.sample(range(len(neighbor)), 2)
    neighbor[idxa], neighbor[idxb] = neighbor[idxb], neighbor[idxa]
    return neighbor


def random_neighbor(solution):
    move = random.choice(["swap", "insert", "reverse"])
    if move == "swap":
        return swap(solution)
    elif move == "insert":
        return insert_move(solution)
    else:
        return reverse_segment(solution)


def gen_first_random(all_libraries: list[Library], deadline: int) -> list[Library]:
    ans = []
    t = 0
    shuffled = all_libraries.copy()
    random.shuffle(shuffled)
    for lib in shuffled:
        if t >= deadline:
            break
        if t + lib.sign_up_time <= deadline:
            ans.append(lib)
            t += lib.sign_up_time

    if not ans:
        return shuffled

    return ans