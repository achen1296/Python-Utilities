import random
from mypy import lists

words = list(lists.read_file_list("wordlist.txt"))
lw = len(words)

while True:
    num = int(input("Number of words: "))

    for _ in range(0, num):
        r = int(random.random() * lw)
        print(words[r])
