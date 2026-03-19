import os
from classes import  Book,Library

def parse_file(filename):
    base_dir = os.path.dirname(__file__) 
    filepath = os.path.join(base_dir, '..', 'input', filename) ##tirar quando chamar-mos na main. Assim podemos chamar nos algoritmos para teste
    with open(filepath) as f:
        #Esta linha diz-nos os parametros do problema
        nr_books, nr_libs, deadline = map(int, f.readline().split())
        # a segunda diz os scores ordenados por indice
        scores = list(map(int, f.readline().split()))
        all_books = [Book(i, scores[i]) for i in range(nr_books)]
        #desta forma criamos os livros todos e depois damos apend na biblioteca
        all_libraries = []
        for i in range(nr_libs):
            lib_line = f.readline().split()
            _, signup, ship_cap = map(int, lib_line) #nao usamos o primeiro valor
            
            book_ids = list(map(int, f.readline().split()))
            #talvez haja maneira melhor
            books_in_this_lib = [all_books[bid] for bid in book_ids]
            lib = Library(i, signup, ship_cap, books_in_this_lib)
            all_libraries.append(lib)
     
    return all_books, all_libraries, deadline
