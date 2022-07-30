from tkinter.tix import MAX
import web

from selenium import webdriver


def steam_friends(driver: webdriver.Firefox, steam_profile: str):
    driver.get(steam_profile + "/friends")
    friends = driver.find_elements(By.CSS_SELECTOR, ("a.selectable_overlay")
    return [f.get_attribute("href") for f in friends]


if __name__ == "__main__":
    # BFS of the friend network from both sides until a connection is found

    p1=input("Person 1: ")
    next_queue1=[p1]
    friends1={p1: "root"}

    p2=input("Person 2: ")
    next_queue2=[p2]
    friends2={p2: "root"}

    degrees=0
    MAX_DEGREES=5

    driver=web.firefox_driver()

    while True:
        if degrees == MAX_DEGREES:
            print(friends1)
            print(friends2)
            break
        degrees += 1

        print(f"degree {degrees} friends of {p1}")
        queue1=next_queue1
        next_queue1=[]
        for person in queue1:
            friends=steam_friends(driver, person)
            for f in friends:
                if f not in friends1:
                    friends1[f]=person
                    next_queue1.append(f)
                # else: found some other way from the same starting person
        print(next_queue1)

        print(f"degree {degrees} friends of {p2}")
        queue2=next_queue2
        next_queue2=[]
        for person in queue2:
            friends=steam_friends(driver, person)
            for f in friends:
                if f not in friends2:
                    friends2[f]=person
                    next_queue2.append(f)
        print(next_queue2)

        intersection=set(friends1) & set(friends2)

        if len(intersection) > 0:
            for f in intersection:
                shared_friend=f
            print(shared_friend)
            f=shared_friend
            while True:
                f=friends1[f]
                print(f"-> {f}", end="")
                if f == p1:
                    break
            f=shared_friend
            while True:
                f=friends2[f]
                print(f"-> {f}", end="")
                if f == p2:
                    break
            break
