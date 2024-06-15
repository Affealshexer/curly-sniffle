import time


def func(*args, jonas=False):
    print(args, jonas)

func("x", 98, 99999, 110, True, jonas=True)

input()

class context_manager_example:
    def __enter__(self):
        print("ENDEAR")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("exit")


try:
    j = context_manager_example()
    j.__enter__()

    # Stuff
    time.sleep(1)
finally:
    j.__exit__("", "", "")


with context_manager_example() as j:
    time.sleep(1)
print("DONE")
