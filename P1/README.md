## To run our app:

```bash
cd P1
pip install -r requirements.txt
python main.py
```

- Library:
    - set of books (book 0, book 1, book2, ...).
    - time it takes in days to sign the library for scanning.
    - number of books that can be scanned each day.

- Only one library at a time can be going through the signup process and it is not parallel between libraries.


class Library:
    def __init__(self, id, books, signup_days, books_per_day):
        self.id = id                          
        self.books = books                   
        self.signup_days = signup_days       
        self.books_per_day = books_per_day 

    def __repr__(self):
        return f"Library(id={self.id}, books={len(self.books)}, signup={self.signup_days}, rate={self.books_per_day})"

class Book:
    def __init__(self, id, score):
    self.id = id
    self.score = score


dick = {
    0: 1,
    1: 2,
    2: 3,
    3: 6,
    4: 5,
    5: 4
}

lib = Library