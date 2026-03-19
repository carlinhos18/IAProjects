class Library:
    def __init__(self, id, books, signup_days, books_per_day):
        self.id = id                          
        self.books = books                   
        self.signup_days = signup_days       
        self.books_per_day = books_per_day 

    def __repr__(self):
        return f"Library(id={self.id}, books={len(self.books)}, signup={self.signup_days}, rate={self.books_per_day})"