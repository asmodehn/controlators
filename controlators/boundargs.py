"""
Hashable bounded args implementation
"""
import unittest
import inspect

import typing

from .algtype import AlgType


def frozen_arguments_type(typename: str, sig: inspect.Signature) -> typing.Type:

    args_defaults = {p: pp.default for p, pp in sig.parameters.items() if pp.default is not inspect.Parameter.empty}

    # if annotation is missing, we type with Any to have it settable on construction.
    # NamedTuple behavior is to turn non-hinted attributes into constants
    args_hints = {p: pp.annotation if pp.annotation is not inspect.Parameter.empty else typing.Any for p, pp in sig.parameters.items()}

    argtype = AlgType(f"{typename}", attrs={
        **args_defaults,
        '__annotations__': args_hints
    })
    return argtype


def freeze_arguments(signature: inspect.Signature, *args, **kwargs):
    # TODO : review usage...
    boundargs = signature.bind(*args, **kwargs)
    boundargs.apply_defaults()  # in case some arguments were omitted during the bind

    return


class TestHashableBoundArguments(unittest.TestCase):

    def test_frozen_arguments_type(self):

        def myfun(a: int, b: float = 42.0, c = 51):
            return a, b, c

        fat = frozen_arguments_type("TypeTest", sig=inspect.signature(myfun))

        assert isinstance(fat, AlgType)

        # instanciation
        myinst_dyn = fat(1, 2, 3)

        assert myinst_dyn.a == 1
        assert myinst_dyn.b == 2
        assert myinst_dyn.c == 3

        # the whole point
        hash(myinst_dyn)


if __name__ == '__main__':
    unittest.main()