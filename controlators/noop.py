from hypothesis import given
from hypothesis import strategies as st
import unittest


# control as a pure function
def noop(input):
    output = input
    return output


# decorator to turn a control function into a generator
def controlator(ctrl_fun):

    # first sent value has to be None to start the generator
    sent = None

    while True:
        recvd = yield sent
        sent = ctrl_fun(recvd)


class ControlTest(unittest.TestCase):

    @given(st.data())
    def test_noop(self, data):

        inputs = data.draw(st.lists(st.integers()))

        for i in inputs:
            # very basic property to test here...
            assert noop(i) == i

    @given(st.data())
    def test_noop_controller(self, data):

        inputs = data.draw(st.lists(st.integers()))

        ctrl = controlator(noop)
        ctrl.send(None)  # first None send
        for i in inputs:
            # very basic property to test here...
            assert ctrl.send(i) == i


if __name__ == '__main__':
    unittest.main()

