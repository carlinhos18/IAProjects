import random
import math
from classes import Library



def heuristic(lib:Library, deadline:int, curr_day:int, books_scanned):
    days_left = deadline - curr_day - lib.sign_up_time
    #se nao da para dar o sign up, cortamos o path
    if days_left <= 0:
        return -1


    max_books = days_left * lib.shipping_cap

    unique_books = sorted(
        (book for book in lib.books if book.id not in books_scanned),
        key=lambda book: book.score,
        reverse=True 
        )[:max_books]
    # se nao ha livros, cortamos o path
    if not unique_books:
        return -1

    score = sum(book.score for book in unique_books)
    return score


def create_individual(libraries, deadline):
    libraries_left = list(libraries)
    curr_day = 0
    books_scanned = set()
    ordered = []

    #loop para escolher a ordem das bibliotecas
    while libraries_left:
        scored = [
            (lib, heuristic(lib,deadline,curr_day,books_scanned)) for lib in libraries_left
        ]
        # queremos tirar as bibliotecas em que a heuristica devolve -1 essencialmente
        scored = [(lib,score) for lib,score in scored if score >0]
        if not scored:
            break

        scored.sort(key=lambda x:x[1], reverse=True)
        #escolher uma aleatoria do 20% melhores, depois posso passar isso como argumento para testar diferentes resultados        
        top_choice = max(1,len(scored)//5)
        chosen_lib = random.choice(scored[:top_choice])[0]

        ordered.append(chosen_lib)
        libraries_left.remove(chosen_lib)

        #TODO: Veridificar se esta logica nao pode ser alterada que como os livros ja vem na biblioteca nao deve ser preciso
        curr_day+= chosen_lib.sign_up_time
        max_books = (deadline - curr_day)*chosen_lib.shipping_cap
        count =0
        for book in chosen_lib.books:
            if book.id not in books_scanned:
                books_scanned.add(book.id)
                count+=1
                if count >=max_books:
                    break

        
        

    random.shuffle(libraries_left)
    return ordered + libraries_left


def fitness(individual, deadline):
    curr_day =0
    books_scanned = set()
    total_lib_score = 0
    
    for lib in individual:
        curr_day +=lib.sign_up_time
        if curr_day >= deadline:
            break
        days_left = deadline - curr_day
        max_books = days_left * lib.shipping_cap

        count = 0
        for book in lib.books:
            if book.id not in books_scanned:
                books_scanned.add(book.id)
                total_lib_score += book.score 
                count +=1
                if count >= max_books:
                    break

    return total_lib_score

def get_neighbor(solution):
    neighbor = solution[:]
    if len(solution) < 2:
        return neighbor

    choice = random.choice(['swap', 'reverse'])

    if choice == 'swap':
        a, b = random.sample(range(len(solution)), 2)
        neighbor[a], neighbor[b] = neighbor[b], neighbor[a]

    elif choice == 'reverse':
        a, b = sorted(random.sample(range(len(solution)), 2))
        neighbor[a:b] = list(reversed(neighbor[a:b]))

    return neighbor

def simulated_annealing(libraries, deadline, 
                        initial_temp=1000, 
                        cooling_rate=0.995, 
                        min_temp=1e-3,
                        max_iter=10000):
    if not libraries:
        return [], 0

    current_solution = create_individual(libraries, deadline)
    current_score = fitness(current_solution, deadline)

    best_solution = current_solution[:]
    best_score = current_score

    T = initial_temp

    for i in range(max_iter):
        if T < min_temp:
            break

        # gerar vizinho
        neighbor = get_neighbor(current_solution)
        neighbor_score = fitness(neighbor, deadline)

        delta = neighbor_score - current_score

        # decidir aceitar
        if delta > 0:
            accept = True
        else:
            prob = math.exp(delta / T)
            accept = random.random() < prob

        if accept:
            current_solution = neighbor
            current_score = neighbor_score

            if current_score > best_score:
                best_solution = current_solution[:]
                best_score = current_score

        # arrefecimento
        T *= cooling_rate

    return best_solution, best_score