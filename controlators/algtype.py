from __future__ import annotations

import warnings
from collections import _tuplegetter
from typing import NamedTuple, NamedTupleMeta
import unittest

import typing


class AlgType(type):

    def __new__(mcls, typename: str, bases: typing.Optional[typing.Tuple] = None, attrs: typing.Optional[typing.Dict] = None):

        if attrs is None:
            attrs = {}

        if bases is not None and len(bases) >0:
            warnings.warn("'bases' argument should be empty for proper Algebraic Types. Only typing.NamedTuple will be used for implementation.")
            # TODO : make warning point to user callsite...

            type_arr = [type(x) for x in bases]
            for i in type_arr:
                if i is AlgType:
                    raise RuntimeError("You cannot subclass a AlgType class")

        # delegate to a namedtuple (to not have to mess around with inheritance and more metaclasses)
        ntt = NamedTupleMeta.__new__(NamedTupleMeta, typename, bases, attrs)

        # retrieve annotations from namedtuple since they might have been processed once more than the ones we have here
        attrs['__annotations__'].update(ntt.__annotations__)

        # encapsulating namedtuple among attributes, overriding attrs with same name
        #  => we want the "default" semantic over the "class constant" semantic...
        tdict = {'_namedtuple_': ntt, **attrs, **{
            f: property(lambda s: getattr(s._namedtuple_, f))  # accessing tuplegetters via property
            for f in ntt._fields
        }}

        kls = super(AlgType, mcls).__new__(mcls, typename, (), tdict)

        def inst_new(cls, *args, **kwargs):
            inst = super(kls, cls).__new__(cls)

            inst._namedtuple_ = cls._namedtuple_(*args, **kwargs)

            return inst

        # hacking new signature like typing.NamedTuple does...
        inst_new.__annotations__ = dict(attrs.get('__annotations__', {}))
        inst_new.__defaults__ = tuple(attrs[f] for f in kls._namedtuple_._fields if f in attrs)

        kls.__new__ = inst_new
        return kls

    # def __call__(self, *args, **kwargs):
    #     # instantiation
    #
    #     inst = self.__new__(self)  # instantiating the actual class
    #
    #     # instantiating the internal nametuple on the instance, replacing the attribute
    #     inst._namedtuple_ = inst._namedtuple_(*args, **kwargs)
    #
    #     inst.__init__()  # initializing
    #
    #     return inst

    def append(self, other: AlgType):
        " Categorical Product "
        dict = {
            **self._field,
            **other._fields,
            '__annotations__': {
                **self.__annotations__,
                **other.__annotations__
            }
        }

        PT = AlgType(name=self.__name__ + other.__name__, dict=dict)
        return PT

    def __sub__(self, other: AlgType):
        raise NotImplementedError


class TestAlgType(unittest.TestCase):

    # TODO : hypothesis
    # def test_algtype_dyncall(self):
    #
    #     AT = AlgType("TestType", dict={
    #         'attr': 42  # constant
    #     })
    #
    #     assert type(AT) is AlgType
    #     assert AT.attr == 42

    def test_algtype_metaclass(self):

        class MyTestClass(metaclass=AlgType):
            attr: int = 42

        assert type(MyTestClass) is AlgType
        assert MyTestClass.__annotations__['attr'] == typing.ForwardRef('int')  # WHY NOT int type ? because nested class ??
        # TODO : asserting signature of __new__

        # test instantiation pos
        inst = MyTestClass(51)
        assert inst.attr == 51

        # test instantiation keyword
        inst = MyTestClass(attr=51)
        assert inst.attr == 51

        # test instantiation default
        inst = MyTestClass()
        assert inst.attr == 42

        # TODO : test typecheck (mypy ?)

    # def test_algtype_append(self):
    #
    #     AT = AlgType("AType", dict={
    #         'attr': 42  # constant
    #     })
    #
    #     BT = AlgType("AType", dict={
    #         'bttr': 51.0,  # constant
    #         '__annotations__': {'bttr': float}
    #     })
    #
    #     ABT = AT.append(BT)
    #     assert type(ABT) is AlgType
    #     assert AT.attr == 42

if __name__ == '__main__':
    unittest.main()