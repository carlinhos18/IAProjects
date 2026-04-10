import random
from classes import Library

#heuristica para a selecao
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


#criar indivios para testar
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


def create_pop(libraries, deadline, pop_size):
    return [create_individual(libraries,deadline) for _ in range(pop_size)]




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



def selection(population, fitness_list, n=5):
    #escolher n elementos aleatorios para aumentar a diversidade genetica
    #depois escolhemos os melhor entre esses n
    n = min(n, len(population))
    indeces = random.sample(range(len(population)), n)
    best_index = max(indeces, key=lambda i: fitness_list[i])
    return population[best_index]


#troca de genes
#TODO talvez usar um set para reduzir a carga de trabalho feita aqui

def crossover(parent1, parent2):
    size = len(parent1)
    if size < 2:
        return parent1[:]

    #escolher 2 valores para por o genes do primeiro parent 
    a,b = sorted(random.sample(range(size),2))
    
    child = [None] * size 
    child[a:b] = parent1[a:b]
    child_libs = set(lib.id for lib in parent1[a:b])

    #so queremos mudar os Nones
    pointer = 0

    for lib in parent2:
        #if lib not in child:
        if lib.id not in child_libs:
            while child[pointer] is not None:
                pointer+=1
            child[pointer] = lib 
            child_libs.add(lib.id)

    return child
            


#mutacoes com uma chance que definimos para causar mais possibilidades de encontrar a melhor solucao
def mutation(individual, mutation_rate=0.03):
    if len(individual) < 2:
        return

    if random.random() > mutation_rate:
        return
    mutation_pool = ['swap', 'reverse', 'insertion']
    mutation_gene = random.choice(mutation_pool)

    if mutation_gene == 'swap':
        a,b = random.sample(range(len(individual)),2)
        individual[a], individual[b] = individual[b], individual[a]
    
    elif mutation_gene == 'reverse':
        a,b = sorted(random.sample(range(len(individual)),2))
        individual[a:b] = individual[a:b][::-1]

    elif mutation_gene == 'insertion':
        a,b = random.sample(range(len(individual)),2)
        lib = individual.pop(a)
        individual.insert(b,lib)


def genetic_alg(libraries, deadline, pop_size=50,generations=100,mutation_rate=0.03,elite_individ = 5):
    if not libraries:
        return [], 0

    pop_size = max(1, pop_size)
    elite_individ = max(1, min(elite_individ, pop_size))
    
    population = create_pop(libraries,deadline,pop_size)

    best_solution = None
    best_score = -1 # Talvez mudar para 0? TODO para o futuro se necessario

    for _gen in range(generations):
        fitness_list = [fitness(individual,deadline) for individual in population]
        
        max_fitness = max(fitness_list)
        if max_fitness > best_score:
            best_solution = population[fitness_list.index(max_fitness)][:]#criar uma copia do elemento 
            best_score = max_fitness

        #escolher os mais aptos ate ao limite definido
        elite_indices = sorted(range(len(fitness_list)), key=lambda i:fitness_list[i], reverse=True)[:elite_individ] 
        
        new_pop = [population[i][:] for i in elite_indices]

        while(len(new_pop) < pop_size):
            parent1 = selection(population, fitness_list)
            parent2 = selection(population, fitness_list)
            child = crossover(parent1, parent2)
            mutation(child,mutation_rate)
            new_pop.append(child)

        population = new_pop

    return best_solution, best_score
            
        





