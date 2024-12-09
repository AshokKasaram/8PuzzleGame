from flask import Flask, render_template_string, jsonify, request, url_for
from PIL import Image
import random
import os
from heapq import heappop, heappush
from itertools import count

app = Flask(__name__)

# Folder to save image tiles
UPLOAD_FOLDER = 'static'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

tiles = []
current_state = []
move_count = 0

# Heuristic function for A* (Manhattan Distance)
def manhattan_distance(state):
    distance = 0
    for index, value in enumerate(state):
        if value == 0:
            continue
        target_x, target_y = divmod(value - 1, 3)
        x, y = divmod(index, 3)
        distance += abs(target_x - x) + abs(target_y - y)
    return distance

# A* search to find the minimum number of moves to solve the 8-puzzle
def a_star_search(initial_state):
    goal_state = tuple(range(1, 9)) + (0,)
    parent_map = {tuple(initial_state): None}
    g_score = {tuple(initial_state): 0}
    f_score = {tuple(initial_state): manhattan_distance(initial_state)}

    open_set = []
    heappush(open_set, (f_score[tuple(initial_state)], next(count()), tuple(initial_state)))

    while open_set:
        _, __, current = heappop(open_set)

        if current == goal_state:
            # Reconstruct path to get the number of moves
            moves = 0
            while parent_map[current]:
                current = parent_map[current]
                moves += 1
            return moves

        current_index = current.index(0)
        x, y = divmod(current_index, 3)
        neighbors = []
        if x > 0: neighbors.append(current_index - 3)
        if x < 2: neighbors.append(current_index + 3)
        if y > 0: neighbors.append(current_index - 1)
        if y < 2: neighbors.append(current_index + 1)

        for neighbor in neighbors:
            new_state = list(current)
            new_state[current_index], new_state[neighbor] = new_state[neighbor], new_state[current_index]
            new_state = tuple(new_state)

            tentative_g_score = g_score[current] + 1
            if new_state not in g_score or tentative_g_score < g_score[new_state]:
                parent_map[new_state] = current
                g_score[new_state] = tentative_g_score
                f_score[new_state] = tentative_g_score + manhattan_distance(new_state)
                heappush(open_set, (f_score[new_state], next(count()), new_state))

    return -1  # Return -1 if no solution is found

# Divide Image into a 3x3 Grid and Save as Files
def split_image(img, upload_folder):
    tile_size = img.size[0] // 3
    pieces = []
    for i in range(3):
        for j in range(3):
            left = j * tile_size
            upper = i * tile_size
            right = left + tile_size
            lower = upper + tile_size
            tile = img.crop((left, upper, right, lower))
            tile_path = os.path.join(upload_folder, f"tile_{i}_{j}.png")
            tile.save(tile_path)
            pieces.append(url_for('static', filename=f"tile_{i}_{j}.png"))
    return pieces

# Shuffle Tiles and Ensure Solvability
def shuffle_tiles():
    state = list(range(1, 9)) + [0]
    while True:
        random.shuffle(state)
        if is_solvable(state):
            break
    return state

# Check Puzzle Solvability
def is_solvable(state):
    inversions = 0
    for i in range(len(state)):
        for j in range(i + 1, len(state)):
            if state[i] > state[j] and state[i] != 0 and state[j] != 0:
                inversions += 1
    return inversions % 2 == 0

@app.route("/", methods=["GET", "POST"])
def home():
    global tiles, current_state, move_count
    if request.method == "POST":
        # Reset the game state
        move_count = 0
        img_file = request.files["file"]
        img = Image.open(img_file)
        img = img.resize((300, 300))  # Resize image
        tiles = split_image(img, UPLOAD_FOLDER)
        current_state = shuffle_tiles()

    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>8-Puzzle Game</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 20px;
                    background-color: #87CEFA; /* Light blue background */
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(3, 100px);
                    gap: 5px;
                    justify-content: center;
                    margin: 20px auto;
                }
                .tile {
                    width: 100px;
                    height: 100px;
                    border: 1px solid #1E90FF; /* Darker blue for borders */
                    cursor: pointer;
                    background-size: cover;
                    background-position: center;
                    transition: background 0.3s ease; /* Animation for tile movements */
                }
                .blank {
                    background-color: #B0E0E6; /* Lighter blue for blank tiles */
                    cursor: default;
                }
                button {
                    margin: 10px;
                    padding: 10px 20px;
                    font-size: 16px;
                    background-color: #1E90FF; /* Button color */
                    color: white; /* Button text color */
                    border: none;
                    border-radius: 5px;
                    transition: background-color 0.2s;
                }
                button:hover {
                    background-color: #4682B4; /* Darker blue on hover */
                }
                #status {
                    margin-top: 20px;
                    font-size: 18px;
                    color: #2F4F4F; /* Dark Slate Gray for text */
                }
                @media (max-width: 600px) {
                    .grid {
                        grid-template-columns: repeat(3, 33vw);
                        gap: 2vw;
                    }
                    .tile {
                        width: 33vw;
                        height: 33vw;
                    }
                }
            </style>
        </head>
        <body>
            <h1>8-Puzzle Game</h1>
            <p>Drag an image file below to scramble it into a puzzle. Click the tiles to move them and rearrange the image back to its original form. Aim to solve the puzzle with the minimum moves possible!</p>
            <form method="post" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <button type="submit">Upload Image</button>
            </form>
            <button id="show-solution" onclick="showSolution()">Show Solution</button>
            <button id="min-moves" onclick="getMinimumMoves()">Get Minimum Moves to Solve</button>
            <div id="grid" class="grid"></div>
            <p id="move-count">Moves: {{ move_count }}</p>
            <p id="status"></p>
            <script>
                let state = {{ state }};
                let moveCount = {{ move_count }};
                const tiles = {{ tiles|tojson }};
                const grid = document.getElementById("grid");
                const moveCountDisplay = document.getElementById("move-count");
                const statusDisplay = document.getElementById("status");

                function renderGrid() {
                    grid.innerHTML = '';
                    state.forEach((tile, index) => {
                        const div = document.createElement('div');
                        if (tile === 0) {
                            div.className = 'tile blank';
                        } else {
                            div.className = 'tile';
                            div.style.backgroundImage = `url(${tiles[tile - 1]})`;
                            div.onclick = () => moveTile(tile);
                        }
                        grid.appendChild(div);
                    });
                }

                function moveTile(tile) {
                    fetch('/move', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: `tile=${tile}`
                    }).then(response => response.json())
                      .then(data => {
                          state = data.state;
                          moveCount = data.move_count;
                          moveCountDisplay.textContent = `Moves: ${moveCount}`;
                          renderGrid();
                          if (data.solved) {
                              statusDisplay.textContent = "Congratulations! You solved the puzzle!";
                          }
                      });
                }

                function showSolution() {
                    fetch('/solution', { method: 'GET' })
                        .then(response => response.json())
                        .then(data => {
                            state = data.state;
                            renderGrid();
                            statusDisplay.textContent = "Here's the solved puzzle!";
                        });
                }

                function getMinimumMoves() {
                    fetch('/minimum-moves', { method: 'GET' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.minimum_moves !== undefined) {
                                alert('Minimum moves to solve: ' + data.minimum_moves);
                            } else {
                                alert('Error: ' + data.error);
                            }
                        });
                }

                renderGrid();
            </script>
        </body>
        </html>
        """,
        state=current_state,
        move_count=move_count,
        tiles=tiles,
    )

@app.route("/move", methods=["POST"])
def move_tile():
    global current_state, move_count
    tile = int(request.form["tile"])
    blank_index = current_state.index(0)
    tile_index = current_state.index(tile)

    row_blank, col_blank = divmod(blank_index, 3)
    row_tile, col_tile = divmod(tile_index, 3)

    if abs(row_blank - row_tile) + abs(col_blank - col_tile) == 1:
        # Swap the tiles
        current_state[blank_index], current_state[tile_index] = (
            current_state[tile_index],
            current_state[blank_index],
        )
        move_count += 1
        solved = current_state == list(range(1, 9)) + [0]
        return jsonify({"state": current_state, "move_count": move_count, "solved": solved})

    return jsonify({"state": current_state, "move_count": move_count, "solved": False})

@app.route("/solution", methods=["GET"])
def show_solution():
    global current_state
    current_state = list(range(1, 9)) + [0]  # Solved state
    return jsonify({"state": current_state})

@app.route("/minimum-moves", methods=["GET"])
def minimum_moves():
    global current_state
    if is_solvable(current_state):
        moves = a_star_search(current_state)
        return jsonify({"minimum_moves": moves})
    return jsonify({"error": "This puzzle state is not solvable"})

if __name__ == "__main__":
    app.run(debug=True)
