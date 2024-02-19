# coding=utf-8
from __future__ import annotations

from typing import ClassVar, Collection, Iterable, TYPE_CHECKING

from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

__all__ = ["ColumnSelector"]

if TYPE_CHECKING:
    from typing import Type

    def Property(*_: type) -> Type[property]:
        return property

else:
    from qtpy.QtCore import Property


class ColumnSelectorPage(QWizardPage):
    def __init__(
        self,
        columns: Iterable[str],
        selected_columns: Collection[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setTitle(self.tr("Columns to Read"))
        self.setSubTitle(self.tr("Select columns to write in the results"))

        self._check_boxes: list[QCheckBox] = []

        self.registerField("selected_columns", self, "selected_columns")

        layout: QVBoxLayout = QVBoxLayout(self)
        for column in columns:
            cb: QCheckBox = QCheckBox(column, self)
            self._check_boxes.append(cb)
            layout.addWidget(cb)

        self.selected_columns = selected_columns

    def validatePage(self) -> bool:
        selected_columns: list[str] = self.selected_columns
        self.setField("selected_columns", selected_columns)
        return bool(selected_columns)

    if TYPE_CHECKING:

        @property
        def selected_columns(self) -> list[str]:
            return []

        @selected_columns.setter
        def selected_columns(self, value: Collection[str]) -> None:
            pass

    else:

        @Property(list)
        def selected_columns(self) -> list[str]:
            return [cb.text() for cb in self._check_boxes if cb.isChecked()]

        @selected_columns.setter
        def selected_columns(self, value: Collection[str]) -> None:
            for cb in self._check_boxes:
                cb.setChecked(cb.text() in value)


class PrincipalColumnSelectorPage(QWizardPage):
    def __init__(
        self,
        principal_column: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setTitle(self.tr("Principal Column"))
        self.setSubTitle(self.tr("Select a column to compare by"))

        self._principal_column: str = principal_column
        self._radio_buttons: list[QRadioButton] = []

        self._layout: QVBoxLayout = QVBoxLayout(self)

    def initializePage(self) -> None:
        super().initializePage()

        rb: QRadioButton
        for rb in self._radio_buttons:
            rb.deleteLater()
        self._radio_buttons.clear()

        columns: list[str] = self.field("selected_columns")
        for column in columns:
            rb = QRadioButton(column, self)
            rb.setChecked(column == self._principal_column)
            self._radio_buttons.append(rb)
            self._layout.addWidget(rb)

    def validatePage(self) -> bool:
        return any(rb.isChecked() for rb in self._radio_buttons)

    @property
    def principal_column(self) -> str:
        for rb in self._radio_buttons:
            if rb.isChecked():
                return rb.text()
        return ""


class ColumnSelectorWizard(QWizard):
    def __init__(
        self,
        columns: Iterable[str],
        selected_columns: Collection[str],
        principal_column: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._columns: list[str] = list(columns)

        self._page1: ColumnSelectorPage = ColumnSelectorPage(
            self._columns,
            selected_columns,
            self,
        )
        self.addPage(self._page1)
        self._page2: PrincipalColumnSelectorPage = PrincipalColumnSelectorPage(
            principal_column,
            self,
        )
        self.addPage(self._page2)

        self.setModal(True)
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

    @property
    def selected_columns(self) -> list[str]:
        return self._page1.selected_columns

    @property
    def principal_column(self) -> str:
        return self._page2.principal_column


class ColumnSelector(QLabel):
    last_time_selected_columns: ClassVar[set[str]] = set()
    last_time_principal_column: ClassVar[str] = ""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._columns: list[str] = []
        self._selected_columns: set[str] = set(
            ColumnSelector.last_time_selected_columns
        )
        self._principal_column_index: int = 0

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        w: ColumnSelectorWizard = ColumnSelectorWizard(
            columns=self._columns,
            selected_columns=self.selected_columns,
            principal_column=self.principal_column,
            parent=self,
        )
        if w.exec() == QDialog.DialogCode.Accepted:
            principal_column: str = w.principal_column
            selected_columns: list[str] = w.selected_columns
            self._principal_column_index = self._columns.index(principal_column)
            self._selected_columns = set(selected_columns)
            ColumnSelector.last_time_selected_columns = self._selected_columns
            ColumnSelector.last_time_principal_column = principal_column
            self._show_columns()
        return super().mouseDoubleClickEvent(event)

    def _show_columns(self) -> None:
        text: str
        if not self._selected_columns:
            text = "[ ]"  # the space is intended not to join the brackets
            self.setToolTip("")
        else:
            text = (
                "["
                + ", ".join(
                    (
                        self.principal_column,
                        "(" + ", ".join(self.other_selected_columns) + ")",
                    )
                )
                + "]"
            )
            self.setToolTip(text)
        self.setText(text)

    @property
    def columns(self) -> list[str]:
        return self._columns.copy()

    @columns.setter
    def columns(self, new_columns: Iterable[str]) -> None:
        old_principal_column: str = (
            self.principal_column or ColumnSelector.last_time_principal_column
        )
        self._columns = list(new_columns)
        self.setEnabled(bool(self._columns))

        # restore the principal column if possible
        if old_principal_column:
            try:
                self._principal_column_index = self._columns.index(old_principal_column)
            except ValueError:
                self._principal_column_index = 0

        self._show_columns()

    @property
    def principal_column(self) -> str:
        try:
            return self._columns[self._principal_column_index]
        except LookupError:
            return ""

    @principal_column.setter
    def principal_column(self, new_value: str) -> None:
        if new_value in self._columns:
            self._principal_column_index = self._columns.index(new_value)
            self._selected_columns.add(new_value)

    @property
    def selected_columns(self) -> list[str]:
        return [c for c in self._columns if c in self._selected_columns]

    @selected_columns.setter
    def selected_columns(self, new_selected_columns: Collection[str]) -> None:
        old_principal_column: str = (
            self.principal_column or ColumnSelector.last_time_principal_column
        )
        new_selected_columns = [c for c in self._columns if c in new_selected_columns]
        if new_selected_columns and old_principal_column not in new_selected_columns:
            old_principal_column = new_selected_columns[0]
        self._selected_columns = set(new_selected_columns)
        ColumnSelector.last_time_selected_columns = self._selected_columns

        # restore the principal column if possible
        if old_principal_column:
            try:
                self._principal_column_index = self._columns.index(old_principal_column)
            except ValueError:
                self._principal_column_index = 0

        self._show_columns()

    @property
    def other_selected_columns(self) -> list[str]:
        principal_column: str = self.principal_column
        return [
            c
            for c in self._columns
            if c != principal_column and c in self._selected_columns
        ]
