import sys, os
import time
import threading
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QHBoxLayout,
    QGraphicsDropShadowEffect,
    QGraphicsView,
    QGraphicsScene,
    QSpinBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QFrame,
    QComboBox,
    QDialog,
    QProgressBar,
)
from PyQt5.QtGui import QPixmap, QFont, QCursor, QColor, QPen, QBrush
from PyQt5 import QtGui, QtCore
from algorithms.genetic import genetic_alg
from algorithms.hill_climbing import (
    hill_climbing,
    stochastic_hill_climbing,
    first_choice_hill_climbing,
    random_restart_hill_climbing,
)
from algorithms.simulated_annealing import simulated_annealing
from file_parser import parse_file

widgets = []
active_jobs = []
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
INPUT_DIR = os.path.join(PROJECT_ROOT, 'input')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
RUNTIME_HISTORY = {}

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle('Book Scanning')
window.resize(1700, 1020)
window.setMinimumSize(1360, 860)
window.setStyleSheet(
    'QWidget { '
    'background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2f2538, stop:0.5 #3f3150, stop:1 #2b344f); '
    '}'
)
window.setWindowIcon(QtGui.QIcon(os.path.join(ASSETS_DIR, 'books.png')))

layout = QVBoxLayout()
layout.setAlignment(QtCore.Qt.AlignCenter)

ALGORITHM_PARAMETER_SPECS = {
    'simulated_annealing': [
        {'name': 'initial_temp', 'label': 'Initial temperature', 'type': 'float', 'default': 1000.0, 'min': 0.1, 'max': 1000000.0, 'step': 10.0, 'decimals': 3},
        {'name': 'cooling_rate', 'label': 'Cooling rate', 'type': 'float', 'default': 0.995, 'min': 0.1, 'max': 0.999999, 'step': 0.001, 'decimals': 6},
        {'name': 'min_temp', 'label': 'Minimum temperature', 'type': 'float', 'default': 0.001, 'min': 0.0, 'max': 10.0, 'step': 0.001, 'decimals': 6},
        {'name': 'max_iter', 'label': 'Max iterations', 'type': 'int', 'default': 10000, 'min': 1, 'max': 1000000, 'step': 100},
    ],
    'hill_climbing': [
        {'name': 'max_iter', 'label': 'Max iterations', 'type': 'int', 'default': 100, 'min': 1, 'max': 1000000, 'step': 10},
    ],
    'genetic_algorithm': [
        {'name': 'pop_size', 'label': 'Population size', 'type': 'int', 'default': 50, 'min': 1, 'max': 1000, 'step': 10},
        {'name': 'generations', 'label': 'Generations', 'type': 'int', 'default': 100, 'min': 1, 'max': 100000, 'step': 10},
        {'name': 'mutation_rate', 'label': 'Mutation rate', 'type': 'float', 'default': 0.03, 'min': 0.0, 'max': 1.0, 'step': 0.01, 'decimals': 4},
        {'name': 'elite_individ', 'label': 'Elite individuals', 'type': 'int', 'default': 5, 'min': 1, 'max': 1000, 'step': 1},
    ],
}

HILL_CLIMBING_VARIANTS = {
    'hill_climbing': {
        'label': 'Basic Hill Climbing',
        'description': 'Generates one random neighbor per iteration and keeps it only if it improves the score.',
        'algorithm': hill_climbing,
        'params': [
            {'name': 'max_iter', 'label': 'Max iterations', 'type': 'int', 'default': 100, 'min': 1, 'max': 1000000, 'step': 10},
        ],
    },
    'stochastic_hill_climbing': {
        'label': 'Stochastic Hill Climbing',
        'description': 'Generates several better neighbors and randomly picks one of the best candidates.',
        'algorithm': stochastic_hill_climbing,
        'params': [
            {'name': 'it', 'label': 'Iterations', 'type': 'int', 'default': 100, 'min': 1, 'max': 1000000, 'step': 10},
            {'name': 'candidates', 'label': 'Candidate neighbors', 'type': 'int', 'default': 5, 'min': 1, 'max': 1000, 'step': 1},
        ],
    },
    'first_choice_hill_climbing': {
        'label': 'First Choice Hill Climbing',
        'description': 'Keeps searching until it reaches a streak of non-improving neighbors.',
        'algorithm': first_choice_hill_climbing,
        'params': [
            {'name': 'max_no_improvement', 'label': 'Max no improvement', 'type': 'int', 'default': 100, 'min': 1, 'max': 1000000, 'step': 10},
        ],
    },
    'random_restart_hill_climbing': {
        'label': 'Random Restart Hill Climbing',
        'description': 'Runs hill climbing multiple times from fresh random starts and keeps the best result.',
        'algorithm': random_restart_hill_climbing,
        'params': [
            {'name': 'restarts', 'label': 'Restarts', 'type': 'int', 'default': 10, 'min': 1, 'max': 100000, 'step': 1},
            {'name': 'max_iter', 'label': 'Max iterations per restart', 'type': 'int', 'default': 1000, 'min': 1, 'max': 1000000, 'step': 10},
        ],
    },
}


class AlgorithmWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal(dict)
    failed = QtCore.pyqtSignal(str)
    cancelled = QtCore.pyqtSignal()

    def __init__(self, algorithm, input_file, algorithm_name, algorithm_params=None, cancel_event=None):
        super().__init__()
        self.algorithm = algorithm
        self.input_file = input_file
        self.algorithm_name = algorithm_name
        self.algorithm_params = dict(algorithm_params or {})
        self.cancel_event = cancel_event

    @QtCore.pyqtSlot()
    def run(self):
        try:
            execution_params = dict(self.algorithm_params)
            execution_params.setdefault('stop_requested', lambda: self.cancel_event.is_set() if self.cancel_event else False)
            result = run_algorithm_from_input(
                self.algorithm,
                self.input_file,
                self.algorithm_name,
                execution_params,
            )
            if self.cancel_event and self.cancel_event.is_set():
                self.cancelled.emit()
                return
            self.finished.emit(result)
        except Exception as exc:
            if self.cancel_event and self.cancel_event.is_set():
                self.cancelled.emit()
                return
            self.failed.emit(str(exc))


class RunProgressDialog(QDialog):
    def __init__(self, parent, algorithm_name, estimated_seconds, on_cancel=None):
        super().__init__(parent)
        self.estimated_seconds = estimated_seconds
        self.start_time = time.perf_counter()
        self.on_cancel = on_cancel
        self.cancel_triggered = False

        self.setWindowTitle('Running Algorithm')
        self.setModal(True)
        self.setFixedWidth(520)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(
            'QDialog { background: #2f2538; border: 1px solid rgba(255,255,255,0.12); border-radius: 12px; }'
            'QLabel { color: #f2ecff; }'
            'QProgressBar { border: 1px solid rgba(255,255,255,0.25); border-radius: 8px; text-align: center; '
            'background: rgba(255,255,255,0.08); color: #f2ecff; height: 22px; }'
            'QProgressBar::chunk { background-color: #7d5a8a; border-radius: 7px; }'
        )

        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        dialog_layout.setSpacing(10)

        title = QLabel(f'Running {algorithm_name.replace("_", " ").title()}')
        title.setStyleSheet('font-size: 17px; font-weight: bold;')
        dialog_layout.addWidget(title)

        self.status_label = QLabel('Preparing execution...')
        self.status_label.setStyleSheet('font-size: 13px; color: #e8dcff;')
        self.status_label.setWordWrap(True)
        dialog_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        dialog_layout.addWidget(self.progress_bar)

        self.details_label = QLabel('Elapsed: 0.0 s')
        self.details_label.setStyleSheet('font-size: 12px; color: #cbb8e7;')
        dialog_layout.addWidget(self.details_label)

        self.cancel_button = QPushButton('Cancel Run')
        self.cancel_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.cancel_button.setStyleSheet(
            'QPushButton { color: white; background: #7d4b57; font-size: 14px; font-weight: bold; '
            'padding: 8px 14px; border-radius: 10px; } '
            'QPushButton:hover { background: #8a5662; } '
            'QPushButton:disabled { background: #5e4c63; color: #d0c1e0; }'
        )
        self.cancel_button.clicked.connect(self.request_cancel)
        dialog_layout.addWidget(self.cancel_button, alignment=QtCore.Qt.AlignRight)

        self.setLayout(dialog_layout)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self.refresh)

        if self.estimated_seconds and self.estimated_seconds > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText(f'Expected time: {self.estimated_seconds:.1f} s')
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText('Expected time: estimating from future runs...')

        self.timer.start()

    def refresh(self):
        elapsed = time.perf_counter() - self.start_time
        if self.estimated_seconds and self.estimated_seconds > 0:
            progress = min(95, int((elapsed / self.estimated_seconds) * 100))
            self.progress_bar.setValue(progress)
            remaining = max(0.0, self.estimated_seconds - elapsed)
            self.details_label.setText(f'Elapsed: {elapsed:.1f} s | ETA: {remaining:.1f} s')
        else:
            self.details_label.setText(f'Elapsed: {elapsed:.1f} s')

    def request_cancel(self):
        if self.cancel_triggered:
            return
        self.cancel_triggered = True
        self.status_label.setText('Cancelling... waiting for the current iteration to finish.')
        self.cancel_button.setEnabled(False)
        if self.on_cancel is not None:
            self.on_cancel()

    def closeEvent(self, event):
        if not self.cancel_triggered and self.on_cancel is not None:
            self.request_cancel()
        self.timer.stop()
        super().closeEvent(event)


def runtime_history_key(algorithm_name, input_file):
    return algorithm_name, os.path.basename(input_file)


def estimate_runtime_seconds(algorithm_name, input_file):
    key = runtime_history_key(algorithm_name, input_file)
    values = RUNTIME_HISTORY.get(key, [])
    if values:
        return sum(values) / len(values)

    fallback_values = []
    for (alg_name, _), runtimes in RUNTIME_HISTORY.items():
        if alg_name == algorithm_name:
            fallback_values.extend(runtimes)
    if fallback_values:
        return sum(fallback_values) / len(fallback_values)
    return None


def register_runtime_sample(algorithm_name, input_file, runtime_seconds):
    key = runtime_history_key(algorithm_name, input_file)
    samples = RUNTIME_HISTORY.setdefault(key, [])
    samples.append(float(runtime_seconds))
    if len(samples) > 8:
        del samples[0]

def clear_layout_items(target_layout):
    while target_layout.count():
        item = target_layout.takeAt(0)
        child_layout = item.layout()
        child_widget = item.widget()

        if child_layout is not None:
            clear_layout_items(child_layout)
        elif child_widget is not None:
            child_widget.setParent(None)
            child_widget.deleteLater()


def clear_widgets():
    global layout
    clear_layout_items(layout)
    widgets.clear()


def format_parameter_value(value):
    if isinstance(value, float):
        return f'{value:.6g}'
    return str(value)


def create_parameter_widget(spec):
    if spec['type'] == 'int':
        widget = QSpinBox()
        widget.setRange(spec.get('min', 0), spec.get('max', 1000000))
        widget.setSingleStep(spec.get('step', 1))
        widget.setValue(spec['default'])
    else:
        widget = QDoubleSpinBox()
        widget.setDecimals(spec.get('decimals', 3))
        widget.setRange(spec.get('min', 0.0), spec.get('max', 1000000.0))
        widget.setSingleStep(spec.get('step', 0.1))
        widget.setValue(spec['default'])

    widget.setStyleSheet('background: white; color: #231a2b; border-radius: 6px; padding: 4px;')
    return widget


def create_styled_combo_box():
    combo = QComboBox()
    combo.setStyleSheet(
        'QComboBox { background: white; color: #231a2b; border: 1px solid rgba(32, 24, 40, 0.15); '
        'border-radius: 10px; padding: 6px 10px; font-size: 14px; }'
        'QComboBox::drop-down { border: none; width: 28px; }'
        'QComboBox QAbstractItemView { background: white; color: #231a2b; selection-background-color: #d8d0ff; }'
    )
    return combo


def build_parameter_cards(specs, parameter_layout, parameter_widgets):
    for spec in specs:
        widget = create_parameter_widget(spec)
        parameter_widgets[spec['name']] = widget
        field_card = QFrame()
        field_card.setStyleSheet(
            'QFrame { background: rgba(255,255,255,0.92); border: 1px solid rgba(32, 24, 40, 0.08); '
            'border-radius: 14px; }'
        )
        field_layout = QVBoxLayout()
        field_layout.setContentsMargins(14, 12, 14, 12)
        field_layout.setSpacing(6)

        label_row = QHBoxLayout()
        label = QLabel(spec['label'])
        label.setStyleSheet('color: #281f33; font-size: 15px; font-weight: bold;')
        value_hint = QLabel(f'Default: {format_parameter_value(spec["default"])}')
        value_hint.setAlignment(QtCore.Qt.AlignRight)
        value_hint.setStyleSheet('color: #7a6f86; font-size: 12px;')
        label_row.addWidget(label)
        label_row.addStretch()
        label_row.addWidget(value_hint)

        descriptions = {
            'initial_temp': 'Higher values explore more aggressively at the start.',
            'cooling_rate': 'Closer to 1.0 slows cooling and keeps exploration longer.',
            'min_temp': 'Stops the search once the temperature becomes too low.',
            'mutation_rate': 'Controls how often children are mutated during reproduction.',
            'elite_individ': 'Keeps the best individuals directly in the next generation.',
            'max_iter': 'Raises the number of search iterations used by the algorithm.',
            'it': 'How many iterations the stochastic version should perform.',
            'candidates': 'How many better neighbors are sampled each iteration.',
            'max_no_improvement': 'Search stops after this many non-improving neighbors.',
            'restarts': 'Number of fresh hill climbing runs used to pick the best solution.',
        }

        description = QLabel(descriptions.get(spec['name'], ''))
        description.setWordWrap(True)
        description.setStyleSheet('color: #544a60; font-size: 12px;')

        field_layout.addLayout(label_row)
        field_layout.addWidget(description)
        field_layout.addWidget(widget)
        field_card.setLayout(field_layout)
        parameter_layout.addWidget(field_card)


def build_settings_header(input_file, algorithm_label, intro_text):
    image = QPixmap(os.path.join(ASSETS_DIR, 'books.png'))
    image = image.scaled(60, 60)
    logo = QLabel()
    logo.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    logo.setPixmap(image)
    logo.setAlignment(QtCore.Qt.AlignCenter)
    logo.setStyleSheet('margin-bottom: 20px;')
    widgets.append(logo)
    layout.addWidget(logo)
    logo.mousePressEvent = lambda _: algorithm_choice_menu(input_file)

    title = QLabel(f'{algorithm_label} Settings')
    title.setAlignment(QtCore.Qt.AlignCenter)
    title.setStyleSheet('font-size: 28px; font-weight: bold; color: white; margin-bottom: 8px;')
    widgets.append(title)
    layout.addWidget(title)

    subtitle = QLabel('Adjust the parameters before running the algorithm.')
    subtitle.setAlignment(QtCore.Qt.AlignCenter)
    subtitle.setStyleSheet('font-size: 16px; color: #f0e8ff; margin-bottom: 18px;')
    widgets.append(subtitle)
    layout.addWidget(subtitle)

    intro_card = QGroupBox()
    intro_card.setStyleSheet(
        'QGroupBox { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,45); '
        'border-radius: 18px; padding: 16px; }'
    )
    intro_layout = QVBoxLayout()
    intro_layout.setContentsMargins(18, 12, 18, 12)
    intro_layout.setSpacing(6)
    intro_title = QLabel('Tune the algorithm before running')
    intro_title.setAlignment(QtCore.Qt.AlignCenter)
    intro_title.setStyleSheet('font-size: 18px; font-weight: bold; color: white;')
    intro_label = QLabel(intro_text)
    intro_label.setAlignment(QtCore.Qt.AlignCenter)
    intro_label.setWordWrap(True)
    intro_label.setStyleSheet('font-size: 14px; color: #efe6ff; line-height: 1.4;')
    intro_layout.addWidget(intro_title)
    intro_layout.addWidget(intro_label)
    intro_card.setLayout(intro_layout)
    widgets.append(intro_card)
    layout.addWidget(intro_card)


def build_action_row(input_file, run_callback):
    action_row = QHBoxLayout()
    back_button = QPushButton('Back to Algorithms')
    back_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    back_button.setStyleSheet('QPushButton{ color: white; background: #5a445f; font-size: 16px; font-weight: bold; padding: 10px 16px; border-radius: 12px; } QPushButton:hover{background: #664d6c;}')
    back_button.clicked.connect(lambda: algorithm_choice_menu(input_file))

    run_button = QPushButton('Run Algorithm')
    run_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    run_button.setStyleSheet('QPushButton{ color: white; background: #684756; font-size: 16px; font-weight: bold; padding: 10px 16px; border-radius: 12px; } QPushButton:hover{background: #705665;}')
    run_button.clicked.connect(run_callback)

    action_row.addWidget(back_button)
    action_row.addStretch()
    action_row.addWidget(run_button)
    widgets.append(back_button)
    widgets.append(run_button)
    layout.addLayout(action_row)


def open_hill_climbing_settings(input_file):
    clear_widgets()
    build_settings_header(
        input_file,
        'Hill Climbing',
        'Choose a hill climbing variant and tune its parameters.'
    )

    selector_box = QGroupBox('Hill Climbing Variant')
    selector_box.setStyleSheet(
        'QGroupBox { color: white; font-size: 18px; font-weight: bold; border: 1px solid rgba(255,255,255,70); '
        'border-radius: 16px; margin-top: 16px; padding: 20px; background: rgba(255,255,255,0.06); }'
        'QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; }'
    )
    selector_layout = QVBoxLayout()
    selector_layout.setContentsMargins(6, 18, 6, 6)
    selector_layout.setSpacing(10)

    variant_combo = create_styled_combo_box()
    variant_combo.addItem('Basic Hill Climbing', 'hill_climbing')
    variant_combo.addItem('Stochastic Hill Climbing', 'stochastic_hill_climbing')
    variant_combo.addItem('First Choice Hill Climbing', 'first_choice_hill_climbing')
    variant_combo.addItem('Random Restart Hill Climbing', 'random_restart_hill_climbing')

    variant_description = QLabel()
    variant_description.setWordWrap(True)
    variant_description.setStyleSheet('color: #efe6ff; font-size: 13px;')

    selector_layout.addWidget(variant_combo)
    selector_layout.addWidget(variant_description)
    selector_box.setLayout(selector_layout)
    widgets.append(selector_box)
    layout.addWidget(selector_box)

    parameters_container = QGroupBox('Algorithm Parameters')
    parameters_container.setStyleSheet(
        'QGroupBox { color: white; font-size: 18px; font-weight: bold; border: 1px solid rgba(255,255,255,70); '
        'border-radius: 16px; margin-top: 16px; padding: 20px; background: rgba(255,255,255,0.06); }'
        'QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; }'
    )
    parameters_layout = QVBoxLayout()
    parameters_layout.setContentsMargins(6, 18, 6, 6)
    parameters_layout.setSpacing(12)
    parameters_container.setLayout(parameters_layout)
    widgets.append(parameters_container)
    layout.addWidget(parameters_container)

    parameter_widgets = {}

    def render_variant_fields():
        clear_layout_items(parameters_layout)
        parameter_widgets.clear()

        variant_key = variant_combo.currentData()
        variant_info = HILL_CLIMBING_VARIANTS[variant_key]
        variant_description.setText(variant_info['description'])

        build_parameter_cards(variant_info['params'], parameters_layout, parameter_widgets)
        parameters_layout.addStretch()

    variant_combo.currentIndexChanged.connect(render_variant_fields)
    render_variant_fields()

    def run_selected_variant():
        variant_key = variant_combo.currentData()
        variant_info = HILL_CLIMBING_VARIANTS[variant_key]
        params = {}
        for spec in variant_info['params']:
            value = parameter_widgets[spec['name']].value()
            params[spec['name']] = int(value) if spec['type'] == 'int' else float(value)
        apply_algorithm_and_show_results(variant_info['algorithm'], input_file, variant_key, params)

    build_action_row(input_file, run_selected_variant)


def open_algorithm_settings(input_file, algorithm_name, algorithm_label, algorithm):
    clear_widgets()

    image = QPixmap(os.path.join(ASSETS_DIR, 'books.png'))
    image = image.scaled(60, 60)
    logo = QLabel()
    logo.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    logo.setPixmap(image)
    logo.setAlignment(QtCore.Qt.AlignCenter)
    logo.setStyleSheet('margin-bottom: 20px;')
    widgets.append(logo)
    layout.addWidget(logo)
    logo.mousePressEvent = lambda _: algorithm_choice_menu(input_file)

    title = QLabel(f'{algorithm_label} Settings')
    title.setAlignment(QtCore.Qt.AlignCenter)
    title.setStyleSheet('font-size: 28px; font-weight: bold; color: white; margin-bottom: 8px;')
    widgets.append(title)
    layout.addWidget(title)

    subtitle = QLabel('Adjust the parameters before running the algorithm.')
    subtitle.setAlignment(QtCore.Qt.AlignCenter)
    subtitle.setStyleSheet('font-size: 16px; color: #f0e8ff; margin-bottom: 18px;')
    widgets.append(subtitle)
    layout.addWidget(subtitle)

    intro_card = QGroupBox()
    intro_card.setStyleSheet(
        'QGroupBox { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,45); '
        'border-radius: 18px; padding: 16px; }'
    )
    intro_layout = QVBoxLayout()
    intro_layout.setContentsMargins(18, 12, 18, 12)
    intro_layout.setSpacing(6)
    intro_title = QLabel('Tune the algorithm before running')
    intro_title.setAlignment(QtCore.Qt.AlignCenter)
    intro_title.setStyleSheet('font-size: 18px; font-weight: bold; color: white;')
    intro_text = QLabel('Each parameter changes the search behavior. Use the defaults as a baseline, then adjust the values to balance quality and runtime.')
    intro_text.setAlignment(QtCore.Qt.AlignCenter)
    intro_text.setWordWrap(True)
    intro_text.setStyleSheet('font-size: 14px; color: #efe6ff; line-height: 1.4;')
    intro_layout.addWidget(intro_title)
    intro_layout.addWidget(intro_text)
    intro_card.setLayout(intro_layout)
    widgets.append(intro_card)
    layout.addWidget(intro_card)

    parameter_box = QGroupBox('Algorithm Parameters')
    parameter_box.setStyleSheet(
        'QGroupBox { color: white; font-size: 18px; font-weight: bold; border: 1px solid rgba(255,255,255,70); '
        'border-radius: 16px; margin-top: 16px; padding: 20px; background: rgba(255,255,255,0.06); }'
        'QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; }'
    )
    parameter_layout = QVBoxLayout()
    parameter_layout.setContentsMargins(6, 18, 6, 6)
    parameter_layout.setSpacing(12)

    parameter_widgets = {}
    for spec in ALGORITHM_PARAMETER_SPECS.get(algorithm_name, []):
        widget = create_parameter_widget(spec)
        parameter_widgets[spec['name']] = widget
        field_card = QFrame()
        field_card.setStyleSheet(
            'QFrame { background: rgba(255,255,255,0.9); border: 1px solid rgba(32, 24, 40, 0.08); '
            'border-radius: 14px; }'
        )
        field_layout = QVBoxLayout()
        field_layout.setContentsMargins(14, 12, 14, 12)
        field_layout.setSpacing(6)

        label_row = QHBoxLayout()
        label = QLabel(spec['label'])
        label.setStyleSheet('color: #281f33; font-size: 15px; font-weight: bold;')
        value_hint = QLabel(f'Default: {format_parameter_value(spec["default"])}')
        value_hint.setAlignment(QtCore.Qt.AlignRight)
        value_hint.setStyleSheet('color: #7a6f86; font-size: 12px;')
        label_row.addWidget(label)
        label_row.addStretch()
        label_row.addWidget(value_hint)

        if spec['name'] in ('initial_temp', 'cooling_rate', 'min_temp'):
            description_text = {
                'initial_temp': 'Higher values explore more aggressively at the start.',
                'cooling_rate': 'Closer to 1.0 slows cooling and keeps exploration longer.',
                'min_temp': 'Stops the search once the temperature becomes too low.',
            }[spec['name']]
        elif spec['name'] == 'mutation_rate':
            description_text = 'Controls how often children are mutated during reproduction.'
        elif spec['name'] == 'elite_individ':
            description_text = 'Keeps the best individuals directly in the next generation.'
        else:
            description_text = 'Raises the number of search iterations used by the algorithm.'

        description = QLabel(description_text)
        description.setWordWrap(True)
        description.setStyleSheet('color: #544a60; font-size: 12px;')

        field_layout.addLayout(label_row)
        field_layout.addWidget(description)
        field_layout.addWidget(widget)
        field_card.setLayout(field_layout)
        parameter_layout.addWidget(field_card)

    parameter_layout.addStretch()

    parameter_box.setLayout(parameter_layout)
    widgets.append(parameter_box)
    layout.addWidget(parameter_box)

    action_row = QHBoxLayout()
    back_button = QPushButton('Back to Algorithms')
    back_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    back_button.setStyleSheet('QPushButton{ color: white; background: #5a445f; font-size: 16px; font-weight: bold; padding: 10px 16px; border-radius: 12px; } QPushButton:hover{background: #664d6c;}')
    back_button.clicked.connect(lambda: algorithm_choice_menu(input_file))

    run_button = QPushButton('Run Algorithm')
    run_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    run_button.setStyleSheet('QPushButton{ color: white; background: #684756; font-size: 16px; font-weight: bold; padding: 10px 16px; border-radius: 12px; } QPushButton:hover{background: #705665;}')

    def run_selected_algorithm():
        params = {}
        for spec in ALGORITHM_PARAMETER_SPECS.get(algorithm_name, []):
            value = parameter_widgets[spec['name']].value()
            if spec['type'] == 'int':
                params[spec['name']] = int(value)
            else:
                params[spec['name']] = float(value)
        apply_algorithm_and_show_results(algorithm, input_file, algorithm_name, params)

    run_button.clicked.connect(run_selected_algorithm)

    action_row.addWidget(back_button)
    action_row.addStretch()
    action_row.addWidget(run_button)
    widgets.append(back_button)
    widgets.append(run_button)
    layout.addLayout(action_row)

def show_main_menu(error=""):
    clear_widgets()
    main_menu(error)

def create_button(text):
    button = QPushButton(text)
    button.setFont(QFont('Segoe UI Black', 30))
    button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    button.setStyleSheet('QPushButton{ color: white; background: #684756; font-size: 30px; font-weight: bold; padding: 15px 30px; border-radius: 25px; margin-bottom: 20px; } QPushButton:hover{background: #705665;}')
    return button


def format_books_preview(book_ids, max_items=20):
    if len(book_ids) <= max_items:
        return ' '.join(map(str, book_ids))
    return ' '.join(map(str, book_ids[:max_items])) + f' ... (+{len(book_ids) - max_items})'


def build_visualization_data(solution, deadline):
    scanned_books = set()
    current_day = 0
    day_shipments = {}
    library_summary = []
    total_score = 0
    total_books_sent = 0

    for lib in solution:
        current_day += lib.sign_up_time
        signup_start_day = current_day - lib.sign_up_time
        signup_end_day = current_day
        if signup_end_day >= deadline:
            break

        days_left = deadline - signup_end_day
        max_books = days_left * lib.shipping_cap
        if max_books <= 0:
            continue

        books_to_scan = []
        for book in lib.books:
            if book.id in scanned_books:
                continue
            scanned_books.add(book.id)
            books_to_scan.append(book.id)
            if len(books_to_scan) >= max_books:
                break

        if not books_to_scan:
            continue

        lib_score = 0
        shipments_by_day = {}
        for idx, book_id in enumerate(books_to_scan):
            day = signup_end_day + (idx // lib.shipping_cap)
            if day >= deadline:
                break
            day_shipments.setdefault(day, []).append((lib.id, book_id))
            shipments_by_day[day] = shipments_by_day.get(day, 0) + 1

        for book in lib.books:
            if book.id in books_to_scan:
                lib_score += book.score

        total_score += lib_score
        total_books_sent += len(books_to_scan)

        library_summary.append(
            {
                'library_id': lib.id,
                'signup_start_day': signup_start_day,
                'signup_end_day': signup_end_day,
                'books_sent': len(books_to_scan),
                'score': lib_score,
                'shipping_cap': lib.shipping_cap,
                'shipments_by_day': shipments_by_day,
                'first_ship_day': signup_end_day,
                'last_ship_day': signup_end_day + ((len(books_to_scan) - 1) // lib.shipping_cap),
            }
        )

    day_summary = []
    for day in sorted(day_shipments.keys()):
        entries = day_shipments[day]
        libs_on_day = set(lib_id for lib_id, _ in entries)
        day_summary.append((day, len(entries), len(libs_on_day)))

    return {
        'day_shipments': day_shipments,
        'day_summary': day_summary,
        'library_summary': library_summary,
        'total_score': total_score,
        'total_books_sent': total_books_sent,
        'libraries_used': len(library_summary),
    }


def build_submission(solution, deadline):
    selected = []
    current_day = 0
    scanned_books = set()

    for lib in solution:
        current_day += lib.sign_up_time
        if current_day >= deadline:
            break

        days_left = deadline - current_day
        max_books = days_left * lib.shipping_cap

        books_to_scan = []
        for book in lib.books:
            if book.id in scanned_books:
                continue

            scanned_books.add(book.id)
            books_to_scan.append(book.id)
            if len(books_to_scan) >= max_books:
                break

        if books_to_scan:
            selected.append((lib.id, books_to_scan))

    return selected


def save_solution(input_file, algorithm_name, solution, deadline):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_path = os.path.join(OUTPUT_DIR, f'{base_name}_{algorithm_name}.out')
    submission = build_submission(solution, deadline)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f'{len(submission)}\n')
        for lib_id, books in submission:
            f.write(f'{lib_id} {len(books)}\n')
            f.write(' '.join(map(str, books)) + '\n')

    return output_path


def run_algorithm_from_input(algorithm, input_file, algorithm_name, algorithm_params=None):
    all_books, libraries, deadline = parse_file(input_file)
    algorithm_params = dict(algorithm_params or {})
    display_params = {k: v for k, v in algorithm_params.items() if k != 'stop_requested'}
    start_time = time.perf_counter()
    solution, score = algorithm(libraries, deadline, **algorithm_params)
    elapsed_time = time.perf_counter() - start_time
    output_path = save_solution(input_file, algorithm_name, solution, deadline)
    visualization = build_visualization_data(solution, deadline)
    return {
        'score': score,
        'output_path': output_path,
        'algorithm_name': algorithm_name,
        'deadline': deadline,
        'num_books': len(all_books),
        'num_libraries': len(libraries),
        'visualization': visualization,
        'elapsed_time': elapsed_time,
        'parameters': display_params,
    }

def import_libraries():
    filename = QFileDialog.getOpenFileName(window, 'Import Libraries', INPUT_DIR, 'Input Files (*.in)')[0]
    if filename:
        clear_widgets()

        try:
            all_books, libraries, num_days = parse_file(filename)
            library_menu(len(all_books), len(libraries), num_days, filename)
        except Exception as exc:
            show_main_menu(f'Error: {exc}')


def apply_algorithm_and_show_results(algorithm, input_file, algorithm_name, algorithm_params=None):
    estimated_seconds = estimate_runtime_seconds(algorithm_name, input_file)
    cancel_event = threading.Event()

    def request_cancel():
        cancel_event.set()

    progress_dialog = RunProgressDialog(window, algorithm_name, estimated_seconds, on_cancel=request_cancel)

    worker_thread = QtCore.QThread(window)
    worker = AlgorithmWorker(algorithm, input_file, algorithm_name, algorithm_params, cancel_event=cancel_event)
    worker.moveToThread(worker_thread)

    show_timer = QtCore.QTimer(window)
    show_timer.setSingleShot(True)

    job = {
        'thread': worker_thread,
        'worker': worker,
        'dialog': progress_dialog,
        'show_timer': show_timer,
        'cancel_event': cancel_event,
    }
    active_jobs.append(job)

    def cleanup_job():
        if show_timer.isActive():
            show_timer.stop()
        progress_dialog.close()
        if job in active_jobs:
            active_jobs.remove(job)

    def on_success(result):
        register_runtime_sample(algorithm_name, input_file, result['elapsed_time'])
        cleanup_job()
        show_result_visualization(result)

    def on_error(error_message):
        cleanup_job()
        show_main_menu(f'Error: {error_message}')

    def on_cancelled():
        cleanup_job()
        show_main_menu('Run cancelled by user.')

    show_timer.timeout.connect(lambda: progress_dialog.show() if worker_thread.isRunning() else None)
    show_timer.start(350)

    worker_thread.started.connect(worker.run)
    worker.finished.connect(on_success)
    worker.failed.connect(on_error)
    worker.cancelled.connect(on_cancelled)

    worker.finished.connect(worker_thread.quit)
    worker.failed.connect(worker_thread.quit)
    worker.cancelled.connect(worker_thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker.failed.connect(worker.deleteLater)
    worker.cancelled.connect(worker.deleteLater)
    worker_thread.finished.connect(worker_thread.deleteLater)

    worker_thread.start()


def show_result_visualization(result):
    clear_widgets()

    viz = result['visualization']

    page = QWidget()
    page_layout = QVBoxLayout()
    page_layout.setContentsMargins(12, 12, 12, 12)
    page_layout.setSpacing(10)

    graph = QGraphicsView()
    
    
    
    def wheelEvent(event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            graph.scale(zoom_in_factor, zoom_in_factor)
        else:
            graph.scale(zoom_out_factor, zoom_out_factor)

    graph.wheelEvent = wheelEvent
    
    graph.setMinimumHeight(1020)
    graph.setStyleSheet('background: #f8f9fc; border: 1px solid #d6d9e8; border-radius: 10px;')
    graph.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing)
    graph.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    graph.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    graph.setDragMode(QGraphicsView.ScrollHandDrag)
    page_layout.addWidget(graph, 1)

    score_header = QLabel(f'Algorithm: {result["algorithm_name"].replace("_", " ").title()} | Total Score: {result["score"]}')
    score_header.setStyleSheet('font-size: 16px; font-weight: bold; color: #000008; background: rgba(255,255,255,0.1); padding: 10px 12px; border-radius: 8px;')
    page_layout.addWidget(score_header)

    parameter_parts = [f'{name.replace("_", " ").title()}: {format_parameter_value(value)}' for name, value in result.get('parameters', {}).items()]
    runtime_text = f'Run time: {result["elapsed_time"]:.3f} s'
    if parameter_parts:
        runtime_text += ' | Parameters: ' + ', '.join(parameter_parts)
    runtime_label = QLabel(runtime_text)
    runtime_label.setStyleSheet('font-size: 15px; font-weight: bold; color: #000008; background: rgba(255,255,255,0.08); padding: 10px 12px; border-radius: 8px;')
    runtime_label.setWordWrap(True)
    page_layout.addWidget(runtime_label)

    legend = QLabel(
        'Bar description: Orange horizontal bar = library signup period (days spent preparing that library).\n'
        'Green vertical bars = books shipped that day for that library; bars are scaled against the largest daily shipping capacity in the solution.'
    )
    legend.setStyleSheet('font-size: 15px; font-weight: bold; color: #000008; background: rgba(255,255,255,0.08); padding: 10px 12px; border-radius: 8px;')
    legend.setWordWrap(True)
    page_layout.addWidget(legend)

    all_rows = viz['library_summary']
    libs_per_page = 10
    total_pages = max(1, (len(all_rows) + libs_per_page - 1) // libs_per_page)
    total_days = max(1, result['deadline'])
    days_per_page = 120
    total_day_pages = max(1, (total_days + days_per_page - 1) // days_per_page)

    pagination_layout = QHBoxLayout()
    page_label = QLabel(f'Page: ')
    page_label.setStyleSheet('font-size: 14px; color: white;')
    page_spin = QSpinBox()
    page_spin.setMinimum(1)
    page_spin.setMaximum(total_pages)
    page_spin.setValue(1)
    page_spin.setStyleSheet('background: white; color: #231a2b; border-radius: 6px; padding: 4px;')
    page_info = QLabel(f'of {total_pages} ({len(all_rows)} libraries total)')
    page_info.setStyleSheet('font-size: 14px; color: #f3e9ff;')
    pagination_layout.addWidget(page_label)
    pagination_layout.addWidget(page_spin)
    pagination_layout.addWidget(page_info)
    day_page_label = QLabel('Day Page: ')
    day_page_label.setStyleSheet('font-size: 14px; color: white;')
    day_page_spin = QSpinBox()
    day_page_spin.setMinimum(1)
    day_page_spin.setMaximum(total_day_pages)
    day_page_spin.setValue(1)
    day_page_spin.setStyleSheet('background: white; color: #231a2b; border-radius: 6px; padding: 4px;')
    day_page_info = QLabel(f'of {total_day_pages} ({days_per_page} days per page)')
    day_page_info.setStyleSheet('font-size: 14px; color: #f3e9ff;')
    pagination_layout.addWidget(day_page_label)
    pagination_layout.addWidget(day_page_spin)
    pagination_layout.addWidget(day_page_info)
    pagination_layout.addStretch()
    page_layout.addLayout(pagination_layout)

    def render_timeline():
        scene = QGraphicsScene()

        if not all_rows:
            scene.addText('No libraries were selected by this solution.')
            graph.setScene(scene)
            return

        current_page = page_spin.value()
        start_idx = (current_page - 1) * libs_per_page
        end_idx = min(start_idx + libs_per_page, len(all_rows))
        visible_rows = all_rows[start_idx:end_idx]
        global_max_daily_cap = max(1, max((row['shipping_cap'] for row in all_rows), default=1))
        current_day_page = day_page_spin.value()
        day_start = (current_day_page - 1) * days_per_page
        day_end = min(day_start + days_per_page, total_days)
        visible_days = max(1, day_end - day_start)

        left_pad = 136
        top_pad = 22
        if len(visible_rows) <= 150:
            row_h = 60
        elif len(visible_rows) <= 1000:
            row_h = 40
        else:
            row_h = 25

        if result['deadline'] <= 300:
            day_w = 40
        elif result['deadline'] <= 1000:
            day_w = 25  
        else:
            day_w = 15

        width = left_pad + visible_days * day_w + 100
        height = top_pad + len(visible_rows) * row_h + 74
        scene.setSceneRect(0, 0, width, height)

        axis_pen = QPen(QColor(56, 59, 89))
        axis_pen.setWidth(1)
        scene.addLine(left_pad, top_pad, left_pad, height - 45, axis_pen)
        scene.addLine(left_pad, height - 45, width - 20, height - 45, axis_pen)

        x_title = scene.addText('Days')
        x_title.setDefaultTextColor(QColor(56, 59, 89))
        x_title.setPos(width - 70, height - 40)

        y_title = scene.addText('Libraries')
        y_title.setDefaultTextColor(QColor(56, 59, 89))
        y_title.setPos(8, 0)

        tick_target = 12
        tick_step = max(1, visible_days // tick_target)
        for day in range(day_start, day_end, tick_step):
            x = left_pad + (day - day_start) * day_w
            scene.addLine(x, top_pad, x, height - 45, QPen(QColor(223, 226, 239)))
            scene.addLine(x, height - 45, x, height - 40, axis_pen)
            label = scene.addText(str(day))
            label.setDefaultTextColor(QColor(95, 100, 132))
            label.setPos(x - 8, height - 38)

        for idx, lib in enumerate(visible_rows):
            y = top_pad + idx * row_h
            lib_id = lib['library_id']
            signup_start = lib['signup_start_day']
            signup_end = lib['signup_end_day']
            lane_top = y + 2
            lane_height = max(4, row_h - 4)
            lane_bottom = lane_top + lane_height

            id_label = scene.addText(str(lib_id))
            id_label.setFont(QFont('Arial', 12, QFont.Bold)) # Make the Y-axis labels bigger
            id_label.setPos(10, y + (row_h // 4))

            if idx % 2 == 0:
                scene.addRect(
                    left_pad,
                    y,
                    width - left_pad - 20,
                    row_h,
                    QPen(QtCore.Qt.NoPen),
                    QBrush(QColor(239, 242, 252, 170)),
                )

            signup_visible_start = max(signup_start, day_start)
            signup_visible_end = min(signup_end, day_end)
            if signup_visible_end > signup_visible_start:
                sx = left_pad + (signup_visible_start - day_start) * day_w
                sw = max(3, (signup_visible_end - signup_visible_start) * day_w)
                signup_rect = scene.addRect(
                    sx,
                    lane_top,
                    sw,
                    lane_height,
                    QPen(QColor(196, 106, 0, 200)),
                    QBrush(QColor(255, 171, 64, 220)),
                )
                signup_rect.setToolTip(f'Library {lib_id}\nSignup: day {signup_start} to {signup_end - 1}')

            for day, sent_count in lib['shipments_by_day'].items():
                if day < day_start or day >= day_end:
                    continue

                x = left_pad + (day - day_start) * day_w + 1
                cap = max(1, lib['shipping_cap'])
                usage = sent_count / global_max_daily_cap
                clamped_usage = max(0.0, min(1.0, usage))
                h = int(round(lane_height * clamped_usage))
                if sent_count > 0 and h == 0:
                    h = 1
                if clamped_usage >= 1.0:
                    h = lane_height
                ship_w = max(2, day_w - 2)
                shipment_rect = scene.addRect(
                    x,
                    lane_bottom - h,
                    ship_w,
                    h,
                    QPen(QColor(23, 128, 67, 200)),
                    QBrush(QColor(46, 204, 113, 230)),
                )
                shipment_rect.setToolTip(
                    f'Library {lib_id} | Day {day}\nBooks sent: {sent_count}\nLibrary capacity: {cap}\nScaled against max daily capacity: {global_max_daily_cap}'
                )

                if sent_count > 0 and day_w >= 12 and row_h >= 22:
                    txt = scene.addText(str(sent_count))
                    txt.setDefaultTextColor(QColor(14, 74, 38))
                    
                    # Calculate bar center coordinates
                    bar_center_x = x + ship_w / 2
                    bar_center_y = (lane_bottom - h) + h / 2
                    
                    # Get text bounding rect to center it properly
                    txt_rect = txt.boundingRect()
                    
                    # Position text so its center aligns with bar center
                    txt.setPos(bar_center_x - txt_rect.width() / 2, bar_center_y - txt_rect.height() / 2)

        graph.setScene(scene)

    page_spin.valueChanged.connect(render_timeline)
    day_page_spin.valueChanged.connect(render_timeline)
    render_timeline()

    action_row = QHBoxLayout()
    back_button = QPushButton('Back to Main Menu')
    back_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    back_button.setStyleSheet('QPushButton{ color: white; background: #684756; font-size: 16px; font-weight: bold; padding: 10px 16px; border-radius: 12px; } QPushButton:hover{background: #705665;}')
    back_button.clicked.connect(lambda: show_main_menu())
    action_row.addStretch()
    action_row.addWidget(back_button)
    page_layout.addLayout(action_row)

    page.setLayout(page_layout)
    widgets.append(page)
    layout.addWidget(page)

def algorithm_choice_menu(input_file):
    clear_widgets()
    
    image = QPixmap(os.path.join(ASSETS_DIR, 'books.png'))
    image = image.scaled(60, 60)
    logo = QLabel()
    logo.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    logo.setPixmap(image)
    logo.setAlignment(QtCore.Qt.AlignCenter)
    logo.setStyleSheet('margin-bottom: 20px;')
    widgets.append(logo)
    layout.addWidget(logo)
    
    logo.mousePressEvent = lambda _: show_main_menu()
    
    label = QLabel("Choose an algorithm")
    label.setAlignment(QtCore.Qt.AlignCenter)
    label.setStyleSheet('font-size: 25px; color: white;')
    widgets.append(label)
    layout.addWidget(label)

    simulated_annealing_button = create_button('Simulated Annealing Algorithm')
    simulated_annealing_button.clicked.connect(lambda: open_algorithm_settings(input_file, 'simulated_annealing', 'Simulated Annealing Algorithm', simulated_annealing))
    widgets.append(simulated_annealing_button)
    layout.addWidget(simulated_annealing_button, alignment=QtCore.Qt.AlignCenter)
    
    hill_climbing_button = create_button('Hill Climbing Algorithm')
    hill_climbing_button.clicked.connect(lambda: open_hill_climbing_settings(input_file))
    widgets.append(hill_climbing_button)
    layout.addWidget(hill_climbing_button, alignment=QtCore.Qt.AlignCenter)
    
    genetic_algorithm_button = create_button('Genetic Algorithm')
    genetic_algorithm_button.clicked.connect(lambda: open_algorithm_settings(input_file, 'genetic_algorithm', 'Genetic Algorithm', genetic_alg))
    widgets.append(genetic_algorithm_button)
    layout.addWidget(genetic_algorithm_button, alignment=QtCore.Qt.AlignCenter)

def main_menu(error=""):
    image = QPixmap(os.path.join(ASSETS_DIR, 'books.png'))
    image = image.scaled(120, 120)
    logo = QLabel()
    logo.setPixmap(image)
    logo.setStyleSheet('margin-left: 120px; margin-bottom: 20px;')
    widgets.append(logo)

    title = QLabel('Book Scanning')
    title.setStyleSheet('font-size: 50px; font-weight: bold; color: white; margin-right: 120px; margin-bottom: 20px;')
    title.setFont(QFont('Segoe UI Black', 50))
    widgets.append(title)

    title_box = QHBoxLayout()
    title_box.addWidget(logo)
    title_box.addWidget(title)
    layout.addLayout(title_box)

    import_button = create_button('Import Libraries')
    import_button.clicked.connect(import_libraries)
    widgets.append(import_button)
    layout.addWidget(import_button, alignment=QtCore.Qt.AlignCenter)
    
    if error:
        error_label = QLabel(error)
        color = 'red' if 'Error' in error else 'green'
        error_label.setStyleSheet(f'font-size: 20px; font-weight: bold; color: {color}; margin-bottom: 20px;')
        widgets.append(error_label)
        layout.addWidget(error_label, alignment=QtCore.Qt.AlignCenter)

    quit_button = create_button('Quit')
    quit_button.clicked.connect(app.quit)
    widgets.append(quit_button)
    layout.addWidget(quit_button, alignment=QtCore.Qt.AlignCenter)
    
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(30)
    effect.setColor(QColor(0, 0, 0, 50))
    effect.setOffset(0, 4)
    import_button.setGraphicsEffect(effect)
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(30)
    effect.setColor(QColor(0, 0, 0, 50))
    effect.setOffset(0, 4)
    quit_button.setGraphicsEffect(effect)
    
def library_menu(num_books, num_libraries, num_days, input_name):  
    # logo
    image = QPixmap(os.path.join(ASSETS_DIR, 'books.png'))
    image = image.scaled(60, 60)
    logo = QLabel()
    logo.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
    logo.setPixmap(image)
    logo.setAlignment(QtCore.Qt.AlignCenter)
    logo.setStyleSheet('margin-bottom: 20px;')
    widgets.append(logo)
    layout.addWidget(logo)
    
    logo.mousePressEvent = lambda _: show_main_menu()
    
    # general info  
    general_info = QLabel(f'Number of books: {num_books}\nNumber of libraries: {num_libraries}\nNumber of days: {num_days}')
    general_info.setStyleSheet('font-size: 25px; font-weight: bold; color: white; margin-bottom: 20px;')
    general_info.setAlignment(QtCore.Qt.AlignCenter)
    widgets.append(general_info)
    layout.addWidget(general_info)
    
    # scan button
    scan_button = create_button('Apply Algorithm')
    scan_button.clicked.connect(lambda: algorithm_choice_menu(input_name))
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(30)
    effect.setColor(QColor(0, 0, 0, 50))
    effect.setOffset(0, 4)
    scan_button.setGraphicsEffect(effect)
    widgets.append(scan_button)
    layout.addWidget(scan_button, alignment=QtCore.Qt.AlignRight)

main_menu()

window.setLayout(layout)

window.show()
sys.exit(app.exec())