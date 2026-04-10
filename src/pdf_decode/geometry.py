from typing import List, Dict, Any


def group_words_by_line(words: List[Dict[str, Any]], tolerance: int = 5) -> Dict[int, List[Dict[str, Any]]]:
    """
    Groups words into lines based on their Y-coordinate.
    Uses closest-match to prevent wrong line assignment when lines are
    close together (within 2*tolerance).
    Returns a dictionary where keys are Y-coordinates (integers) and values are lists of words.
    """
    lines: Dict[int, List[Dict[str, Any]]] = {}
    for word in words:
        y_center = int((word['top'] + word['bottom']) / 2)
        best_y = None
        best_dist = tolerance  # only consider lines within tolerance
        for y in lines:
            dist = abs(y - y_center)
            if dist < best_dist:
                best_dist = dist
                best_y = y
        if best_y is not None:
            lines[best_y].append(word)
        else:
            lines[y_center] = [word]
    return lines
