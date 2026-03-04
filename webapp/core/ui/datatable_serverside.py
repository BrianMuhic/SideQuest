"""
Handle server side data tables
"""

import re
from typing import Any, Mapping, Sequence

from pydantic import BaseModel
from sqlalchemy import ColumnElement, or_
from sqlalchemy.orm import InstrumentedAttribute, Session

from core.db.base_model import count
from core.service.logger import get_logger
from core.util.types import NameValueDict, NameValueDicts, SelectT

log = get_logger()

# TODO: Redo test data


class DataTableSearch(BaseModel):
    """Store the search fields (value and regex) of args used to search entire table"""

    value: str
    regex: bool

    def pattern(self) -> str:
        """Return SQL search string for self.value"""
        return f"%{self.value}%"

    def validate_regex(self, pattern: str) -> str:
        """Validate and sanitize regex pattern"""
        if not pattern:
            return ".*"  # Match everything if empty

        # Check if the pattern is valid regex
        try:
            re.compile(pattern)
            return pattern
        except re.error:
            # If invalid regex, escape it and treat as literal string
            return re.escape(pattern)

    def match_pattern(self, col: InstrumentedAttribute[Any]) -> ColumnElement[bool]:
        """Return SQL search of col for self.value"""
        if self.regex:
            safe_pattern = self.validate_regex(self.value)
            pattern = col.regexp_match(safe_pattern)
        else:
            pattern = col.like(f"%{self.value}%")
        if self.value.lower() in ("none", "non"):
            pattern = or_(pattern, col.is_(None))
        return pattern

    @staticmethod
    def test_data() -> NameValueDict:
        return dict(value="", regex=False)


class DataTableOrder(BaseModel):
    """Store the 'order' field of args used to sort the table"""

    column: int
    dir: str

    @staticmethod
    def test_data() -> NameValueDict:
        return dict(column=0, dir="asc")


class DataTableColumn(BaseModel):
    """Store the 'column' fields of args used to field and sort individual columns"""

    data: str | None = None
    name: str
    orderable: bool
    searchable: bool
    search: DataTableSearch | None = None

    @staticmethod
    def test_data() -> NameValueDicts:
        return [
            dict(
                data="name",
                name="",
                orderable=False,
                searchable=True,
                search=DataTableSearch.test_data(),
            ),
        ]


class DataTablePayload(BaseModel):
    """Process the args passed from a serverside datatable"""

    draw: int
    start: int
    length: int | None = None
    search: DataTableSearch | None = None
    order: Sequence[DataTableOrder]
    columns: Sequence[DataTableColumn]

    # total number of rows in the table, without considering any filters.
    records_total: int = 0
    # total number of rows that match the current search filter.
    records_filtered: int = 0

    # database field for any column that is to be sortable or searchable
    column_map: Mapping = {}

    # filter (column, values) for any column that is duplicated in the table
    # filter_map: dict = None

    export: bool = False

    @classmethod
    def create(cls, args: Any) -> "DataTablePayload":
        """Required for server side export..."""
        if args:
            return cls.model_validate(args)
        return cls(draw=1, start=0, length=-1, search=None, order=(), columns=(), export=True)

    def __str__(self) -> str:
        result = f"\t{self.draw=}, {self.start=}, {self.length=}, {self.export=},\n"
        result = f"{result}\t{self.search=},\n"
        result = f"{result}\t{self.order=},\n"
        for column in self.columns:
            result = f"{result}\t{column=},\n"
        return result

    def __call__(
        self,
        db: Session,
        selection: SelectT,
        column_map: Mapping[str, InstrumentedAttribute[Any] | list[InstrumentedAttribute[Any]]],
        # filter_map: dict[str, tuple[InstrumentedAttribute[Any], list[Any]]] = None,
    ) -> SelectT:
        """Process the data according to args"""

        self.column_map = column_map
        # self.filter_map = filter_map or {}

        if not self.draw:  # TODO: Replace with assertion
            log.w("Not a server-side datatable")
            return selection
        self.records_total = count(db, selection)

        selection = self.filter(selection)
        self.records_filtered = count(db, selection)
        selection = self.paginate(selection)
        selection = self.sort(selection)
        return selection

    def paginate(self, selection: SelectT) -> SelectT:
        """Paginate the data according to args"""

        # Pass "-1" to show all records.
        # This is conventional with js datatables.
        if self.length == -1:
            self.length = None

        selection = selection.limit(self.length).offset(self.start)
        return selection

    def sort(self, selection: SelectT) -> SelectT:
        """Sort the data according to args"""

        fields = []
        order: DataTableOrder
        for order in self.order:
            column = self.columns[order.column]
            col = self.column_map.get(column.data)

            # if hasattr(model, column.data): col = getattr(model, column.data)
            if col is None:
                continue

            # If list of fields passed for one column, append them seperately into fields
            if isinstance(col, list):
                for field in col:
                    if order.dir == "desc":  # if order.desc:
                        field = field.desc()
                    fields.append(field)
            else:
                if order.dir == "desc":  # if order.desc:
                    col = col.desc()
                fields.append(col)

        if fields:
            selection = selection.order_by(*fields)

        return selection

    def filter(self, selection: SelectT) -> SelectT:
        """Filter the data according to args"""

        # Search all columns
        if self.search and self.search.value:
            pattern = self.search.pattern()

            search_cols: list[ColumnElement] = []
            for column in self.columns:
                if not (column.searchable and column.data in self.column_map):
                    continue
                fields = self.column_map[column.data]
                if isinstance(fields, list):
                    for field in fields:
                        search_cols.append(field)
                else:
                    search_cols.append(self.column_map[column.data])

            if search_cols:
                filters = [col.like(pattern) for col in search_cols]
                if pattern.lower() in ("%none%", "%non%"):
                    filters += [col.is_(None) for col in search_cols]
                selection = selection.where(or_(*filters))

        # Search individual columns
        for column in self.columns:
            if column.search and column.search.value and column.data in self.column_map:
                col = self.column_map[column.data]

                # Handle array passed as column data
                if isinstance(col, list):
                    filters = [column.search.match_pattern(field) for field in col]
                    selection = selection.where(or_(*filters))
                # Single column value
                else:
                    selection = selection.where(column.search.match_pattern(col))

        return selection

    def result(self, data: list[Any]) -> NameValueDict:
        """Return the response to be passed back to the front-end datatable"""

        if self.export:
            data = [list(record.values()) for record in data]

        return dict(
            data=data,
            draw=self.draw,
            recordsFiltered=self.records_filtered,
            recordsTotal=self.records_total,
        )

    @staticmethod
    def test_data(**kw) -> NameValueDict:
        result = dict(
            draw=1,
            start=0,
            length=25,
            search=DataTableSearch.test_data(),
            order=(),  # DataTableOrder.test_data(),
            columns=DataTableColumn.test_data(),
        )
        result.update(**kw)
        return result


class ServerSideDatatableRequest(BaseModel):
    args: DataTablePayload
    option: int | None = None
