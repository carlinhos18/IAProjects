import random
from classes import Library

# Podiamos implementar Stochastic Hill climing e First-Choice hill climbing e random.restart

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
        newly_scanned = f_books[:total_scannable]  # Os livros ja estao por score, pelo que lemos os melhores primeiro.
        scanned_books.update(book.id for book in newly_scanned)
        score += sum(b.score for b in newly_scanned)
        i += 1
    
    return score

def swap(solution: list[Library]) -> list[Library]:
    neighbor = solution.copy()
    idxa, idxb = random.sample(range(len(neighbor)), 2)
    neighbor[idxa], neighbor[idxb] = neighbor[idxb], neighbor[idxa]
    return neighbor


def gen_first_random(all_libraries: list[Library], deadline: int) -> list[Library]:  # Podiamos meter greedy choice
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


# nos podemos dar swap,
# lista de livrarias por ordem de signup, ler livros que nao tenham sido scanned por ordem de valor
def hill_climbing(libraries: list[Library], deadline: int, max_iter: int = 1000):
    if not libraries:
        return [], 0

    cur = gen_first_random(libraries, deadline)
    score = cal_score(cur, deadline)
    best = cur[:]
    best_score = score

    for _ in range(max_iter):
        ngh = swap(cur)
        ngh_score = cal_score(ngh, deadline)

        if ngh_score > score:
            cur = ngh
            score = ngh_score

            if score > best_score:
                best = cur[:]
                best_score = score

    return best, best_score
