"""Brute force solve ball sort puzzle"""

def main():
    """Confirm game is valid, solve it, then post the steps"""
    game = [[1, 2, 3, 4], [3, 5, 6, 4], [7, 8, 8, 3], [8, 9, 9, 6], [10, 1, 8, 5], [11, 2, 12, 10], [11, 1, 6, 5],
            [1, 12, 12, 11], [7, 2, 4, 5], [11, 10, 10, 2], [4, 9, 7, 6], [7, 12, 3, 9], [], []]
    assert_valid(game)

def assert_valid(game):
    """Assert that the game has 4 of each color used and that there are two empty viles"""
    color_counts = {}
    for vile in game:
        for color in vile:
            if color_counts[color]:
                color_counts[color] = color_counts[color] + 1
            else:
                color_counts[color] = 1
    for key, value in color_counts.items():
        assert value == 4, f"Invalid color count (${value}) for color #${key}"
    assert len(game) == len(color_counts) + 2

if __name__ == '__main__':
    main()
