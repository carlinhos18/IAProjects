import os
import sys #patch para correr ,depois tirar
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import file_parser
import random
from classes import Library,Book

all_books, all_libraries, deadline= file_parser.parse_file("a_example.in")


def cal_score(l1:list)->int:
    scanned_books = set()
    t = 0
    score = 0
    i = 0
    dictionary={}
    while i < len(l1):
        current_lib = l1[i]
        t += current_lib.sign_up_time

        if t >= deadline:
            break

        rem_days = deadline - t
        nr_books = rem_days * current_lib.shipping_cap
        f_books = [b for b in current_lib.books if b not in scanned_books]
        new_scanned = f_books[:nr_books] #A logica é temos x dias disponiveis para ler x*capaicdade de livraria ,e os livros ja estao por ordem de valor logo ficamos com os melhores livros
        scanned_books.update(new_scanned)
        dictionary[current_lib]=new_scanned
        score += sum(b.score for b in new_scanned)
        i += 1
    
    return dictionary,score

#Maneira de chegar a um neighbor
def swap(lst):
    lst=lst.copy()
    idxa=random.randint(0,len(lst)-1)
    idxb=random.randint(0,len(lst)-1)
    while idxa==idxb:
        idxb=random.randint(0,len(lst)-1)
  
    lst[idxa], lst[idxb] = lst[idxb], lst[idxa]
    return lst


def genFirstRandom()->list:#Podiamos meter greedy choice
    ans=[]
    t=0
    shuffled=all_libraries.copy()
    random.shuffle(shuffled)
    for lib in shuffled:
        if t>=deadline:
            break
        if t+lib.sign_up_time<=deadline:
            ans.append(lib)
            t+=lib.sign_up_time

    return ans


#nos podemos dar swap, 
#lista de livrarias por ordem de signup,ler livros que nao tenham sido scaned por ordem de valor 

def hill_climbing_stochastic_choice(prob:float):
    cur=genFirstRandom()
    solution,score=cal_score(cur)
    i=0
    tries=0
    while tries<6: #pode dar loop
        ngh=swap(cur)
        dictionaryb,ngh_cr=cal_score(ngh)
        if ngh_cr>score:
            cur=ngh
            score=ngh_cr
            solution=dictionaryb
            tries=0
        elif random.random()<prob:
            cur=ngh
            score=ngh_cr
            tries+=1
        else:
            tries+=1
        i+=1

    return solution,score

def hill_climbing_first_choice():
    cur=genFirstRandom()
    solution,score=cal_score(cur)
    i=0
    tries=0
    while tries<6: #pode dar loop
        ngh=swap(cur)
        dic,ngh_cr=cal_score(ngh)
        if ngh_cr>score:
            cur=ngh
            score=ngh_cr
            tries=0
            solution=dic
        else:
            tries+=1
        i+=1

    return solution,score


def hill_climbing_random_restart(n:int):
    ans=0
    solution=dict()
    for i in range(n):
        dic,tmp=hill_climbing_first_choice()
        if ans<tmp:
            solution=dic
            ans=tmp

    return solution,ans


       


