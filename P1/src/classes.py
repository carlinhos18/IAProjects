#Sujeito a mudar, 
class Book:
    def __init__(self,id:int,score:int):
        self.id=id
        self.score=score
  
class Library:
    def __init__(self,id:int,sign_up_time:int,shipping_cap:int,books):
        self.id=id
        self.books=[]
        self.sign_up_time=sign_up_time
        self.shipping_cap=shipping_cap
        #assim quando iterarmos vai já estar melhor custo
        self.books = sorted(books, key=lambda x: x.score, reverse=True)