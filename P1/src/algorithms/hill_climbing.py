import os
import sys #patch para correr 
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import file_parser
import random
from classes import Library,Book
#Podiamos implementar Stochastic Hill climing e First-Choice hill climbing e random.restart


all_books, all_libraries, deadline= file_parser.parse_file("a_example.in")


def cal_score(l1:list)->int:
    scanned_books = set()
    t = 0
    score = 0
    i = 0

    while i < len(l1):
        current_lib = l1[i]
        t += current_lib.sign_up_time

        if t >= deadline:
            break

        days_available = deadline - t
        total_scannable = days_available * current_lib.shipping_cap
        f_books = [b for b in current_lib.books if b not in scanned_books]
        newly_scanned = f_books[:total_scannable] #A logica é temos x dias disponiveis para ler x*capaicdade de livraria ,e os livros ja estao por ordem de valor logo ficamos com os melhores livros
        scanned_books.update(newly_scanned)
        score += sum(b.score for b in newly_scanned)
        i += 1
    
    return score

#Maneira de chegar a um neighbor
def swap(lst):
    lst=lst.copy()
    idxa=random.randint(0,len(lst)-1)
    idxb=random.randint(0,len(lst)-1)
    while idxa==idxb:
        idxb=random.randint(0,len(lst)-1)
  
    lst[idxa], lst[idxb] = lst[idxb], lst[idxa]
    print(lst)
    return lst


def genFirstRandom()->list:#Podiamos meter greedy choice
    ans=[]
    t=0
    shuffled=all_libraries.copy()
    random.shuffle(shuffled)
    print(shuffled)
    for lib in shuffled:
        if t>=deadline:
            break
        if t+lib.sign_up_time<=deadline:
            ans.append(lib)
            t+=lib.sign_up_time
    print(f"First sOL{ans}")
    return ans


#nos podemos dar swap, 
#lista de livrarias por ordem de signup,ler livros que nao tenham sido scaned por ordem de valor 
#TEMPORARIO
def hill_climbing():
    cur=genFirstRandom()
    score=cal_score(cur)
    i=0
    while True and i<100:
        ngh=swap(cur)
        ngh_cr=cal_score(ngh)
        if ngh_cr>score:
            cur=ngh
            score=ngh_cr
        i+=1
    print(f"Score {score}")
    return cur,score

hill_climbing()