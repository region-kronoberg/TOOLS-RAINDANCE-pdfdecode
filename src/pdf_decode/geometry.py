from typing import List, Dict, Any

def group_words_by_line(words: List[Dict[str, Any]], tolerance: int = 5) -> Dict[int, List[Dict[str, Any]]]:
    """
    Groups words into lines based on their Y-coordinate.
    Returns a dictionary where keys are Y-coordinates (integers) and values are lists of words.
    """
    lines = {}
    for word in words:
        y_center = int((word['top'] + word['bottom']) / 2)
        found = False
        for y in lines:
            if abs(y - y_center) < tolerance:
                lines[y].append(word)
                found = True
                break
        if not found:
            lines[y_center] = [word]
    return lines
