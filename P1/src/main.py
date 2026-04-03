import sys, os
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
    QPlainTextEdit,
)
from PyQt5.QtGui import QPixmap, QFont, QCursor, QColor, QPen, QBrush
from PyQt5 import QtGui, QtCore
from algorithms.genetic import genetic_alg
from algorithms.hill_climbing import hill_climbing
from algorithms.simulated_annealing import simulated_annealing
from file_parser import parse_file

widgets = []
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
INPUT_DIR = os.path.join(PROJECT_ROOT, 'input')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

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

def clear_widgets():
    global layout
    for widget in widgets:
        if isinstance(widget, QWidget):
            layout.removeWidget(widget)
            widget.deleteLater()
    widgets.clear()

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


def run_algorithm_from_input(algorithm, input_file, algorithm_name):
    all_books, libraries, deadline = parse_file(input_file)
    solution, score = algorithm(libraries, deadline)
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


def apply_algorithm_and_show_results(algorithm, input_file, algorithm_name):
    try:
        result = run_algorithm_from_input(algorithm, input_file, algorithm_name)
        show_result_visualization(result)
    except Exception as exc:
        show_main_menu(f'Error: {exc}')


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

    legend = QLabel(
        'Bar description: Orange horizontal bar = library signup period (days spent preparing that library).\n'
        'Green vertical bars = books shipped that day for that library; taller green bar means more books sent on that day.'
    )
    legend.setStyleSheet('font-size: 15px; font-weight: bold; color: #000008; background: rgba(255,255,255,0.08); padding: 10px 12px; border-radius: 8px;')
    legend.setWordWrap(True)
    page_layout.addWidget(legend)

    def render_timeline():
        scene = QGraphicsScene()

        all_rows = viz['library_summary']
        if not all_rows:
            scene.addText('No libraries were selected by this solution.')
            graph.setScene(scene)
            return

        visible_rows = all_rows
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

        total_days = max(1, result['deadline'])

        width = left_pad + total_days * day_w + 100
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
        tick_step = max(1, total_days // tick_target)
        for day in range(0, total_days, tick_step):
            x = left_pad + day * day_w
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

            sx = left_pad + signup_start * day_w
            sw = max(3, (signup_end - signup_start) * day_w)
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
                x = left_pad + day * day_w + 1
                cap = max(1, lib['shipping_cap'])
                usage = min(1.0, sent_count / cap)
                h = max(6, int(lane_height * usage))
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
                    f'Library {lib_id} | Day {day}\nBooks sent: {sent_count}\nCapacity: {cap} ({int(usage * 100)}%)'
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
    simulated_annealing_button.clicked.connect(lambda: apply_algorithm_and_show_results(simulated_annealing, input_file, 'simulated_annealing'))
    widgets.append(simulated_annealing_button)
    layout.addWidget(simulated_annealing_button, alignment=QtCore.Qt.AlignCenter)
    
    hill_climbing_button = create_button('Hill Climbing Algorithm')
    hill_climbing_button.clicked.connect(lambda: apply_algorithm_and_show_results(hill_climbing, input_file, 'hill_climbing'))
    widgets.append(hill_climbing_button)
    layout.addWidget(hill_climbing_button, alignment=QtCore.Qt.AlignCenter)
    
    genetic_algorithm_button = create_button('Genetic Algorithm')
    genetic_algorithm_button.clicked.connect(lambda: apply_algorithm_and_show_results(genetic_alg, input_file, 'genetic_algorithm'))
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