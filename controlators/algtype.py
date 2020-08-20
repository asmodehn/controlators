from __future__ import annotations

import warnings
from typing import NamedTupleMeta
import unittest

import typing


class AlgType(type):

    def __new__(mcls, typename: str, bases: typing.Optional[typing.Tuple] = None, attrs: typing.Optional[typing.Dict] = None):
        # although unused here, 'bases' is needed to be compatible with metaclass usage.

        if bases is not None and len(bases) >0:
            warnings.warn("'bases' argument should be empty for proper Algebraic Types. Only typing.NamedTuple will be used for implementation.")
            # TODO : make warning point to user callsite...

            type_arr = [type(x) for x in bases]
            for i in type_arr:
                if i is AlgType:
                    raise RuntimeError("You cannot subclass a AlgType class")

        if attrs is None:
            return Void  # no attributes == the Empty Type. name is ignored. #TODO : typevar maybe ? alias ?

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

        # TODO : currently small inconsistency when called dynamically or statically in the resolution of annotations
        #   one is ForwardRef, the other is not. calling get_type_hints fixes the problem however
        #   cf tests: check __annotations__ to see the problem.

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

    def __contains__(self, item):
        if isinstance(item, str):
            item = [item]
        return sum(i in self._namedtuple_._fields for i in item) == len(item)  # all True (False is 0)

    def __getitem__(self, item: typing.Union[str, list]) -> AlgType:  # a mapping to subtypes...
        th = typing.get_type_hints(self._namedtuple_)
        if isinstance(item, str):
            item = [item]

        if isinstance(item, list):
            if len(item) == 0:
                return Void
            elif item == list(self._namedtuple_._fields):
                return self
            else:
                annots = {}
                deflts = {}
                for i in item:
                    if i not in self._namedtuple_._fields:
                        raise TypeError(f"{i} is not a subtype of {self}")
                    else:
                        annots.update({i: th[i]})
                        deflts.update({i: self._namedtuple_._field_defaults[i]})

                return AlgType(f"{self.__name__}[{item}]", attrs={
                        **deflts,  # access default values and pass them
                        "__annotations__": annots
                    })

    def __iter__(self):
        for f in self._namedtuple_._fields:
            yield self[f]  # leveraging getitem

    def __eq__(self, other):
        return (self._namedtuple_._field_defaults == other._namedtuple_._field_defaults and
                typing.get_type_hints(self._namedtuple_) == typing.get_type_hints(other._namedtuple_))

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
        " Categorical Product. using + for similarity with nametuple append operator + "
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
        " removes a subtype."
        excludes = []
        for att_name in other._namedtuple_._fields:
            excludes.append(att_name)

        remain = [f for f in self._namedtuple_._fields if f not in excludes]

        return self[remain]


    # TODO : this is hacky. We should strive for a more "proper" type system... whenever time permits...


class Void(metaclass=AlgType):
    " The Empty Type"
    pass


class TestAlgType(unittest.TestCase):

    tested_type = None
    def setUp(self) -> None:
    # TODO : hypothesis to generate various types and test them all...

        class MyTestClass(metaclass=AlgType):
            attr: int = 42

        self.tested_type = MyTestClass

    def test_algtype_new(self):

        assert type(self.tested_type) is AlgType
        assert typing.get_type_hints(self.tested_type)['attr'] == int
        # TODO : asserting signature of __new__

        # test instantiation pos
        inst = self.tested_type(51)
        assert inst.attr == 51

        # test instantiation keyword
        inst = self.tested_type(attr=51)
        assert inst.attr == 51

        # test instantiation default
        inst = self.tested_type()
        assert inst.attr == 42

        # TODO : test typecheck (mypy ?)

    def test_algtype_add(self):

        # relying on dynamic type creation here...
        BT = AlgType("BType", attrs={
            'bttr': 51,  # default
            '__annotations__': {'bttr': float}  # hint, not enforced !
        })

        ABT = self.tested_type + BT
        assert type(ABT) is AlgType
        assert typing.get_type_hints(ABT)['attr'] == int
        assert typing.get_type_hints(ABT)['bttr'] == float

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

    def test_algtype_contains(self):
        assert 'attr' in self.tested_type
        assert 'what_is_this' not in self.tested_type

    def test_algtype_getitem(self):
        # property to access the data attribute in the instance
        assert isinstance(self.tested_type.attr, property)

        # however we can also access its type via Type[attribute_name]... which is the same as the current one (only one attr).
        assert self.tested_type['attr'] == self.tested_type

        with self.assertRaises(TypeError):
            self.tested_type['does_not_exist']

        #  we can also pass a list to get multiple attrs (tested more via __sub__)
        assert self.tested_type[['attr']] == self.tested_type

    def test_algtype_iter(self):
        for fT in self.tested_type:
            assert fT is self.tested_type  # only one attr ! -> we iterate on itself, only once.

    def test_eq(self):
        assert self.tested_type == self.tested_type

        # TODO: more tests !

    def test_algtype_sub(self):
        assert self.tested_type - self.tested_type is Void

        # TODO : more tests


class TestAlgTypeDynamic(TestAlgType):

    def setUp(self) -> None:
        # replacing tested_type with a dynamic one. but running same tests
        AT = AlgType("TestType", attrs={
            'attr': 42  # default semantics ! as for named tuple! inferring type from value...
        })

        self.tested_type = AT


if __name__ == '__main__':
    unittest.main()
