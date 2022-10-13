import random
import lists

words = list(lists.read_file_list("common words.txt"))
# printable ASCII except letters and digits
symbols = "!\"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"

while True:
    format = input("Format: ")
    pwd = ""
    for c in format:
        if c == "w":
            pwd += lists.random_from(words)
        elif c == "d":
            pwd += str(random.randint(0, 9))
        elif c == "s":
            pwd += lists.random_from(symbols)
        else:
            print(
                "May only input the characters w for word, d for digit, and s for symbol")
            break
    print(pwd)
