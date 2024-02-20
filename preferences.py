# coding=utf-8
from __future__ import annotations

from abc import abstractmethod
from functools import partial
from logging import Logger, getLogger
from pathlib import Path
from typing import Any, ClassVar, Hashable, ParamSpec, cast

from qtawesome import icon
from qtpy.QtCore import Qt, QByteArray
from qtpy.QtGui import QCloseEvent
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from open_file_path_entry import OpenFilePathEntry
from settings import Settings

__all__ = ["Preferences"]


class BaseLogger:
    logger: ClassVar[Logger]
    _P = ParamSpec("_P")

    def __new__(cls, *args: _P.args, **kwargs: _P.kwargs):
        cls.logger = getLogger(cls.__name__)
        return super().__new__(cls)

    @abstractmethod
    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        pass


class PreferencePage(QScrollArea, BaseLogger):
    """A page of the Preferences dialog"""

    def __init__(
        self,
        value: dict[
            str,
            (
                Settings.CallbackOnly
                | Settings.PathCallbackOnly
                | Settings.SpinboxAndCallback
                | Settings.ComboboxAndCallback
                | Settings.EditableComboboxAndCallback
            ),
        ],
        settings: Settings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        widget: QWidget = QWidget(self)
        self.setWidget(widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameStyle(0)

        self._changed_settings: dict[str, Any] = {}

        # https://forum.qt.io/post/671245
        def _on_event(x: bool | int | float | str, *, callback: str) -> None:
            self._changed_settings[callback] = x

        def _on_combo_box_current_index_changed(
            _: int, *, sender: QComboBox, callback: str
        ) -> None:
            self._changed_settings[callback] = sender.currentData()

        if not (isinstance(value, dict) and value):
            raise TypeError(f"Invalid type: {type(value)}")
        layout: QFormLayout = QFormLayout(widget)
        layout.setLabelAlignment(
            layout.labelAlignment() | Qt.AlignmentFlag.AlignVCenter
        )
        key2: str
        value2: (
            Settings.CallbackOnly
            | Settings.PathCallbackOnly
            | Settings.SpinboxAndCallback
            | Settings.ComboboxAndCallback
            | Settings.EditableComboboxAndCallback
        )

        check_box: QCheckBox
        path_entry: OpenFilePathEntry
        spin_box: QSpinBox | QDoubleSpinBox
        combo_box: QComboBox

        for key2, value2 in value.items():
            if isinstance(value2, Settings.CallbackOnly):
                if isinstance(getattr(settings, value2.callback), bool):
                    check_box = QCheckBox(settings.tr(key2), widget)
                    check_box.setChecked(getattr(settings, value2.callback))
                    check_box.toggled.connect(
                        partial(_on_event, callback=value2.callback)
                    )
                    layout.addWidget(check_box)
                elif isinstance(
                    initial_path := getattr(settings, value2.callback), Path
                ):
                    path_entry = OpenFilePathEntry(initial_path, widget)
                    path_entry.changed.connect(
                        partial(_on_event, callback=value2.callback)
                    )
                    layout.addRow(settings.tr(key2), path_entry)
                else:
                    PreferencePage.logger.error(
                        f"The type of {value2.callback!r} is not supported"
                    )
            if isinstance(value2, Settings.PathCallbackOnly):
                if isinstance(
                    initial_path := getattr(settings, value2.callback),
                    (Path, type(None)),
                ):
                    path_entry = OpenFilePathEntry(initial_path, widget)
                    path_entry.changed.connect(
                        partial(_on_event, callback=value2.callback)
                    )
                    layout.addRow(settings.tr(key2), path_entry)
                else:
                    PreferencePage.logger.error(
                        f"The type of {value2.callback!r} is not supported"
                    )
            elif isinstance(value2, Settings.SpinboxAndCallback):
                if isinstance(getattr(settings, value2.callback), int):
                    spin_box = QSpinBox(widget)
                else:
                    spin_box = QDoubleSpinBox(widget)
                spin_box.setValue(getattr(settings, value2.callback))
                spin_box.setRange(value2.range.start, value2.range.stop)
                spin_box.setSingleStep(value2.range.step or 1)
                spin_box.setPrefix(value2.prefix_and_suffix[0])
                spin_box.setSuffix(value2.prefix_and_suffix[1])
                spin_box.valueChanged.connect(
                    partial(_on_event, callback=value2.callback)
                )
                layout.addRow(key2, spin_box)
            elif isinstance(value2, Settings.ComboboxAndCallback):
                combo_box = QComboBox(widget)
                combobox_data: dict[Hashable, str]
                if isinstance(value2.combobox_data, dict):
                    combobox_data = value2.combobox_data
                else:
                    combobox_data = dict(enumerate(value2.combobox_data))
                for index, (data, item) in enumerate(combobox_data.items()):
                    combo_box.addItem(settings.tr(item), data)
                combo_box.setEditable(False)
                combo_box.setCurrentText(
                    combobox_data[getattr(settings, value2.callback)]
                )
                combo_box.currentIndexChanged.connect(
                    partial(
                        _on_combo_box_current_index_changed,
                        sender=combo_box,
                        callback=value2.callback,
                    )
                )
                layout.addRow(settings.tr(key2), combo_box)
            elif isinstance(value2, Settings.EditableComboboxAndCallback):
                combo_box = QComboBox(widget)
                combo_box.addItems(value2.combobox_items)
                current_text: str = getattr(settings, value2.callback)
                if current_text in value2.combobox_items:
                    combo_box.setCurrentIndex(value2.combobox_items.index(current_text))
                else:
                    combo_box.insertItem(0, current_text)
                    combo_box.setCurrentIndex(0)
                combo_box.setEditable(True)
                combo_box.currentTextChanged.connect(
                    partial(_on_event, callback=value2.callback)
                )
                layout.addRow(settings.tr(key2), combo_box)
            else:
                PreferencePage.logger.error(f"{value2!r} is not supported")

    @property
    def changed_settings(self) -> dict[str, Any]:
        return self._changed_settings.copy()


class PreferencesBody(QSplitter, BaseLogger):
    """The main area of the GUI preferences dialog"""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setOrientation(Qt.Orientation.Horizontal)
        self.setChildrenCollapsible(False)
        content: QListWidget = QListWidget(self)
        self._stack: QStackedWidget = QStackedWidget(self)
        key: (
            str
            | tuple[str, tuple[str, ...]]
            | tuple[str, tuple[str, ...], tuple[tuple[str, Any], ...]]
        )
        value: dict[
            str,
            (
                Settings.CallbackOnly
                | Settings.PathCallbackOnly
                | Settings.SpinboxAndCallback
                | Settings.ComboboxAndCallback
                | Settings.EditableComboboxAndCallback
            ),
        ]
        for key, value in settings.dialog.items():
            if not (isinstance(value, dict) and value):
                PreferencesBody.logger.error(f"Invalid value of {key!r}")
                continue
            new_item: QListWidgetItem
            if isinstance(key, str):
                new_item = QListWidgetItem(key)
            elif isinstance(key, tuple):
                if len(key) == 1:
                    new_item = QListWidgetItem(key[0])
                elif len(key) == 2:
                    new_item = QListWidgetItem(icon(*key[1]), key[0])
                elif len(key) == 3:
                    new_item = QListWidgetItem(icon(*key[1], **dict(key[2])), key[0])
                else:
                    PreferencesBody.logger.error(f"Invalid key: {key!r}")
                    continue
            else:
                PreferencesBody.logger.error(f"Invalid key type: {key!r}")
                continue
            content.addItem(new_item)
            box: PreferencePage = PreferencePage(value, settings, self._stack)
            self._stack.addWidget(box)
        content.setMinimumWidth(content.sizeHintForColumn(0) + 2 * content.frameWidth())
        self.addWidget(content)
        self.addWidget(self._stack)

        if content.count() > 0:
            content.setCurrentRow(0)  # select the first page

        content.currentRowChanged.connect(self._stack.setCurrentIndex)

    @property
    def changed_settings(self) -> dict[str, Any]:
        changed_settings: dict[str, Any] = {}
        for index in range(self._stack.count()):
            changed_settings.update(
                cast(PreferencePage, self._stack.widget(index)).changed_settings
            )
        return changed_settings


class Preferences(QDialog):
    """GUI preferences dialog"""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._settings: Settings = settings
        self.setModal(True)
        self.setWindowTitle(self.tr("Preferences"))
        if parent is not None:
            self.setWindowIcon(parent.windowIcon())

        layout: QVBoxLayout = QVBoxLayout(self)
        self._preferences_body: PreferencesBody = PreferencesBody(
            settings=settings, parent=parent
        )
        layout.addWidget(self._preferences_body)
        buttons: QDialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

        self.adjustSize()
        self.resize(self.width() + 4, self.height())

        self._settings.beginGroup("geometry")
        self.restoreGeometry(
            cast(QByteArray, self._settings.value("preferencesDialog", QByteArray()))
        )
        self._settings.endGroup()
        self._settings.beginGroup("state")
        self._preferences_body.restoreState(
            cast(QByteArray, self._settings.value("preferencesDialog", QByteArray()))
        )
        self._settings.endGroup()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings.beginGroup("geometry")
        self._settings.setValue("preferencesDialog", self.saveGeometry())
        self._settings.endGroup()
        self._settings.beginGroup("state")
        self._settings.setValue("preferencesDialog", self._preferences_body.saveState())
        self._settings.endGroup()

    def accept(self) -> None:
        for key, value in self._preferences_body.changed_settings.items():
            setattr(self._settings, key, value)
        return super().accept()
