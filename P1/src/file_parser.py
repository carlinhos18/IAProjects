from classes import Book, Library

def parse_file(filepath):
    if not filepath:
        raise ValueError('No input file path provided')

    with open(filepath, 'r') as f:
        header = f.readline().split()
        if len(header) != 3:
            raise ValueError('Invalid input file header')

        nr_books, nr_libs, deadline = map(int, header)
        scores = list(map(int, f.readline().split()))
        if len(scores) != nr_books:
            raise ValueError('Number of scores does not match number of books')

        all_books = [Book(i, scores[i]) for i in range(nr_books)]
        
        all_libraries = []
        for i in range(nr_libs):
            lib_line = f.readline().split()
            if not lib_line:
                break

            _, signup, ship_cap = map(int, lib_line)
            
            book_ids = list(map(int, f.readline().split()))
            if any(bid < 0 or bid >= nr_books for bid in book_ids):
                raise ValueError(f'Invalid book id in library {i}')

            books_in_this_lib = [all_books[bid] for bid in book_ids]
            # Ordenar logo os livros por score para otimizar os algoritmos
            books_in_this_lib.sort(key=lambda x: x.score, reverse=True)
            
            lib = Library(i, signup, ship_cap, books_in_this_lib)
            all_libraries.append(lib)
     
    return all_books, all_libraries, deadline