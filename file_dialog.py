# -*- coding: utf-8 -*-
from __future__ import annotations

import mimetypes
from importlib.util import find_spec
from os import PathLike
from pathlib import Path
from typing import Collection, NamedTuple, final

from qtpy.QtWidgets import QFileDialog, QWidget

from settings import Settings

__all__ = ["OpenFileDialog", "SaveFileDialog"]


class FileDialog(QFileDialog):
    class SupportedType(NamedTuple):
        required_packages: Collection[str, ...]
        file_extension: str

    def __init__(
        self,
        settings: Settings,
        supported_types: Collection[SupportedType] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)

        self.settings: Settings = settings
        self.supported_types: Collection[FileDialog.SupportedType] = tuple(
            supported_types
        )

    def selectFile(self, filename: str | PathLike[str]) -> None:
        return super().selectFile(str(filename))

    def selectedFile(self) -> Path | None:
        try:
            return Path(self.selectedFiles()[0])
        except IndexError:
            return None


@final
class OpenFileDialog(FileDialog):
    def get_open_filename(self) -> Path | None:
        mimetypes.init()

        opened_filename: Path = self.settings.opened_file_name

        supported_mimetypes: list[str] = []
        mimetype: str | None
        for supported_type in self.supported_types:
            if any(find_spec(package) for package in supported_type.required_packages):
                if mimetype := mimetypes.types_map.get(supported_type.file_extension):
                    supported_mimetypes.append(mimetype)
        # for the “All files (*)” filter
        supported_mimetypes.append("application/octet-stream")

        self.restoreGeometry(self.settings.open_dialog_geometry)
        self.restoreState(self.settings.open_dialog_state)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        self.setFileMode(QFileDialog.FileMode.ExistingFile)
        self.setMimeTypeFilters(supported_mimetypes)
        if len(supported_mimetypes) > 1:
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
                            for t in supported_mimetypes[:-1]
                        ),
                        ")",
                    )
                ),
            )
            self.setNameFilters(name_filters)
        self.selectFile(opened_filename)

        if self.exec() and (file_path := self.selectedFile()):
            self.settings.open_dialog_state = self.saveState()
            self.settings.open_dialog_geometry = self.saveGeometry()
            self.settings.opened_file_name = file_path
            return file_path
        return None


@final
class SaveFileDialog(FileDialog):
    def get_save_filename(self) -> Path | None:
        mimetypes.init()

        filename: Path = self.settings.saved_file_name
        opened_filename: Path = self.settings.opened_file_name

        supported_mimetypes: list[str] = []
        mimetype: str | None
        for supported_type in self.supported_types:
            if any(find_spec(package) for package in supported_type.required_packages):
                if mimetype := mimetypes.types_map.get(supported_type.file_extension):
                    supported_mimetypes.append(mimetype)

        if not supported_mimetypes:
            return None

        selected_mimetype: str | None = None
        if filename:
            selected_mimetype = mimetypes.guess_type(filename, strict=False)[0]
        if supported_mimetypes and selected_mimetype is None:
            selected_mimetype = supported_mimetypes[0]

        self.restoreGeometry(self.settings.save_dialog_geometry)
        self.restoreState(self.settings.save_dialog_state)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setMimeTypeFilters(supported_mimetypes)
        self.setOption(QFileDialog.Option.DontConfirmOverwrite, False)
        if selected_mimetype is not None:
            self.selectMimeTypeFilter(selected_mimetype)
            self.selectFile(
                str(
                    Path(filename or opened_filename)
                    .with_name(Path(opened_filename).name)
                    .with_suffix(
                        mimetypes.guess_extension(selected_mimetype, strict=False) or ""
                    )
                )
            )

        if self.exec() and self.selectedFiles():
            self.settings.save_dialog_state = self.saveState()
            self.settings.save_dialog_geometry = self.saveGeometry()
            if not (filename := self.selectedFile()):
                return None
            new_file_type: str | None = mimetypes.guess_type(
                url=filename, strict=False
            )[0]
            if new_file_type is None or (
                supported_mimetypes and new_file_type not in supported_mimetypes
            ):
                new_file_type = self.selectedMimeTypeFilter()
                ext: str | None = mimetypes.guess_extension(new_file_type, strict=False)
                if ext is not None:
                    filename += ext
            self.settings.saved_file_name = filename
            return filename
        return None
