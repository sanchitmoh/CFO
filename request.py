import requests
from bs4 import BeautifulSoup

def decode_secret_message(url):
    """
    Decode a secret message from a published Google Doc.
    The document contains coordinates (x, y) and characters to place on a grid.
    """
    # Fetch the published Google Doc content
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n")

    lines_list = text.splitlines()
    
    # Parse lines containing character and coordinates
    # Table format: headers are at lines 7-9, then data in groups of 3 (x, char, y)
    entries = []
    
    # Skip header lines (0-9) and start from line 10
    data_lines = lines_list[10:]
    
    # Process every 3 lines as: x-coordinate, character, y-coordinate
    for i in range(0, len(data_lines), 3):
        if i + 2 < len(data_lines):
            try:
                x = int(data_lines[i].strip())
                char = data_lines[i + 1].strip()
                y = int(data_lines[i + 2].strip())
                if char:  # Only add if character is not empty
                    entries.append((x, y, char))
            except ValueError:
                continue

    # Determine grid size
    if not entries:
        print("Error: No valid entries found. Check the document format.")
        print("Expected format: x y character (one per line)")
        return
    
    max_x = max(x for x, y, char in entries)
    max_y = max(y for x, y, char in entries)

    # Create empty grid
    grid = [[" " for _ in range(max_x + 1)] for _ in range(max_y + 1)]

    # Fill grid with characters
    for x, y, char in entries:
        grid[y][x] = char

    # Print the decoded message
    print("\nDecoded Message:")
    print("=" * (max_x + 1))
    for row in grid:
        print("".join(row))
    print("=" * (max_x + 1))


# Example usage
if __name__ == "__main__":
    decode_secret_message(
        "https://docs.google.com/document/d/e/2PACX-1vSvM5gDlNvt7npYHhp_XfsJvuntUhq184By5xO_pA4b_gCWeXb6dM6ZxwN8rE6S4ghUsCj2VKR21oEP/pub"
    )
