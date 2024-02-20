# -*- coding: utf-8 -*-
from __future__ import annotations

import mimetypes
from importlib.util import find_spec
from pathlib import Path
from typing import final

from pyexcel import Book, Sheet, get_book
from qtpy.QtWidgets import QFileDialog, QWidget

from settings import Settings

__all__ = ["OpenFileDialog", "SaveFileDialog"]


class FileDialog(QFileDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)

        self.settings: Settings = settings


@final
class OpenFileDialog(FileDialog):
    def get_open_filename(self) -> str:
        mimetypes.init()

        opened_filename: str = self.settings.opened_file_name

        supported_formats: list[str] = []
        mimetype: str | None
        if find_spec("pyexcel_xlsx") is not None:
            if mimetype := mimetypes.types_map.get(".xlsx"):
                supported_formats.append(mimetype)
        if (
            find_spec("pyexcel_ods") is not None
            or find_spec("pyexcel_ods3") is not None
        ):
            if mimetype := mimetypes.types_map.get(".ods"):
                supported_formats.append(mimetype)
        if find_spec("pyexcel_xls") is not None:
            if mimetype := mimetypes.types_map.get(".xls"):
                supported_formats.append(mimetype)
        # for the “All files (*)” filter
        supported_formats.append("application/octet-stream")

        self.restoreGeometry(self.settings.open_dialog_geometry)
        self.restoreState(self.settings.open_dialog_state)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self.setFileMode(QFileDialog.FileMode.ExistingFile)
        self.setMimeTypeFilters(supported_formats)
        name_filters: list[str] = self.nameFilters()
        name_filters.insert(
            0,
            "".join(
                (
                    self.tr("All supported"),
                    " (",
                    " ".join(
                        " ".join(
                            [
                                "*" + ext
                                for ext in mimetypes.guess_all_extensions(
                                    t, strict=False
                                )
                            ]
                        )
                        for t in supported_formats[:-1]
                    ),
                    ")",
                )
            ),
        )
        self.setNameFilters(name_filters)
        self.selectFile(opened_filename)

        if self.exec() and self.selectedFiles()[0]:
            self.settings.open_dialog_state = self.saveState()
            self.settings.open_dialog_geometry = self.saveGeometry()
            file_name: str = self.selectedFiles()[0]
            self.settings.opened_file_name = file_name
            return file_name
        return ""

    def load(self) -> Book | None:
        if filename := self.get_open_filename():
            return get_book(file_name=filename)
        return None


@final
class SaveFileDialog(FileDialog):
    def get_save_filename(self) -> str:
        mimetypes.init()

        filename: str = self.settings.saved_file_name
        opened_filename: str = self.settings.opened_file_name

        supported_formats: list[str] = []
        mimetype: str | None
        if find_spec("pyexcel_xlsx") is not None:
            if mimetype := mimetypes.types_map.get(".xlsx"):
                supported_formats.append(mimetype)
        if (
            find_spec("pyexcel_ods") is not None
            or find_spec("pyexcel_ods3") is not None
        ):
            if mimetype := mimetypes.types_map.get(".ods"):
                supported_formats.append(mimetype)
        if find_spec("pyexcel_xls") is not None:
            if mimetype := mimetypes.types_map.get(".xls"):
                supported_formats.append(mimetype)

        if not supported_formats:
            return ""

        selected_format: str | None = None
        if filename:
            selected_format = mimetypes.guess_type(filename, strict=False)[0]
        if supported_formats and selected_format is None:
            selected_format = supported_formats[0]

        self.restoreGeometry(self.settings.save_dialog_geometry)
        self.restoreState(self.settings.save_dialog_state)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setMimeTypeFilters(supported_formats)
        self.setOption(QFileDialog.Option.DontConfirmOverwrite, False)
        if selected_format is not None:
            self.selectMimeTypeFilter(selected_format)
            self.selectFile(
                str(
                    Path(filename or opened_filename)
                    .with_name(Path(opened_filename).name)
                    .with_suffix(
                        mimetypes.guess_extension(selected_format, strict=False) or ""
                    )
                )
            )

        if self.exec() and self.selectedFiles():
            self.settings.save_dialog_state = self.saveState()
            self.settings.save_dialog_geometry = self.saveGeometry()
            filename = self.selectedFiles()[0]
            if not filename:
                return ""
            new_file_format: str | None = mimetypes.guess_type(
                url=filename, strict=False
            )[0]
            if new_file_format is None or (
                supported_formats and new_file_format not in supported_formats
            ):
                new_file_format = self.selectedMimeTypeFilter()
                ext: str | None = mimetypes.guess_extension(
                    new_file_format, strict=False
                )
                if ext is not None:
                    filename += ext
            self.settings.saved_file_name = filename
            return filename
        return ""

    def save(self, sheet: Sheet) -> None:
        if filename := self.get_save_filename():
            sheet.save_as(filename)
