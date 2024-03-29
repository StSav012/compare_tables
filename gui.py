# coding=utf-8
from __future__ import annotations

import enum
import sys
import traceback
from contextlib import suppress
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import BinaryIO, Collection, Final, Iterator, cast, final

from pyexcel import Book, Sheet, get_book
from qtawesome import icon
from qtpy.QtCore import QLibraryInfo, QLocale, QModelIndex, QTranslator, Slot
from qtpy.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
    QVBoxLayout,
    QWidget,
)

from column_selector import ColumnSelector
from file_dialog import OpenFileDialog, SaveFileDialog
from preferences import Preferences
from settings import Settings


class Columns(enum.IntEnum):
    File = 0
    Sheets = 1
    Columns = 2


def xrange(*args: int) -> range:
    match args:
        case [stop]:
            return range(stop + 1)
        case [start, stop]:
            return range(start, stop + 1)
        case [start, stop, step]:
            return range(start, stop + 1, step)
        case _:
            return range(*args)


def read_sheet(
    sheet: Sheet,
    selected_columns: Collection[str],
    principal_column: str,
    *,
    ignore_case: bool = False,
    merge_spaces: bool = False,
) -> dict[tuple[str, ...], int]:
    data: dict[tuple[str, ...], int] = {}
    column_names: list[str] = [
        sheet[0, col] for col in range(sheet.number_of_columns())
    ]
    try:
        principal_column_index: int = column_names.index(principal_column)
    except LookupError:
        return {}
    key_columns: list[int] = [
        col
        for col, column_name in enumerate(column_names)
        if column_name in selected_columns
    ]
    for row in range(1, sheet.number_of_rows()):
        key: tuple[str, ...] = tuple(sheet[row, col] for col in key_columns)
        if any(key):
            matching_key: tuple[str, ...] = key
            simplified_key: list[str] = list(matching_key)
            if ignore_case:
                simplified_key = [
                    k.casefold() for k in simplified_key if isinstance(k, str)
                ]
            if merge_spaces:
                simplified_key = [
                    " ".join(k.split()) for k in simplified_key if isinstance(k, str)
                ]
            for existing_key in data:
                simplified_existing_key = list(existing_key)
                if ignore_case:
                    simplified_existing_key = [
                        k.casefold()
                        for k in simplified_existing_key
                        if isinstance(k, str)
                    ]
                if merge_spaces:
                    simplified_existing_key = [
                        " ".join(k.split())
                        for k in simplified_existing_key
                        if isinstance(k, str)
                    ]
                if simplified_key == simplified_existing_key:
                    matching_key = existing_key
                    break
            with suppress(TypeError):
                data[matching_key] = (
                    data.get(matching_key, 0) + sheet[row, principal_column_index]
                )
    return data


def find_qm_files(
    root: str | PathLike[str] = Path.cwd(),
    *,
    exclude: Collection[str | PathLike[str]] = frozenset(),
) -> Iterator[Path]:
    magic: Final[bytes] = bytes(
        [
            0x3C,
            0xB8,
            0x64,
            0x18,
            0xCA,
            0xEF,
            0x9C,
            0x95,
            0xCD,
            0x21,
            0x1C,
            0xBF,
            0x60,
            0xA1,
            0xBD,
            0xDD,
        ]
    )
    exclude = frozenset(map(Path, exclude))

    def list_files(path: Path) -> set[Path]:
        files: set[Path] = set()
        if path not in exclude:
            if path.is_dir():
                for child in path.iterdir():
                    if (child := child.resolve()) not in files:
                        files.update(list_files(child))
            elif path.is_file():
                files.add(path.resolve())
        return files

    file: Path
    f_in: BinaryIO
    for file in list_files(Path(root)):
        with suppress(Exception), open(file, "rb") as f_in:
            if f_in.read(len(magic)) == magic:
                yield file


@final
class UI(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setObjectName(self.__class__.__name__)
        self.setWindowIcon(icon("mdi6.file-compare"))
        self.setWindowTitle("Compare Lists of Lines")

        central_widget: QWidget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout: QVBoxLayout = QVBoxLayout(central_widget)
        central_widget.setLayout(layout)

        self.settings: Settings = Settings("SavSoft", "Compare Lists of Lines", self)
        self.settings.setObjectName(self.settings.__class__.__name__)
        self.open_file_dialog: OpenFileDialog = OpenFileDialog(
            self.settings,
            (
                OpenFileDialog.SupportedType(("pyexcel_xlsx",), ".xlsx"),
                OpenFileDialog.SupportedType(("pyexcel_ods", "pyexcel_ods3"), ".ods"),
                OpenFileDialog.SupportedType(("pyexcel_xls",), ".xls"),
            ),
            self,
        )
        self.open_file_dialog.setObjectName(self.open_file_dialog.__class__.__name__)
        self.save_file_dialog: SaveFileDialog = SaveFileDialog(
            self.settings,
            (
                OpenFileDialog.SupportedType(("pyexcel_xlsx",), ".xlsx"),
                OpenFileDialog.SupportedType(("pyexcel_ods", "pyexcel_ods3"), ".ods"),
                OpenFileDialog.SupportedType(("pyexcel_xls",), ".xls"),
            ),
            self,
        )
        self.save_file_dialog.setObjectName(self.save_file_dialog.__class__.__name__)

        menu: QMenuBar = QMenuBar(self)
        self.setMenuBar(menu)
        self.menu_file: QMenu = menu.addMenu("&File")
        self.action_preferences: QAction = self.menu_file.addAction(
            QIcon.fromTheme("preferences-other", icon("mdi6.cogs")),
            "&Preferences…",
        )
        self.action_preferences.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.action_preferences.setShortcut(QKeySequence.StandardKey.Preferences)
        self.menu_file.addSeparator()
        self.action_quit: QAction = self.menu_file.addAction(
            QIcon.fromTheme("application-exit", icon("mdi6.exit-to-app")),
            "&Quit",
        )
        self.action_quit.setMenuRole(QAction.MenuRole.QuitRole)
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.menu_help: QMenu = menu.addMenu("&Help")
        self.action_about: QAction = self.menu_help.addAction(
            QIcon.fromTheme(
                "help-about",
                icon("mdi6.information"),
            ),
            "&About",
        )
        self.action_about.setMenuRole(QAction.MenuRole.AboutRole)
        self.action_about.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.action_about_qt: QAction = self.menu_help.addAction(
            QIcon.fromTheme(
                "help-about-qt",
                QIcon(":/qt-project.org/q" "messagebox/images/qt" "logo-64.png"),
            ),
            "About &Qt",
        )
        self.action_about_qt.setMenuRole(QAction.MenuRole.AboutQtRole)

        self.table: QTableWidget = QTableWidget(self)
        self.table.setObjectName(self.table.__class__.__name__)
        layout.addWidget(self.table, 1)

        table_buttons: QHBoxLayout = QHBoxLayout()
        layout.addLayout(table_buttons, 0)
        self.button_move_row_up: QPushButton = QPushButton(
            icon("mdi6.arrow-up-bold-outline"), "Move &Up", self
        )
        table_buttons.addWidget(self.button_move_row_up)
        self.button_move_row_down: QPushButton = QPushButton(
            icon("mdi6.arrow-down-bold-outline"), "Move &Down", self
        )
        table_buttons.addWidget(self.button_move_row_down)
        table_buttons.addStretch()
        self.button_add_row: QPushButton = QPushButton(
            icon("mdi6.table-row-plus-after"), "&Add row", self
        )
        table_buttons.addWidget(self.button_add_row)
        self.button_del_row: QPushButton = QPushButton(
            icon("mdi6.table-row-remove"), "&Remove", self
        )
        table_buttons.addWidget(self.button_del_row)

        action_buttons: QDialogButtonBox = QDialogButtonBox()
        layout.addWidget(action_buttons, 0)
        self.button_save_diff: QPushButton = QPushButton(
            icon("mdi6.file-compare"), "Di&fference", self
        )
        action_buttons.addButton(
            self.button_save_diff, QDialogButtonBox.ButtonRole.ApplyRole
        )
        self.button_quit: QPushButton = QPushButton(
            QIcon.fromTheme("application-exit", icon("mdi6.exit-to-app")),
            "&Quit",
            self,
        )
        action_buttons.addButton(
            self.button_quit, QDialogButtonBox.ButtonRole.RejectRole
        )

        self.books: list[Book] = []
        self.sheets: list[QComboBox] = []
        self.columns: list[ColumnSelector] = []

        self._setup_appearance()
        self._setup_behavior()
        self.adjustSize()
        self._load_settings()

    def _setup_appearance(self) -> None:
        self.table.setColumnCount(len(Columns.__members__))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.button_del_row.setEnabled(False)
        self.button_move_row_up.setEnabled(False)
        self.button_move_row_down.setEnabled(False)
        self.button_save_diff.setEnabled(False)

        self.table.setHorizontalHeaderLabels(["File", "Sheet", "Columns"])
        self._install_translation()

    def _setup_translation(self) -> None:
        self.setWindowTitle(self.tr("Compare Lists of Lines"))

        self.menu_file.setTitle(self.tr("&File"))
        self.action_preferences.setText(self.tr("&Preferences…"))
        self.action_quit.setText(self.tr("&Quit"))
        self.menu_help.setTitle(self.tr("&Help"))
        self.action_about.setText(self.tr("&About"))
        self.action_about_qt.setText(self.tr("About &Qt"))

        self.button_move_row_up.setText(self.tr("Move &Up"))
        self.button_move_row_down.setText(self.tr("Move &Down"))
        self.button_add_row.setText(self.tr("&Add row"))
        self.button_del_row.setText(self.tr("&Remove"))

        self.button_save_diff.setText(self.tr("Di&fference"))
        self.button_quit.setText(self.tr("&Quit"))

        self.table.setHorizontalHeaderLabels(
            [self.tr("File"), self.tr("Sheet"), self.tr("Columns")]
        )

    def _setup_behavior(self) -> None:
        self.action_preferences.triggered.connect(self.on_action_preferences_triggered)
        self.action_quit.triggered.connect(self.close)
        self.action_about.triggered.connect(self.on_action_about_triggered)
        self.action_about_qt.triggered.connect(self.on_action_about_qt_triggered)
        self.button_add_row.clicked.connect(self.on_button_add_row_clicked)
        self.button_del_row.clicked.connect(self.on_button_del_row_clicked)
        self.button_move_row_up.clicked.connect(self.on_button_move_row_up_clicked)
        self.button_move_row_down.clicked.connect(self.on_button_move_row_down_clicked)
        self.table.itemSelectionChanged.connect(self.on_table_item_selection_changed)
        self.table.cellDoubleClicked.connect(self.on_table_cell_double_clicked)
        self.button_save_diff.clicked.connect(self.on_button_save_diff_clicked)
        self.button_quit.clicked.connect(self.close)

    def _load_settings(self) -> None:
        self.restoreState(self.settings.main_window_state)
        self.restoreGeometry(self.settings.main_window_geometry)
        self.table.restoreGeometry(self.settings.table_geometry)
        self.table.horizontalHeader().restoreState(self.settings.table_header_state)
        self.table.horizontalHeader().restoreGeometry(
            self.settings.table_header_geometry
        )
        ColumnSelector.last_time_principal_column = self.settings.principal_column
        ColumnSelector.last_time_selected_columns = self.settings.selected_columns

    def _save_settings(self) -> None:
        self.settings.table_geometry = self.table.saveGeometry()
        self.settings.table_header_state = self.table.horizontalHeader().saveState()
        self.settings.table_header_geometry = (
            self.table.horizontalHeader().saveGeometry()
        )
        self.settings.main_window_state = self.saveState()
        self.settings.main_window_geometry = self.saveGeometry()
        self.settings.principal_column = ColumnSelector.last_time_principal_column
        self.settings.selected_columns = ColumnSelector.last_time_selected_columns
        self.settings.sync()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        return super().closeEvent(event)

    def _enable_buttons(self) -> None:
        selected_ranges: list[QTableWidgetSelectionRange] = self.table.selectedRanges()
        self.button_save_diff.setEnabled(self.table.rowCount() > 1)
        self.button_del_row.setEnabled(bool(selected_ranges))
        self.button_move_row_up.setEnabled(
            bool(selected_ranges)
            and all(selected_range.topRow() > 0 for selected_range in selected_ranges)
        )
        self.button_move_row_down.setEnabled(
            bool(selected_ranges)
            and all(
                selected_range.bottomRow() < self.table.rowCount() - 1
                for selected_range in selected_ranges
            )
        )

    def _install_translation(self) -> None:
        qt_translations_path: str = QLibraryInfo.path(
            QLibraryInfo.LibraryPath.TranslationsPath
        )
        qt_translator: QTranslator
        translator: QTranslator
        if self.settings.translation_path is not None:
            translator = QTranslator(self)
            if translator.load(str(self.settings.translation_path)):
                new_locale: QLocale = QLocale(translator.language())

                # remove existing translators
                for child in self.children():
                    if isinstance(child, QTranslator) and child is not translator:
                        QApplication.removeTranslator(child)

                qt_translator = QTranslator(self)
                if qt_translator.load(new_locale, "qtbase", "_", qt_translations_path):
                    QApplication.installTranslator(qt_translator)

                QApplication.installTranslator(translator)
                self.setLocale(new_locale)
        else:
            current_locale: QLocale = self.locale()
            ui_languages: frozenset[str] = frozenset(
                [
                    *current_locale.uiLanguages(),
                    *map(lambda s: s.replace("-", "_"), current_locale.uiLanguages()),
                ]
            )
            for qm_file in find_qm_files(
                root=qt_translations_path, exclude=[sys.exec_prefix]
            ):
                qt_translator = QTranslator(self)
                if (
                    qt_translator.load(str(qm_file))
                    and qt_translator.language() in ui_languages
                ):
                    QApplication.installTranslator(qt_translator)
            for qm_file in find_qm_files(
                exclude=[qt_translations_path, sys.exec_prefix]
            ):
                translator = QTranslator(self)
                if (
                    translator.load(str(qm_file))
                    and translator.language() in ui_languages
                ):
                    QApplication.installTranslator(translator)
        self._setup_translation()

    @Slot()
    def on_button_add_row_clicked(self) -> None:
        filename: Path | None
        if not (filename := self.open_file_dialog.get_open_filename()):
            return
        data: bytes = filename.read_bytes()
        self.centralWidget().setDisabled(True)
        book: Book = get_book(file_content=data, file_type=filename.suffix.lstrip("."))
        self.centralWidget().setEnabled(True)
        book.filename = filename.name
        book.path = filename
        self.books.append(book)

        row: int
        selected_ranges: list[QTableWidgetSelectionRange] = self.table.selectedRanges()
        if selected_ranges:
            selected_range: QTableWidgetSelectionRange = selected_ranges[-1]
            row = selected_range.bottomRow() + 1
        else:
            row = self.table.rowCount()
        self.table.insertRow(row)

        item: QTableWidgetItem = QTableWidgetItem(book.filename)
        item.setToolTip(str(book.path))
        self.table.setItem(row, Columns.File, item)

        cb: QComboBox = QComboBox(self.table)
        self.sheets.append(cb)
        self.table.setCellWidget(row, Columns.Sheets, cb)

        cs: ColumnSelector = ColumnSelector(self.table)
        self.columns.append(cs)
        self.table.setCellWidget(row, Columns.Columns, cs)

        cb.currentTextChanged.connect(self.on_sheet_changed)
        cb.addItems(book.sheet_names())

        self._enable_buttons()

    @Slot()
    def on_button_del_row_clicked(self) -> None:
        row: int
        selected_range: QTableWidgetSelectionRange
        selected_ranges: list[QTableWidgetSelectionRange] = self.table.selectedRanges()
        for selected_range in selected_ranges:
            for row in xrange(selected_range.topRow(), selected_range.bottomRow()):
                self.table.removeRow(row)
                del self.books[row]
                del self.sheets[row]
                del self.columns[row]

        self._enable_buttons()

    @Slot()
    def on_button_move_row_up_clicked(self) -> None:
        selected_rows: set[int] = set()
        selected_range: QTableWidgetSelectionRange
        selected_ranges: list[QTableWidgetSelectionRange] = self.table.selectedRanges()
        for selected_range in selected_ranges:
            selected_rows.update(
                xrange(selected_range.topRow(), selected_range.bottomRow())
            )

        current_index: QModelIndex = self.table.currentIndex()

        for row in sorted(selected_rows):
            new_row: int = row - 1
            if new_row < 0:
                continue

            self.table.insertRow(new_row)
            # now, the row is (row + 1) in the table
            old_row: int = row + 1
            self.table.setItem(
                new_row,
                Columns.File,
                QTableWidgetItem(self.table.item(old_row, Columns.File)),
            )
            self.table.setCellWidget(
                new_row,
                Columns.Sheets,
                self.table.cellWidget(old_row, Columns.Sheets),
            )
            self.table.setCellWidget(
                new_row,
                Columns.Columns,
                self.table.cellWidget(old_row, Columns.Columns),
            )
            self.table.removeRow(old_row)

            self.books[row], self.books[new_row] = self.books[new_row], self.books[row]
            self.sheets[row], self.sheets[new_row] = (
                self.sheets[new_row],
                self.sheets[row],
            )
            self.columns[row], self.columns[new_row] = (
                self.columns[new_row],
                self.columns[row],
            )

        self.table.clearSelection()
        if current_index.row() in selected_rows:
            self.table.setCurrentIndex(
                current_index.siblingAtRow(current_index.row() - 1)
            )
        elif min(selected_rows) <= current_index.row() <= max(selected_rows):
            self.table.setCurrentIndex(
                current_index.siblingAtRow(current_index.row() + 1)
            )
        for selected_range in selected_ranges:
            self.table.setRangeSelected(
                QTableWidgetSelectionRange(
                    selected_range.topRow() - 1,
                    selected_range.leftColumn(),
                    selected_range.bottomRow() - 1,
                    selected_range.rightColumn(),
                ),
                True,
            )

    @Slot()
    def on_button_move_row_down_clicked(self) -> None:
        selected_rows: set[int] = set()
        selected_range: QTableWidgetSelectionRange
        selected_ranges: list[QTableWidgetSelectionRange] = self.table.selectedRanges()
        for selected_range in selected_ranges:
            selected_rows.update(
                xrange(selected_range.topRow(), selected_range.bottomRow())
            )

        current_index: QModelIndex = self.table.currentIndex()

        for row in sorted(selected_rows, reverse=True):
            # `row + 2` to insert a new row _after_ the next one
            new_row: int = row + 2
            if new_row > self.table.rowCount():
                continue

            self.table.insertRow(new_row)
            self.table.setItem(
                new_row,
                Columns.File,
                QTableWidgetItem(self.table.item(row, Columns.File)),
            )
            self.table.setCellWidget(
                new_row,
                Columns.Sheets,
                self.table.cellWidget(row, Columns.Sheets),
            )
            self.table.setCellWidget(
                new_row,
                Columns.Columns,
                self.table.cellWidget(row, Columns.Columns),
            )
            self.table.removeRow(row)

            new_row = row + 1
            self.books[row], self.books[new_row] = self.books[new_row], self.books[row]
            self.sheets[row], self.sheets[new_row] = (
                self.sheets[new_row],
                self.sheets[row],
            )
            self.columns[row], self.columns[new_row] = (
                self.columns[new_row],
                self.columns[row],
            )

        self.table.clearSelection()
        if current_index.row() in selected_rows:
            self.table.setCurrentIndex(
                current_index.siblingAtRow(current_index.row() + 1)
            )
        elif min(selected_rows) <= current_index.row() <= max(selected_rows):
            self.table.setCurrentIndex(
                current_index.siblingAtRow(current_index.row() - 1)
            )
        for selected_range in selected_ranges:
            self.table.setRangeSelected(
                QTableWidgetSelectionRange(
                    selected_range.topRow() + 1,
                    selected_range.leftColumn(),
                    selected_range.bottomRow() + 1,
                    selected_range.rightColumn(),
                ),
                True,
            )

    @Slot()
    def on_table_item_selection_changed(self) -> None:
        self._enable_buttons()

    @Slot(int, int)
    def on_table_cell_double_clicked(self, row: int, col: int) -> None:
        if col == Columns.File:
            filename: Path | None
            if not (filename := self.open_file_dialog.get_open_filename()):
                return
            data: bytes = filename.read_bytes()
            self.centralWidget().setDisabled(True)
            book: Book = get_book(
                file_content=data, file_type=filename.suffix.lstrip(".")
            )
            self.centralWidget().setEnabled(True)
            book.filename = filename.name
            book.path = filename

            self.books[row] = book

            self.table.item(row, Columns.File).setText(book.filename)
            self.table.item(row, Columns.File).setToolTip(str(book.path))

            cb: QComboBox = cast(QComboBox, self.table.cellWidget(row, Columns.Sheets))
            if book.sheet_names():
                # change the items, inform once everything's done
                cb.blockSignals(True)
                cb.clear()
                cb.blockSignals(False)
                cb.addItems(book.sheet_names())
            else:
                cb.clear()

    @Slot(str)
    def on_sheet_changed(self, sheet_name: str) -> None:
        cb: QComboBox = self.sender()
        row: int = self.sheets.index(cb)
        if not sheet_name:
            self.columns[row].columns = []
            return
        book: Book = self.books[row]
        sheet: Sheet = book[sheet_name]
        self.columns[row].columns = list(sheet.named_columns()) or [
            header
            for col in range(sheet.number_of_columns())
            if (header := sheet[0, col])
        ]

    @Slot()
    def on_button_save_diff_clicked(self) -> None:
        try:
            ignore_case: bool = self.settings.ignore_case
            merge_spaces: bool = self.settings.merge_spaces
            data: list[dict[tuple[str, ...], int]] = [
                read_sheet(
                    sheet=book[sheet_cb.currentText()],
                    selected_columns=cs.other_selected_columns,
                    principal_column=cs.principal_column,
                    ignore_case=ignore_case,
                    merge_spaces=merge_spaces,
                )
                for book, sheet_cb, cs in zip(self.books, self.sheets, self.columns)
            ]
            all_keys: frozenset[tuple[str, ...]] = frozenset(
                sum(([key for key in d.keys() if any(key)] for d in data), start=[])
            )
            if not all_keys:
                return
            longest_key_length: int = max(map(len, all_keys))

            base_data: dict[tuple[str, ...], int] = data[0]
            fns: list[str] = [
                (
                    self.tr("{} (base)").format(book.path)
                    if index == 0
                    else self.tr("{} differs by…").format(
                        book.path.relative_to(self.books[0].path.parent)
                    )
                )
                for index, book in enumerate(self.books)
            ]
            best_key_header: list[str] = [""] * longest_key_length
            for cs in self.columns:
                other_selected_columns: list[str] = cs.other_selected_columns
                if len(other_selected_columns) == longest_key_length:
                    best_key_header = other_selected_columns
            header: list[str] = best_key_header + fns
            diff: dict[tuple[str, ...], list[int]] = {}
            for key in all_keys:
                diff[key] = [base_data.get(key, 0)]
            for another_data in data[1:]:
                for key in all_keys:
                    with suppress(TypeError):
                        diff[key].append(
                            another_data.get(key, 0) - base_data.get(key, 0)
                        )

            sheet: Sheet = Sheet(name=self.tr("Difference"), colnames=header)
            for row, key in enumerate(all_keys):
                for col, k in enumerate(key):
                    sheet[row, col] = k
                for col, d in enumerate(diff[key], start=longest_key_length):
                    sheet[row, col] = d

            filename: Path | None
            if not (filename := self.save_file_dialog.get_save_filename()):
                return
            sheet_data: BytesIO = sheet.save_to_memory(filename.suffix.lstrip("."))
            self.centralWidget().setDisabled(True)
            try:
                filename.write_bytes(sheet_data.read())
            finally:
                self.centralWidget().setEnabled(True)
        except Exception as ex:
            QMessageBox.critical(self, ex.__class__.__name__, traceback.format_exc())
        else:
            QMessageBox.information(self, self.windowTitle(), self.tr("Done."))

    @Slot()
    def on_action_preferences_triggered(self) -> None:
        p: Preferences = Preferences(self.settings, self)
        last_translation: Path | None = self.settings.translation_path
        if p.exec() == Preferences.DialogCode.Accepted:
            if self.settings.translation_path != last_translation:
                self._install_translation()

    @Slot()
    def on_action_about_triggered(self) -> None:
        try:
            from _version import __version__
        except ImportError:
            __version__ = None

        QMessageBox.about(
            self,
            self.tr("About"),
            "<html><p>"
            + (
                (
                    self.tr("The application is version {0}").format(__version__)
                    + "</p><p>"
                )
                if __version__ is not None
                else ""
            )
            + self.tr(
                "The application compares tables and stores the difference of the selected columns."
            )
            + "</p><p>"
            + self.tr("The application is licensed under the {0}.").format(
                "<a href='https://www.gnu.org/copyleft/lesser.html'>{0}</a>".format(
                    self.tr("GNU LGPL version 3")
                )
            )
            + "</p><p>"
            + self.tr("The source code is available on {0}.").format(
                "<a href='https://github.com/StSav012/compare_tables'>GitHub</a>"
            )
            + "</p></html>",
        )

    @Slot()
    def on_action_about_qt_triggered(self) -> None:
        QMessageBox.aboutQt(self)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = UI()
    w.show()
    app.exec()
