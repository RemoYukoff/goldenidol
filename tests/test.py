import sys

from goldenrun.tracing import record


class TestClass:
    def __init__(self, arg1, arg2) -> None:
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg1 + arg2


def function_a(arg1, arg2):
    print(f"arg1:{arg1} function_a")
    testclass = function_b(arg1, arg2)
    print(f"arg4:{testclass.arg3} function_a")


@record
def function_b(arg2, arg3):
    print(f"arg2:{arg2} function_b")
    print(f"arg3:{arg3} function_b")
    return TestClass(arg2, arg3)


if __name__ == "__main__":
    function_a(int(sys.argv[1]), int(sys.argv[2]))
