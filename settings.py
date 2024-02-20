# coding=utf-8
from __future__ import annotations

from pathlib import Path
from typing import Hashable, Iterable, NamedTuple, Sequence, cast

from qtpy.QtCore import QByteArray, QSettings

__all__ = ["Settings"]


class Settings(QSettings):
    """Convenient internal representation of the application settings"""

    class CallbackOnly(NamedTuple):
        callback: str

    class PathCallbackOnly(NamedTuple):
        callback: str

    class SpinboxAndCallback(NamedTuple):
        range: slice
        prefix_and_suffix: tuple[str, str]
        callback: str

    class ComboboxAndCallback(NamedTuple):
        combobox_data: Iterable[str] | dict[Hashable, str]
        callback: str

    class EditableComboboxAndCallback(NamedTuple):
        combobox_items: Sequence[str]
        callback: str

    @property
    def dialog(
        self,
    ) -> dict[
        str | tuple[str, tuple[str, ...]],
        dict[
            str,
            CallbackOnly
            | PathCallbackOnly
            | SpinboxAndCallback
            | ComboboxAndCallback
            | EditableComboboxAndCallback,
        ],
    ]:
        return {
            (self.tr("File Reading"), ("mdi6.book-open-blank-variant",)): {
                self.tr("Ignore case"): Settings.CallbackOnly(
                    Settings.ignore_case.fget.__name__
                ),
                self.tr("Merge spaces"): Settings.CallbackOnly(
                    Settings.merge_spaces.fget.__name__
                ),
            },
            (self.tr("View"), ("mdi6.binoculars",)): {
                self.tr("Translation file:"): Settings.PathCallbackOnly(
                    Settings.translation_path.fget.__name__
                ),
            },
        }

    @property
    def translation_path(self) -> Path | None:
        self.beginGroup("translation")
        v: str = cast(str, self.value("filePath", "", str))
        self.endGroup()
        return Path(v) if v else None

    @translation_path.setter
    def translation_path(self, new_value: Path | None) -> None:
        self.beginGroup("translation")
        self.setValue("filePath", str(new_value) if new_value is not None else "")
        self.endGroup()

    @property
    def opened_file_name(self) -> str:
        try:
            self.beginGroup("location")
            return cast(str, self.value("open", str(Path.cwd()), str))
        finally:
            self.endGroup()

    @opened_file_name.setter
    def opened_file_name(self, filename: str) -> None:
        self.beginGroup("location")
        self.setValue("open", filename)
        self.endGroup()

    @property
    def saved_file_name(self) -> str:
        try:
            self.beginGroup("location")
            return cast(str, self.value("save", str(Path.cwd()), str))
        finally:
            self.endGroup()

    @saved_file_name.setter
    def saved_file_name(self, filename: str) -> None:
        self.beginGroup("location")
        self.setValue("save", filename)
        self.endGroup()

    @property
    def save_dialog_state(self) -> QByteArray:
        try:
            self.beginGroup("state")
            return cast(QByteArray, self.value("saveDialog", QByteArray()))
        finally:
            self.endGroup()

    @save_dialog_state.setter
    def save_dialog_state(self, state: QByteArray) -> None:
        self.beginGroup("state")
        self.setValue("saveDialog", state)
        self.endGroup()

    @property
    def save_dialog_geometry(self) -> QByteArray:
        try:
            self.beginGroup("geometry")
            return cast(QByteArray, self.value("saveDialog", QByteArray()))
        finally:
            self.endGroup()

    @save_dialog_geometry.setter
    def save_dialog_geometry(self, state: QByteArray) -> None:
        self.beginGroup("geometry")
        self.setValue("saveDialog", state)
        self.endGroup()

    @property
    def open_dialog_state(self) -> QByteArray:
        try:
            self.beginGroup("state")
            return cast(QByteArray, self.value("openDialog", QByteArray()))
        finally:
            self.endGroup()

    @open_dialog_state.setter
    def open_dialog_state(self, state: QByteArray) -> None:
        self.beginGroup("state")
        self.setValue("openDialog", state)
        self.endGroup()

    @property
    def open_dialog_geometry(self) -> QByteArray:
        try:
            self.beginGroup("geometry")
            return cast(QByteArray, self.value("openDialog", QByteArray()))
        finally:
            self.endGroup()

    @open_dialog_geometry.setter
    def open_dialog_geometry(self, state: QByteArray) -> None:
        self.beginGroup("geometry")
        self.setValue("openDialog", state)
        self.endGroup()

    @property
    def main_window_state(self) -> QByteArray:
        try:
            self.beginGroup("state")
            return cast(QByteArray, self.value("mainWindow", QByteArray()))
        finally:
            self.endGroup()

    @main_window_state.setter
    def main_window_state(self, state: QByteArray) -> None:
        self.beginGroup("state")
        self.setValue("mainWindow", state)
        self.endGroup()

    @property
    def main_window_geometry(self) -> QByteArray:
        try:
            self.beginGroup("geometry")
            return cast(QByteArray, self.value("mainWindow", QByteArray()))
        finally:
            self.endGroup()

    @main_window_geometry.setter
    def main_window_geometry(self, state: QByteArray) -> None:
        self.beginGroup("geometry")
        self.setValue("mainWindow", state)
        self.endGroup()

    @property
    def table_geometry(self) -> QByteArray:
        try:
            self.beginGroup("geometry")
            return cast(QByteArray, self.value("table", QByteArray()))
        finally:
            self.endGroup()

    @table_geometry.setter
    def table_geometry(self, state: QByteArray) -> None:
        self.beginGroup("geometry")
        self.setValue("table", state)
        self.endGroup()

    @property
    def table_header_geometry(self) -> QByteArray:
        try:
            self.beginGroup("geometry")
            return cast(QByteArray, self.value("tableHeader", QByteArray()))
        finally:
            self.endGroup()

    @table_header_geometry.setter
    def table_header_geometry(self, state: QByteArray) -> None:
        self.beginGroup("geometry")
        self.setValue("tableHeader", state)
        self.endGroup()

    @property
    def table_header_state(self) -> QByteArray:
        try:
            self.beginGroup("state")
            return cast(QByteArray, self.value("tableHeader", QByteArray()))
        finally:
            self.endGroup()

    @table_header_state.setter
    def table_header_state(self, state: QByteArray) -> None:
        self.beginGroup("state")
        self.setValue("tableHeader", state)
        self.endGroup()

    @property
    def principal_column(self) -> str:
        try:
            self.beginGroup("columns")
            return cast(str, self.value("principal", ""))
        finally:
            self.endGroup()

    @principal_column.setter
    def principal_column(self, column_name: str) -> None:
        self.beginGroup("columns")
        self.setValue("principal", column_name)
        self.endGroup()

    @property
    def selected_columns(self) -> Sequence[str]:
        selected_columns: list[str] = []
        length: int = self.beginReadArray("columns")
        for index in range(length):
            self.setArrayIndex(index)
            selected_columns.append(cast(str, self.value("selected", "")))
        self.endArray()
        return selected_columns

    @selected_columns.setter
    def selected_columns(self, column_names: Iterable[str]) -> None:
        self.beginWriteArray("columns")
        for index, column_name in enumerate(column_names):
            self.setArrayIndex(index)
            self.setValue("selected", column_name)
        self.endArray()

    @property
    def ignore_case(self) -> bool:
        try:
            self.beginGroup("columns")
            return cast(bool, self.value("ignoreCase", True))
        finally:
            self.endGroup()

    @ignore_case.setter
    def ignore_case(self, value: bool) -> None:
        self.beginGroup("columns")
        self.setValue("ignoreCase", value)
        self.endGroup()

    @property
    def merge_spaces(self) -> bool:
        try:
            self.beginGroup("columns")
            return cast(bool, self.value("mergeSpaces", True))
        finally:
            self.endGroup()

    @merge_spaces.setter
    def merge_spaces(self, value: bool) -> None:
        self.beginGroup("columns")
        self.setValue("mergeSpaces", value)
        self.endGroup()
