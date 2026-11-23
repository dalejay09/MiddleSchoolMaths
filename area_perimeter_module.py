import streamlit as st
import random
import math
import io
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages

import ai_marking_component

# --- GEOMETRY ENGINE ---

def get_grid_locked_rect(grid_w, grid_h, require_pythagorean=False, max_dim=9):
    """
    Generates a rectangle (or square) whose 4 vertices lie strictly on integer grid coordinates.
    Returns a dict with vertices, exact integer area, exact integer perimeter (if Pythagorean),
    and internal decomposition lines.
    """
    if require_pythagorean:
        # Pythagorean triples (a, b, c) so side lengths are clean integers
        # Scaled by small multipliers so they fit comfortably on a 12x12 grid
        base_vectors = [(3, 4, 5), (4, 3, 5)]
        vx, vy, side_unit = random.choice(base_vectors)
        m1 = 1
        m2 = random.choice([1, 2])
    else:
        # Primitive vectors (dx, dy) with dx > 0, dy > 0 for clear grid decomposition
        base_vectors = [(1, 1), (1, 2), (2, 1), (1, 3), (3, 1), (2, 3), (3, 2)]
        vx, vy = random.choice(base_vectors)
        side_unit = math.hypot(vx, vy)
        # Keep dimensions reasonable for middle-school counting
        max_m1 = max(1, min(3, int(max_dim // max(vx, vy))))
        max_m2 = max(1, min(3, int(max_dim // max(vx, vy))))
        m1 = random.randint(1, max_m1)
        m2 = random.randint(1, max_m2)

    # Edge vectors
    u = (m1 * vx, m1 * vy)
    v = (-m2 * vy, m2 * vx)

    # Bounding box offsets relative to P0 = (x0, y0)
    # P0 = (0,0), P1 = u, P2 = u + v, P3 = v
    xs = [0, u[0], u[0] + v[0], v[0]]
    ys = [0, u[1], u[1] + v[1], v[1]]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    span_x = max_x - min_x
    span_y = max_y - min_y

    if span_x > grid_w - 2 or span_y > grid_h - 2:
        # Fallback to a clean 1x1 tilted square if dimensions exceed grid
        vx, vy, side_unit = 1, 1, math.sqrt(2)
        m1, m2 = random.randint(1, 2), random.randint(1, 2)
        u = (m1 * vx, m1 * vy)
        v = (-m2 * vy, m2 * vx)
        xs = [0, u[0], u[0] + v[0], v[0]]
        ys = [0, u[1], u[1] + v[1], v[1]]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max_x - min_x
        span_y = max_y - min_y

    # Choose random top-left anchor inside grid margins
    shift_x = random.randint(1, grid_w - 1 - span_x) - min_x
    shift_y = random.randint(1, grid_h - 1 - span_y) - min_y

    verts = [
        (shift_x + xs[0], shift_y + ys[0]),
        (shift_x + xs[1], shift_y + ys[1]),
        (shift_x + xs[2], shift_y + ys[2]),
        (shift_x + xs[3], shift_y + ys[3]),
    ]

    # Exact Area = |u x v| = (m1*vx)*(m2*vx) - (m1*vy)*(-m2*vy) = m1 * m2 * (vx^2 + vy^2)
    area = m1 * m2 * (vx**2 + vy**2)
    perimeter = int(round(2 * (m1 + m2) * side_unit)) if require_pythagorean else None
    is_square = (m1 == m2)

    return {
        "verts": verts,
        "area": area,
        "perimeter": perimeter,
        "is_square": is_square,
        "rotated": True,
        "bbox": (shift_x + min_x, shift_y + min_y, shift_x + max_x, shift_y + max_y)
    }


def get_axis_aligned_rect(grid_w, grid_h, max_side=6):
    """Generates a standard axis-aligned rectangle or square on integer grid lines."""
    w = random.randint(1, max_side)
    h = random.randint(1, max_side)
    x0 = random.randint(1, grid_w - 1 - w)
    y0 = random.randint(1, grid_h - 1 - h)
    verts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
    return {
        "verts": verts,
        "area": w * h,
        "perimeter": 2 * (w + h),
        "is_square": (w == h),
        "rotated": False,
        "bbox": (x0, y0, x0 + w, y0 + h)
    }


def boxes_overlap(b1, b2, pad=1):
    """Checks if two bounding boxes (x_min, y_min, x_max, y_max) overlap with padding."""
    return not (
        b1[2] + pad <= b2[0] or
        b2[2] + pad <= b1[0] or
        b1[3] + pad <= b2[1] or
        b2[3] + pad <= b1[1]
    )


def generate_multi_shape_scene(grid_w=14, grid_h=14):
    """
    Places 4 non-overlapping shapes (mix of rotated and axis-aligned) on a 14x14 grid.
    Ensures a unique maximum area so the student can shade the largest shape.
    """
    shapes = []
    attempts = 0
    while len(shapes) < 4 and attempts < 200:
        attempts += 1
        use_rotated = random.choice([True, True, False])
        if use_rotated:
            cand = get_grid_locked_rect(grid_w, grid_h, require_pythagorean=False, max_dim=4)
        else:
            cand = get_axis_aligned_rect(grid_w, grid_h, max_side=5)

        if cand["area"] > 18:
            continue

        if all(not boxes_overlap(cand["bbox"], s["bbox"], pad=1) for s in shapes):
            shapes.append(cand)

    # Fallback if random placement couldn't pack 4 shapes
    if len(shapes) < 4:
        shapes = [
            {"verts": [(1, 9), (4, 9), (4, 12), (1, 12)], "area": 9, "perimeter": 12, "is_square": True, "rotated": False, "bbox": (1, 9, 4, 12)},
            {"verts": [(7, 10), (13, 10), (13, 11), (7, 11)], "area": 6, "perimeter": 14, "is_square": False, "rotated": False, "bbox": (7, 10, 13, 11)},
            {"verts": [(2, 4), (4, 2), (5, 3), (3, 5)], "area": 4, "perimeter": None, "is_square": False, "rotated": True, "bbox": (2, 2, 5, 5)},
            {"verts": [(9, 2), (11, 4), (9, 6), (7, 4)], "area": 8, "perimeter": None, "is_square": True, "rotated": True, "bbox": (7, 2, 11, 6)},
        ]

    # Ensure strictly unique maximum area (if tied, adjust one axis-aligned shape or regenerate)
    areas = [s["area"] for s in shapes]
    max_a = max(areas)
    if areas.count(max_a) > 1:
        return generate_multi_shape_scene(grid_w, grid_h)

    # Label shapes A, B, C, D near their top/center so AI and students can reference them
    labels = ["A", "B", "C", "D"]
    for idx, s in enumerate(shapes):
        s["label"] = labels[idx]

    max_shape = max(shapes, key=lambda s: s["area"])
    return shapes, max_shape


# --- PROBLEM GENERATOR ---

def generate_area_perimeter_problem(question_type="Both"):
    """
    Generates a visual grid problem:
    1. Single Rotated Shape Area (with optional dotted guidelines)
    2. Multi-Shape Comparison (shade the shape with the maximum area)
    3. Perimeter (axis-aligned or Pythagorean triple rotated shape)
    """
    if question_type == "Area Only":
        q_mode = random.choice(["single_area", "single_area", "multi_max"])
    elif question_type == "Perimeter Only":
        q_mode = "perimeter"
    else:
        q_mode = random.choice(["single_area", "single_area", "multi_max", "perimeter"])

    if q_mode == "single_area":
        grid_w, grid_h = 10, 8
        shape = get_grid_locked_rect(grid_w, grid_h, require_pythagorean=False, max_dim=7)
        noun = "square" if shape["is_square"] else "rectangle"
        text = f"Find the area of this {noun}."
        ans = f"{shape['area']} square units"
        rule = (
            f"The student must calculate the exact area of the {noun} on the 1x1 unit grid. "
            f"Correct final answer: {shape['area']} (or {shape['area']} square units / units²). "
            f"Accept decomposition into triangles and squares or side-length multiplication."
        )
        return {
            "mode": "Written",
            "q_type": "single_area",
            "text": text,
            "grid_w": grid_w,
            "grid_h": grid_h,
            "shapes": [shape],
            "ans": ans,
            "grading_rule": rule
        }

    elif q_mode == "multi_max":
        grid_w, grid_h = 14, 14
        shapes, max_shape = generate_multi_shape_scene(grid_w, grid_h)
        area_summary = ", ".join([f"Shape {s['label']} = {s['area']}" for s in shapes])
        text = "Find the area of each figure and shade the figure with the LARGEST area."
        ans = f"Shape {max_shape['label']} ({max_shape['area']} square units)"
        rule = (
            f"The student must identify and shade Shape {max_shape['label']} as having the maximum area "
            f"({max_shape['area']} square units). Areas of all shapes: {area_summary}. "
            f"Award full credit if Shape {max_shape['label']} is clearly shaded/circled/indicated as the largest."
        )
        return {
            "mode": "Written",
            "q_type": "multi_max",
            "text": text,
            "grid_w": grid_w,
            "grid_h": grid_h,
            "shapes": shapes,
            "ans": ans,
            "grading_rule": rule
        }

    else:  # perimeter
        grid_w, grid_h = 10, 8
        # 50/50 mix of standard axis-aligned rectangle or Pythagorean triple rotated rectangle
        if random.choice([True, False]):
            shape = get_grid_locked_rect(grid_w, grid_h, require_pythagorean=True, max_dim=7)
        else:
            shape = get_axis_aligned_rect(grid_w, grid_h, max_side=6)

        noun = "square" if shape["is_square"] else "rectangle"
        text = f"Find the perimeter of this {noun}."
        ans = f"{shape['perimeter']} units"
        rule = (
            f"The student must calculate the exact perimeter of the {noun} on the 1x1 unit grid. "
            f"Correct final answer: {shape['perimeter']} units (accept {shape['perimeter']} without units)."
        )
        return {
            "mode": "Written",
            "q_type": "perimeter",
            "text": text,
            "grid_w": grid_w,
            "grid_h": grid_h,
            "shapes": [shape],
            "ans": ans,
            "grading_rule": rule
        }


# --- VISUAL CANVAS ENGINE ---

def draw_decomposition_guides(ax, shape):
    """
    Draws internal horizontal and vertical dashed grid lines inside a rotated polygon
    so students can count whole unit squares and 1/2*b*h right triangles easily.
    """
    verts = shape["verts"]
    poly_path = matplotlib.path.Path(verts)
    x_min, y_min, x_max, y_max = shape["bbox"]

    # Sample horizontal and vertical grid segments clipped strictly inside the polygon
    xs_dense = [x_min + i * 0.02 for i in range(int((x_max - x_min) / 0.02) + 1)]
    ys_dense = [y_min + i * 0.02 for i in range(int((y_max - y_min) / 0.02) + 1)]

    # Horizontal grid lines inside shape
    for gy in range(y_min + 1, y_max):
        pts = [(x, gy) for x in xs_dense]
        inside = poly_path.contains_points(pts, radius=-1e-4)
        seg_x = []
        for idx, is_in in enumerate(inside):
            if is_in:
                seg_x.append(xs_dense[idx])
            elif seg_x:
                if len(seg_x) > 1:
                    ax.plot([seg_x[0], seg_x[-1]], [gy, gy], linestyle="--", color="#333333", linewidth=1.1, zorder=4)
                seg_x = []
        if len(seg_x) > 1:
            ax.plot([seg_x[0], seg_x[-1]], [gy, gy], linestyle="--", color="#333333", linewidth=1.1, zorder=4)

    # Vertical grid lines inside shape
    for gx in range(x_min + 1, x_max):
        pts = [(gx, y) for y in ys_dense]
        inside = poly_path.contains_points(pts, radius=-1e-4)
        seg_y = []
        for idx, is_in in enumerate(inside):
            if is_in:
                seg_y.append(ys_dense[idx])
            elif seg_y:
                if len(seg_y) > 1:
                    ax.plot([gx, gx], [seg_y[0], seg_y[-1]], linestyle="--", color="#333333", linewidth=1.1, zorder=4)
                seg_y = []
        if len(seg_y) > 1:
            ax.plot([gx, gx], [seg_y[0], seg_y[-1]], linestyle="--", color="#333333", linewidth=1.1, zorder=4)


def draw_grid_problem_image(p_data, show_guides=True, width_px=420, height_px=480):
    """
    Renders the prompt text at the top and the crisp 1x1 unit square grid below,
    leaving whitespace at the bottom for student working.
    """
    fig, ax = plt.subplots(figsize=(width_px / 100, height_px / 100), dpi=100)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.04)

    grid_w = p_data["grid_w"]
    grid_h = p_data["grid_h"]

    # Coordinate frame: grid occupies x in [0, grid_w], y in [0, grid_h]
    # Extra headroom above grid_h for prompt text & "1 unit" scale key; extra space below 0 for workings
    top_pad = 3.2 if grid_h <= 10 else 4.2
    bottom_pad = 2.8 if grid_h <= 10 else 2.2

    ax.set_xlim(-0.8, grid_w + 1.4)
    ax.set_ylim(-bottom_pad, grid_h + top_pad)
    ax.set_aspect('equal')
    ax.axis('off')

    # 1. Question Prompt Text
    wrapped_text = "\n".join(textwrap.wrap(p_data["text"], width=44))
    ax.text(
        -0.5, grid_h + top_pad - 0.2,
        wrapped_text,
        fontsize=12,
        fontweight='bold',
        ha='left',
        va='top',
        family='sans-serif',
        color='black'
    )

    # 2. "1 unit" Scale Legend (top-right of grid, matching worksheet style)
    leg_x = grid_w - 1
    leg_y = grid_h + 0.35
    ax.annotate("", xy=(leg_x, leg_y), xytext=(leg_x + 1, leg_y),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.0))
    ax.text(leg_x + 0.5, leg_y + 0.15, "1 unit", fontsize=8.5, ha="center", va="bottom", color="black")

    ax.annotate("", xy=(grid_w + 0.35, grid_h - 1), xytext=(grid_w + 0.35, grid_h),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.0))
    ax.text(grid_w + 0.5, grid_h - 0.5, "1 unit", fontsize=8.5, ha="left", va="center", color="black")

    # 3. Draw Unit Grid Lines
    for x in range(grid_w + 1):
        ax.plot([x, x], [0, grid_h], color="#888888", linewidth=0.8, zorder=1)
    for y in range(grid_h + 1):
        ax.plot([0, grid_w], [y, y], color="#888888", linewidth=0.8, zorder=1)

    # 4. Draw Shapes
    for shape in p_data["shapes"]:
        poly = patches.Polygon(
            shape["verts"],
            closed=True,
            facecolor="none",
            edgecolor="black",
            linewidth=1.8,
            zorder=5
        )
        ax.add_patch(poly)

        # Draw internal dotted guidelines for single rotated shapes if enabled
        if show_guides and shape.get("rotated", False) and p_data["q_type"] in ["single_area", "perimeter"]:
            draw_decomposition_guides(ax, shape)

        # Draw subtle shape label (A, B, C, D) for multi-shape comparison questions
        if "label" in shape:
            cx = sum(v[0] for v in shape["verts"]) / 4.0
            cy = sum(v[1] for v in shape["verts"]) / 4.0
            ax.text(
                cx, cy, shape["label"],
                fontsize=10, fontweight='bold', color="#1f4e78",
                ha="center", va="center",
                bbox=dict(boxstyle="circle,pad=0.18", facecolor="white", edgecolor="#1f4e78", alpha=0.85, lw=0.8),
                zorder=6
            )

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='white', transparent=False)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert('RGBA').copy()


# --- WORKSHEET PDF GENERATOR ---

def create_pdf_bytes(question_type="Both", show_guides=True):
    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        problems = [generate_area_perimeter_problem(question_type=question_type) for _ in range(12)]

        # 2 pages of 6 grid questions each (3 rows x 2 cols) for crisp readability
        for page_idx in range(2):
            fig_ws, axes = plt.subplots(3, 2, figsize=(8.27, 11.69))
            fig_ws.subplots_adjust(left=0.05, right=0.95, top=0.91, bottom=0.04, wspace=0.15, hspace=0.22)
            fig_ws.suptitle(f"Middle School Maths: Area & Perimeter (Page {page_idx + 1})", fontsize=15, fontweight='bold')

            for slot in range(6):
                q_idx = page_idx * 6 + slot
                p_data = problems[q_idx]
                row, col = divmod(slot, 2)
                ax = axes[row, col]
                ax.axis('off')

                img = draw_grid_problem_image(p_data, show_guides=show_guides, width_px=400, height_px=440)
                ax.imshow(img)
                ax.set_title(f"Question {q_idx + 1}", fontsize=10, fontweight='bold', loc='left', pad=2)

            pdf.savefig(fig_ws)
            plt.close(fig_ws)

        # Answer Key Page
        fig_ans, ax_ans = plt.subplots(figsize=(8.27, 11.69))
        ax_ans.axis('off')
        ax_ans.text(0.5, 0.95, "Area & Perimeter — Answer Key", fontsize=16, fontweight='bold', ha='center')
        for idx, p_data in enumerate(problems):
            y_pos = 0.88 - (idx * 0.065)
            ax_ans.text(0.08, y_pos, f"Q{idx + 1}: {p_data['ans']}", fontsize=11, va='top')
        pdf.savefig(fig_ans)
        plt.close(fig_ans)

    buffer.seek(0)
    return buffer.getvalue()


# --- STATE MANAGEMENT & MODULE RUNNER ---

def handle_ap_settings_change():
    st.session_state.ap_generating = True
    st.session_state.ap_pdf_bytes = None
    st.session_state.ap_suite_refresh_id += 1
    st.session_state.ap_question_queue = []
    st.session_state.ap_quiz_active = False
    st.session_state.ap_quiz_score = 0
    st.session_state.ap_questions_answered = 0
    st.session_state.ap_quiz_completed = False


def get_next_ap_question():
    mode = st.session_state.get('ap_selection_mode', 'Random')
    q_type = st.session_state.get('ap_question_type', 'Both')

    if mode == "Random":
        return generate_area_perimeter_problem(question_type=q_type)

    if 'ap_question_queue' not in st.session_state or not st.session_state.ap_question_queue:
        if mode == "Quiz":
            st.session_state.ap_quiz_score = 0
            st.session_state.ap_questions_answered = 0
            st.session_state.ap_quiz_completed = False

        queue_len = 10 if mode == "Quiz" else 12
        st.session_state.ap_question_queue = [
            generate_area_perimeter_problem(question_type=q_type) for _ in range(queue_len)
        ]

    if mode == "Quiz" and not st.session_state.ap_question_queue:
        st.session_state.ap_quiz_completed = True
        return None

    return st.session_state.ap_question_queue.pop(0)


def run_app():
    st.markdown("""
        <style>
        button[kind="primary"] { background-color: #007AFF !important; border-color: #007AFF !important; color: white !important; }
        button[kind="primary"]:hover { background-color: #0056b3 !important; border-color: #0056b3 !important; }
        div[data-testid="stElementContainer"]:has(#next-problem-btn) + div[data-testid="stElementContainer"] button {
            background-color: #28a745 !important; border-color: #28a745 !important; color: white !important;
        }
        div[data-testid="stElementContainer"]:has(#next-problem-btn) + div[data-testid="stElementContainer"] button:hover {
            background-color: #218838 !important; border-color: #218838 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Strict ap_ session state initialization
    if 'ap_generating' not in st.session_state: st.session_state.ap_generating = True
    if 'ap_pdf_bytes' not in st.session_state: st.session_state.ap_pdf_bytes = None
    if 'ap_suite_refresh_id' not in st.session_state: st.session_state.ap_suite_refresh_id = 0
    if 'ap_selection_mode' not in st.session_state: st.session_state.ap_selection_mode = "Random"
    if 'ap_question_type' not in st.session_state: st.session_state.ap_question_type = "Both"
    if 'ap_show_guides' not in st.session_state: st.session_state.ap_show_guides = True
    if 'ap_quiz_active' not in st.session_state: st.session_state.ap_quiz_active = False
    if 'ap_questions_answered' not in st.session_state: st.session_state.ap_questions_answered = 0
    if 'ap_quiz_score' not in st.session_state: st.session_state.ap_quiz_score = 0
    if 'ap_quiz_completed' not in st.session_state: st.session_state.ap_quiz_completed = False

    st.title("Area & Perimeter 📐")

    col_actions, col_set = st.columns([4, 1])
    with col_actions:
        with st.popover("📄 Worksheet Actions", use_container_width=True):
            if st.session_state.ap_pdf_bytes is None:
                if st.button("⚙️ Generate 12-Question PDF", use_container_width=True):
                    with st.spinner("Compiling PDF..."):
                        st.session_state.ap_pdf_bytes = create_pdf_bytes(
                            question_type=st.session_state.ap_question_type,
                            show_guides=st.session_state.ap_show_guides
                        )
                    st.rerun()
            else:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                st.download_button(
                    "⬇️ Download Worksheet",
                    data=st.session_state.ap_pdf_bytes,
                    file_name=f"Area_Perimeter_{timestamp}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )

    with col_set:
        with st.popover("⚙️", use_container_width=True):
            st.radio(
                "Selection Mode",
                ["Random", "Cyclical", "Quiz"],
                key="ap_selection_mode",
                on_change=handle_ap_settings_change
            )
            st.radio(
                "Topic Focus",
                ["Area Only", "Perimeter Only", "Both"],
                key="ap_question_type",
                on_change=handle_ap_settings_change
            )
            st.toggle(
                "Show Dotted Guidelines",
                key="ap_show_guides",
                help="Displays internal dashed lines to break rotated shapes into whole squares and right triangles."
            )
            st.radio(
                "Camera Mode",
                ["None", "App", "Native"],
                key="ap_camera_mode",
                horizontal=True,
                on_change=handle_ap_settings_change
            )
            st.toggle(
                "Canvas Controls",
                key="ap_show_controls",
                on_change=handle_ap_settings_change
            )

    # --- QUIZ START GATE ---
    if st.session_state.ap_selection_mode == "Quiz" and not st.session_state.ap_quiz_active:
        if st.session_state.ap_quiz_completed:
            st.success(f"🎉 Quiz Complete! You completed {st.session_state.ap_questions_answered} questions.")
            if st.button("Restart Quiz", use_container_width=True):
                handle_ap_settings_change()
                st.rerun()
            return

        st.info("Ready to test your Area & Perimeter skills? This quiz presents 10 grid challenges.")
        if st.button("🚀 Start 10-Question Quiz", use_container_width=True, type="primary"):
            st.session_state.ap_quiz_active = True
            st.session_state.ap_quiz_score = 0
            st.session_state.ap_questions_answered = 0
            st.session_state.ap_generating = True
            st.rerun()
        return

    # --- RUNNING PROGRESS BANNER ---
    if st.session_state.ap_selection_mode == "Quiz" and st.session_state.ap_quiz_active:
        col1, col2 = st.columns(2)
        col1.metric("Question", f"{st.session_state.ap_questions_answered + 1} / 10")
        col2.metric("Guidelines", "On" if st.session_state.ap_show_guides else "Off")
        st.divider()

    # --- QUESTION GENERATION ---
    if st.session_state.ap_generating or 'ap_problem_data' not in st.session_state:
        st.session_state.ap_generating = True
        with st.spinner("Generating grid problem..."):
            p_data = get_next_ap_question()
            if p_data is None:
                st.session_state.ap_quiz_active = False
                st.rerun()

            st.session_state.ap_problem_data = p_data
            st.session_state.ap_generating = False
            st.rerun()

    else:
        p_data = st.session_state.ap_problem_data
        # Render image dynamically so toggling "Show Dotted Guidelines" updates the current question immediately
        bg_image = draw_grid_problem_image(
            p_data,
            show_guides=st.session_state.get('ap_show_guides', True),
            width_px=420,
            height_px=480
        )
        problem_context = f"Question: {p_data['text']}\nGrading Rule: {p_data.get('grading_rule', '')}"

        ai_marking_component.render_grading_suite(
            bg_image=bg_image,
            height_px=480,
            key_prefix=f"ap_suite_{st.session_state.ap_suite_refresh_id}",
            solution_requirement="general",
            problem_context=problem_context,
            show_controls=st.session_state.get('ap_show_controls', False),
            camera_mode=st.session_state.get('ap_camera_mode', 'App')
        )

        st.markdown('<div id="next-problem-btn"></div>', unsafe_allow_html=True)
        if st.button("Next Question", use_container_width=True):
            if st.session_state.ap_selection_mode == "Cyclical":
                st.session_state.ap_question_queue.append(p_data)
            if st.session_state.ap_selection_mode == "Quiz":
                st.session_state.ap_questions_answered += 1
            st.session_state.ap_generating = True
            st.session_state.ap_suite_refresh_id += 1
            st.rerun()