class Book:
    def __init__(self, id, score):
        self.id = id
        self.score = score
        
    def __repr__(self):
        return f"Book(id={self.id}, score={self.score})"