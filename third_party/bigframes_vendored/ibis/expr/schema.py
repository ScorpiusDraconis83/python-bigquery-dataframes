# Contains code from https://github.com/ibis-project/ibis/blob/9.2.0/ibis/expr/schema.py

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any, TYPE_CHECKING, Union

from bigframes_vendored.ibis.common.annotations import attribute
from bigframes_vendored.ibis.common.collections import FrozenOrderedDict, MapSet
from bigframes_vendored.ibis.common.dispatch import lazy_singledispatch
from bigframes_vendored.ibis.common.exceptions import InputTypeError, IntegrityError
from bigframes_vendored.ibis.common.grounds import Concrete
from bigframes_vendored.ibis.common.patterns import Coercible
import bigframes_vendored.ibis.expr.datatypes as dt
from bigframes_vendored.ibis.util import indent

if TYPE_CHECKING:
    from typing import TypeAlias


class Schema(Concrete, Coercible, MapSet):
    """An ordered mapping of str -> [datatype](./datatypes.qmd), used to hold a [Table](./expression-tables.qmd#ibis.expr.tables.Table)'s schema."""

    fields: FrozenOrderedDict[str, dt.DataType]
    """A mapping of [](`str`) to
    [`DataType`](./datatypes.qmd#ibis.expr.datatypes.DataType)
    objects representing the type of each column."""

    def __repr__(self) -> str:
        space = 2 + max(map(len, self.names), default=0)
        return "ibis.Schema {{{}\n}}".format(
            indent(
                "".join(
                    f"\n{name.ljust(space)}{type!s}" for name, type in self.items()
                ),
                2,
            )
        )

    def __rich_repr__(self):
        for name, dtype in self.items():
            yield name, str(dtype)

    def __len__(self) -> int:
        return len(self.fields)

    def __iter__(self) -> Iterator[str]:
        return iter(self.fields)

    def __getitem__(self, name: str) -> dt.DataType:
        return self.fields[name]

    @classmethod
    def __coerce__(cls, value) -> Schema:
        if isinstance(value, cls):
            return value
        return schema(value)

    @attribute
    def names(self):
        return tuple(self.keys())

    @attribute
    def types(self):
        return tuple(self.values())

    @attribute
    def _name_locs(self) -> dict[str, int]:
        return {v: i for i, v in enumerate(self.names)}

    def equals(self, other: Schema) -> bool:
        """Return whether `other` is equal to `self`.

        The order of fields in the schema is taken into account when computing equality.

        Parameters
        ----------
        other
            Schema to compare `self` to.

        Examples
        --------
        >>> import ibis
        >>> xy = ibis.schema({"x": int, "y": str})
        >>> xy2 = ibis.schema({"x": int, "y": str})
        >>> yx = ibis.schema({"y": str, "x": int})
        >>> xy_float = ibis.schema({"x": float, "y": str})
        >>> assert xy.equals(xy2)
        >>> assert not xy.equals(yx)
        >>> assert not xy.equals(xy_float)
        """
        if not isinstance(other, Schema):
            raise TypeError(
                f"invalid equality comparison between Schema and {type(other)}"
            )
        return self == other

    @classmethod
    def from_tuples(
        cls,
        values: Iterable[tuple[str, str | dt.DataType]],
    ) -> Schema:
        """Construct a `Schema` from an iterable of pairs.

        Parameters
        ----------
        values
            An iterable of pairs of name and type.

        Returns
        -------
        Schema
            A new schema

        Examples
        --------
        >>> import ibis
        >>> ibis.Schema.from_tuples([("a", "int"), ("b", "string")])
        ibis.Schema {
          a  int64
          b  string
        }

        """
        pairs = list(values)
        if len(pairs) == 0:
            return cls({})

        names, types = zip(*pairs)

        # validate unique field names
        name_locs = {v: i for i, v in enumerate(names)}
        if len(name_locs) < len(names):
            duplicate_names = list(names)
            for v in name_locs:
                duplicate_names.remove(v)
            raise IntegrityError(f"Duplicate column name(s): {duplicate_names}")

        # construct the schema
        return cls(dict(zip(names, types)))

    @classmethod
    def from_numpy(cls, numpy_schema):
        """Return the equivalent ibis schema."""
        from bigframes_vendored.ibis.formats.numpy import NumpySchema

        return NumpySchema.to_ibis(numpy_schema)

    @classmethod
    def from_pandas(cls, pandas_schema):
        """Return the equivalent ibis schema."""
        from bigframes_vendored.ibis.formats.pandas import PandasSchema

        return PandasSchema.to_ibis(pandas_schema)

    @classmethod
    def from_pyarrow(cls, pyarrow_schema):
        """Return the equivalent ibis schema."""
        from bigframes_vendored.ibis.formats.pyarrow import PyArrowSchema

        return PyArrowSchema.to_ibis(pyarrow_schema)

    @classmethod
    def from_polars(cls, polars_schema):
        """Return the equivalent ibis schema."""
        from bigframes_vendored.ibis.formats.polars import PolarsSchema

        return PolarsSchema.to_ibis(polars_schema)

    def to_numpy(self):
        """Return the equivalent numpy dtypes."""
        from bigframes_vendored.ibis.formats.numpy import NumpySchema

        return NumpySchema.from_ibis(self)

    def to_pandas(self):
        """Return the equivalent pandas datatypes."""
        from bigframes_vendored.ibis.formats.pandas import PandasSchema

        return PandasSchema.from_ibis(self)

    def to_pyarrow(self):
        """Return the equivalent pyarrow schema."""
        from bigframes_vendored.ibis.formats.pyarrow import PyArrowSchema

        return PyArrowSchema.from_ibis(self)

    def __arrow_c_schema__(self):
        return self.to_pyarrow().__arrow_c_schema__()

    def to_polars(self):
        """Return the equivalent polars schema."""
        from bigframes_vendored.ibis.formats.polars import PolarsSchema

        return PolarsSchema.from_ibis(self)

    def as_struct(self) -> dt.Struct:
        return dt.Struct(self)

    def name_at_position(self, i: int) -> str:
        """Return the name of a schema column at position `i`.

        Parameters
        ----------
        i
            The position of the column

        Returns
        -------
        str
            The name of the column in the schema at position `i`.

        Examples
        --------
        >>> import ibis
        >>> sch = ibis.Schema({"a": "int", "b": "string"})
        >>> sch.name_at_position(0)
        'a'
        >>> sch.name_at_position(1)
        'b'

        """
        return self.names[i]


SchemaLike: TypeAlias = Union[
    Schema,
    Mapping[str, Union[str, dt.DataType]],
    Iterable[tuple[str, Union[str, dt.DataType]]],
]


@lazy_singledispatch
def schema(value: Any) -> Schema:
    """Construct ibis schema from schema-like python objects."""
    raise InputTypeError(value)


@lazy_singledispatch
def infer(value: Any) -> Schema:
    """Infer the corresponding ibis schema for a python object."""
    raise InputTypeError(value)


@schema.register(Schema)
def from_schema(s):
    return s


@schema.register(Mapping)
def from_mapping(d):
    return Schema(d)


@schema.register(Iterable)
def from_pairs(lst):
    return Schema.from_tuples(lst)


@schema.register(type)
def from_class(cls):
    return Schema(dt.dtype(cls))


@schema.register("pandas.Series")
def from_pandas_series(s):
    from bigframes_vendored.ibis.formats.pandas import PandasSchema

    return PandasSchema.to_ibis(s)


@schema.register("pyarrow.Schema")
def from_pyarrow_schema(schema):
    from bigframes_vendored.ibis.formats.pyarrow import PyArrowSchema

    return PyArrowSchema.to_ibis(schema)


@infer.register("pandas.DataFrame")
def infer_pandas_dataframe(df):
    from bigframes_vendored.ibis.formats.pandas import PandasData

    return PandasData.infer_table(df)


@infer.register("pyarrow.Table")
def infer_pyarrow_table(table):
    from bigframes_vendored.ibis.formats.pyarrow import PyArrowSchema

    return PyArrowSchema.to_ibis(table.schema)


@infer.register("polars.DataFrame")
@infer.register("polars.LazyFrame")
def infer_polars_dataframe(df):
    from bigframes_vendored.ibis.formats.polars import PolarsSchema

    return PolarsSchema.to_ibis(df.collect_schema())


# lock the dispatchers to avoid adding new implementations
del infer.register
del schema.register