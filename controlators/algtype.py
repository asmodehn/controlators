from __future__ import annotations

import warnings
from collections import _tuplegetter
from typing import NamedTuple, NamedTupleMeta
import unittest

import typing


class AlgType(type):

    def __new__(mcls, typename: str, bases: typing.Optional[typing.Tuple] = None, attrs: typing.Optional[typing.Dict] = None):
        # although unused here, 'bases' is needed to be compatible with metaclass usage.

        if attrs is None:
            attrs = {}

        if bases is not None and len(bases) >0:
            warnings.warn("'bases' argument should be empty for proper Algebraic Types. Only typing.NamedTuple will be used for implementation.")
            # TODO : make warning point to user callsite...

            type_arr = [type(x) for x in bases]
            for i in type_arr:
                if i is AlgType:
                    raise RuntimeError("You cannot subclass a AlgType class")

        # deducting annotations from attrs if needed
        # to unify the dynamic_call and metaclass behavior: default value instead of immutable constant
        annotations = attrs.get("__annotations__", {})
        for n, a in attrs.items():
            # CAREFUL with "__*" special case !
            if not n.startswith("__") and n not in annotations:
                # attempt to deduce type if there is a default value
                annotations[n] = type(a)
                # on Error : set to typing.Any
                # TODO
        attrs.setdefault("__annotations__", {})  # set if needed
        attrs["__annotations__"].update(annotations)

        # delegate to a namedtuple (to not have to mess around with inheritance and more metaclasses)
        ntt = NamedTupleMeta.__new__(NamedTupleMeta, typename, bases, attrs)

        # retrieve annotations from namedtuple since they might have been processed once more than the ones we have here
        attrs.get('__annotations__', {}).update(ntt.__annotations__)

        # encapsulating namedtuple among attributes, overriding attrs with same name
        #  => we want the "default" semantic over the "class constant" semantic...
        tdict = {'_namedtuple_': ntt, **attrs, **{
            # accessing tuplegetters via property (careful to bind f properly here!)
            f: property(lambda s, ff=f: getattr(s._namedtuple_, ff))
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

    def __init__(self, typename: str, bases: typing.Optional[typing.Tuple] = None, attrs: typing.Optional[typing.Dict] = None):
        # Just to allow keyword arguments
        super(AlgType, self).__init__(typename, bases, attrs)

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

    def __add__(self, other: AlgType):
        " Categorical Product "
        newattrs = {
            **self._namedtuple_._field_defaults,
            **other._namedtuple_._field_defaults,
            '__annotations__': {
                **self.__annotations__,
                **other.__annotations__
            }
        }

        PT = AlgType(self.__name__ + other.__name__, attrs=newattrs)
        return PT

    def __sub__(self, other: AlgType):
        raise NotImplementedError


class TestAlgType(unittest.TestCase):

    def instantiation(self, cls):
        # test instantiation pos
        inst = cls(51)
        assert inst.attr == 51

        # test instantiation keyword
        inst = cls(attr=51)
        assert inst.attr == 51

        # test instantiation default
        inst = cls()
        assert inst.attr == 42

        # TODO : test typecheck (mypy ?)

    # TODO : hypothesis
    def test_algtype_dyncall(self):

        AT = AlgType("TestType", attrs={
            'attr': 42  # default semantics ! as for named tuple! inferring type from value...
        })

        assert type(AT) is AlgType
        assert AT.__annotations__['attr'] == int
        # TODO : asserting signature of __new__

        self.instantiation(AT)

    def test_algtype_metaclass(self):

        class MyTestClass(metaclass=AlgType):
            attr: int = 42

        assert type(MyTestClass) is AlgType
        assert MyTestClass.__annotations__['attr'] == typing.ForwardRef('int')  # WHY NOT int type ? because nested class ??
        # TODO : asserting signature of __new__

        self.instantiation(MyTestClass)

        # TODO : test typecheck (mypy ?)

    def test_algtype_add(self):

        AT = AlgType("AType", attrs={
            'attr': 42  # default
        })

        BT = AlgType("BType", attrs={
            'bttr': 51,  # default
            '__annotations__': {'bttr': float}  # hint, not enforced !
        })

        ABT = AT + BT
        assert type(ABT) is AlgType
        assert ABT.__annotations__['attr'] == int
        assert ABT.__annotations__['bttr'] == float

        # test instantiation pos
        inst = ABT(51)
        assert inst.attr == 51  #set value
        assert inst.bttr == 51  # default

        # test instantiation keyword
        inst = ABT(bttr=42)
        assert inst.attr == 42  # default
        assert inst.bttr == 42  # set value

        # test instantiation default
        inst = ABT()
        assert inst.attr == 42
        assert inst.bttr == 51

        # TODO : test typecheck (mypy ?)


if __name__ == '__main__':
    unittest.main()
