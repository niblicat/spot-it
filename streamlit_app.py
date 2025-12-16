import streamlit as st
import math
import random
from PIL import Image, ImageDraw
import io
import zipfile
import tempfile

# --- Constants ---
SYMBOL_SIZE_DEFAULT = 100
MARGIN = 20

st.set_page_config(page_title="Spot It! Card Generator")
st.title("🔄 Spot It! Card Generator")

with st.sidebar:
    # --- Mode selection ---
    mode = st.radio("Choose mode:", ["Simple", "Circle", "Advanced"])

    # --- Common inputs ---
    n = st.slider("Symbols per card (n):", min_value=3, max_value=9, value=4)
    total_symbols = n**2 - n + 1
    image_files = st.file_uploader(
        f"Upload at least {total_symbols} images",
        type=['png', 'jpg', 'jpeg'], accept_multiple_files=True
    )
    card_size = st.slider("Card size (px):", 300, 800, 500)
    symbol_size = st.slider("Symbol size (px):", 20, 200, 80)
    border_thickness = st.slider("Border thickness:", 1, 10, 3)
    use_circles = st.toggle("Use circular border")

    if mode == "Circle":
        center = card_size // 2
        default_radius = (card_size - MARGIN*2) // 2
        st.header("Circle Mode Options")
        face_outward = st.toggle("Face outward instead of inward")
        radius = st.slider("Radius", MARGIN, default_radius, default_radius)
        show_options = st.toggle("Show symbol options", False)

# --- Math logic ---
def generate_spot_it_deck(n):
    cards = []
    for i in range(n):
        card = [0] + [i * (n - 1) + j + 1 for j in range(n - 1)]
        cards.append(card)
    for i in range(n - 1):
        for j in range(n - 1):
            card = [i + 1]
            for k in range(n - 1):
                val = n + (n - 1) * k + ((i * k + j) % (n - 1))
                card.append(val)
            cards.append(card)
    return cards

# --- Collision detection ---
def is_overlapping(new_box, placed_boxes):
    for box in placed_boxes:
        if not (new_box[2] <= box[0] or new_box[0] >= box[2] or
                new_box[3] <= box[1] or new_box[1] >= box[3]):
            return True
    return False

# --- Improved Drawing Logic with Collision ---
def draw_card(symbols, images, size, symbol_size, border):
    card = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)
    center = (size // 2, size // 2)
    radius = (size - symbol_size) // 2

    placed_boxes = []
    max_attempts = 100

    for sym_id in symbols:
        placed = False
        my_symbol_size = symbol_size

        for attempt in range(max_attempts):
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, radius)
            cx = center[0] + r * math.cos(angle)
            cy = center[1] + r * math.sin(angle)

            x1 = cx - my_symbol_size / 2
            y1 = cy - my_symbol_size / 2
            x2 = cx + my_symbol_size / 2
            y2 = cy + my_symbol_size / 2

            corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
            if any(
                math.hypot(c[0]-center[0], c[1]-center[1]) >
                radius for c in corners):
                continue

            if is_overlapping((x1, y1, x2, y2), placed_boxes):
                continue

            placed_boxes.append((x1, y1, x2, y2))
            img = images[sym_id].resize((my_symbol_size, my_symbol_size))
            card.paste(img, (int(x1), int(y1)), img.convert('RGBA'))
            placed = True
            break

        if not placed:
            for smaller_size in range(symbol_size - 10, 20, -10):
                symbol_size = smaller_size
                for attempt in range(max_attempts):
                    angle = random.uniform(0, 2 * math.pi)
                    r = random.uniform(0, radius)
                    cx = center[0] + r * math.cos(angle)
                    cy = center[1] + r * math.sin(angle)

                    x1 = cx - symbol_size / 2
                    y1 = cy - symbol_size / 2
                    x2 = cx + symbol_size / 2
                    y2 = cy + symbol_size / 2

                    corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
                    if any(
                        math.hypot(c[0]-center[0], c[1]-center[1])
                        > radius for c in corners):
                        continue

                    if is_overlapping((x1, y1, x2, y2), placed_boxes):
                        continue

                    placed_boxes.append((x1, y1, x2, y2))
                    img = images[sym_id].resize((symbol_size, symbol_size))
                    card.paste(img, (int(x1), int(y1)), img.convert('RGBA'))
                    placed = True
                    break
                if placed:
                    break

    if border > 0:
        if use_circles:
            draw.ellipse(
                [MARGIN, MARGIN, size - MARGIN, size - MARGIN],
                outline="black",
                width=border
            )
        else:
            draw.rounded_rectangle(
                [MARGIN, MARGIN, size - MARGIN, size - MARGIN],
                outline="black",
                width=border,
                radius=30
            )
    return card

def draw_card_with_positions(
    symbols,
    images: list[Image.Image],
    positions,
    rotations,
    sizes,
    size=500,
    border=3
):
    card = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(card)
    if use_circles:
        draw.ellipse(
            [MARGIN, MARGIN, size - MARGIN, size - MARGIN],
            outline="black",
            width=border
        )
    else:
        draw.rounded_rectangle(
            [MARGIN, MARGIN, size - MARGIN, size - MARGIN],
            outline="black",
            width=border,
            radius=30
        )
    for i, sym_id in enumerate(symbols):
        img: Image.Image = images[sym_id].resize((int(sizes[i]), int(sizes[i])))
        x, y = positions[i]
        rotation = rotations[i]

        if rotation == 0:
            paste_x = x - img.width // 2
            paste_y = y - img.height // 2
            card.paste(img, (int(paste_x), int(paste_y)), img.convert("RGBA"))
        else:
            img_rotated = img.rotate(
                rotation,
                expand=True,
                resample=Image.BICUBIC,
                center=None
            )

            paste_x = x - img_rotated.width // 2
            paste_y = y - img_rotated.height // 2

            card.paste(
                img_rotated,
                (int(paste_x), int(paste_y)),
                img_rotated.convert("RGBA")
            )
    return card

def get_card_identifier(symbol_id, card_number) -> str:
    return f"symbol {symbol_id + 1}, card {card_number + 1}"

if image_files and len(image_files) >= total_symbols:
    deck = generate_spot_it_deck(n)
    st.success(f"Generated {len(deck)} cards.")

    images = [Image.open(f).convert("RGBA")
              for f in image_files[:total_symbols]]
    final_cards = []


    for card_idx, card_symbols in enumerate(deck):
        st.subheader(f"Card {card_idx + 1}")
        if mode == "Easy":
            card_img = draw_card(
                card_symbols,
                images,
                size=card_size,
                symbol_size=symbol_size,
                border=border_thickness
            )
            st.image(card_img, width="stretch")
            final_cards.append(card_img)
        elif mode == "Circle":
            if face_outward: rot = 270
            else: rot = 90

            default_angles = []
            for i in range(len(card_symbols)):
                angle = 360 * i / len(card_symbols)
                default_angles.append(angle)

            positions = []
            sizes = []
            rotations = []

            for i, sym_id in enumerate(card_symbols):
                if show_options:
                    identifer = get_card_identifier(sym_id, card_idx + 1)

                    st.write(f"Symbol {sym_id + 1}")
                    angle_slider = st.slider(
                        f"Angle ({identifer})",
                        0, 360, int(default_angles[i]),
                        key=f"angle_{card_idx}_{i}"
                    )
                    size_slider = st.slider(
                        f"Size Modifier ({identifer})",
                        float(0), float(4), float(1),
                        key=f"s_{card_idx}_{i}"
                    )
                else:
                    angle_slider = default_angles[i]
                    size_slider = float(1)

                pos_x = math.cos(math.radians(angle_slider)) * radius + center
                pos_y = math.sin(math.radians(angle_slider)) * radius + center
                positions.append([pos_x, pos_y])
                sizes.append(size_slider * symbol_size)

                rotations.append(-(angle_slider + rot))

            card_img = draw_card_with_positions(
                card_symbols, images, positions, rotations, sizes,
                size=card_size, border=border_thickness
            )
            st.image(card_img, width="stretch")
            final_cards.append(card_img)
        else:
            center = card_size // 2
            radius = (card_size - MARGIN*2) // 2
            default_positions = []

            for i in range(len(card_symbols)):
                angle = 2 * math.pi * i / len(card_symbols)
                x = center + radius * math.cos(angle)
                y = center + radius * math.sin(angle)
                default_positions.append([x, y])

            positions = []
            sizes = []
            rotations = []

            for i, sym_id in enumerate(card_symbols):
                identifer = get_card_identifier(sym_id, card_idx + 1)

                st.write(f"Symbol {sym_id + 1}")
                pos_x = st.slider(
                    f"X position ({identifer})",
                    MARGIN, card_size - MARGIN, int(default_positions[i][0]),
                    key=f"x_{card_idx}_{i}"
                )
                pos_y = st.slider(
                    f"Y position ({identifer})",
                    MARGIN, card_size - MARGIN, int(default_positions[i][1]),
                    key=f"y_{card_idx}_{i}"
                )
                size_slider = st.slider(
                    f"Size Modifier ({identifer})",
                    float(0), float(4), float(1),
                    key=f"s_{card_idx}_{i}"
                )
                rotation_slider = st.slider(
                    f"Rotation ({identifer})",
                    0, 360, 0,
                    key=f"rotation_{card_idx}_{i}"
                )

                positions.append([pos_x, pos_y])
                rotations.append(rotation_slider)
                sizes.append(size_slider * symbol_size)

            card_img = draw_card_with_positions(
                card_symbols, images, positions, rotations, sizes,
                size=card_size, border=border_thickness
            )
            st.image(card_img, width="stretch")
            final_cards.append(card_img)
    with st.sidebar:
        if st.button("Export All Cards as ZIP"):
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = f"{tmpdir}/spot_it_cards.zip"
                with zipfile.ZipFile(zip_path, "w") as zipf:
                    for i, card_img in enumerate(final_cards):
                        buf = io.BytesIO()
                        card_img.save(buf, format="PNG")
                        zipf.writestr(f"card_{i+1}.png", buf.getvalue())
                with open(zip_path, "rb") as f:
                    st.download_button(
                        "Download ZIP", f, file_name="spot_it_cards.zip"
                    )
else:
    st.info(f"Upload at least {total_symbols} images to generate the cards.")
