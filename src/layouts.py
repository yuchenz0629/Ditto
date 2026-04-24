"""
This dictionary outlines the layout of each number of images
I included 2 versions for each layout to support the change layout functionality
"""

LAYOUTS: dict[str, dict] = {
    "1-image": {
        "slots": [
            {"pos": 1, "cx": 0.50, "cy": 0.62, "w": 0.72, "h": 0.60, "angle": -3, "z": 1},
        ],
        "text_anchor": {"x": 0.08, "y": 0.07},
    },
    "2-image": {
        "slots": [
            # Support: upper-right, clear of text zone
            {"pos": 1, "cx": 0.69, "cy": 0.38, "w": 0.48, "h": 0.38, "angle":  5, "z": 1},
            # Hero: lower-center-left
            {"pos": 2, "cx": 0.35, "cy": 0.68, "w": 0.62, "h": 0.50, "angle": -4, "z": 2},
        ],
        "text_anchor": {"x": 0.07, "y": 0.07},
    },
    "3-image": {
        "slots": [
            # Support: upper-right, clear of text zone
            {"pos": 1, "cx": 0.68, "cy": 0.30, "w": 0.45, "h": 0.31, "angle":  6, "z": 1},
            # Support: mid-left (large)
            {"pos": 2, "cx": 0.27, "cy": 0.55, "w": 0.52, "h": 0.44, "angle": -5, "z": 2},
            # Hero: lower-center-left
            {"pos": 3, "cx": 0.57, "cy": 0.81, "w": 0.58, "h": 0.42, "angle": -3, "z": 3},
        ],
        "text_anchor": {"x": 0.07, "y": 0.07},
    },
    "4-image": {
        "slots": [
            # Support: upper-right, clear of text zone
            {"pos": 1, "cx": 0.68, "cy": 0.28, "w": 0.44, "h": 0.29, "angle":  6, "z": 1},
            # Support: mid-left (large)
            {"pos": 2, "cx": 0.27, "cy": 0.48, "w": 0.50, "h": 0.43, "angle": -5, "z": 2},
            # Support: mid-right
            {"pos": 3, "cx": 0.73, "cy": 0.62, "w": 0.46, "h": 0.33, "angle":  3, "z": 3},
            # Hero: lower-left
            {"pos": 4, "cx": 0.33, "cy": 0.84, "w": 0.54, "h": 0.39, "angle": -4, "z": 4},
        ],
        "text_anchor": {"x": 0.07, "y": 0.07},
    },
    "2-image-v2": {
        "slots": [
            # Support: center-left
            {"pos": 1, "cx": 0.30, "cy": 0.42, "w": 0.48, "h": 0.40, "angle": -6, "z": 1},
            # Hero: center-right, lower
            {"pos": 2, "cx": 0.65, "cy": 0.70, "w": 0.62, "h": 0.50, "angle":  4, "z": 2},
        ],
        "text_anchor": {"x": 0.07, "y": 0.07},
    },
    "3-image-v2": {
        "slots": [
            # Support: upper-right
            {"pos": 1, "cx": 0.68, "cy": 0.36, "w": 0.44, "h": 0.32, "angle": -6, "z": 1},
            # Support: mid-right
            {"pos": 2, "cx": 0.68, "cy": 0.56, "w": 0.48, "h": 0.36, "angle":  5, "z": 2},
            # Hero: lower-left, large
            {"pos": 3, "cx": 0.30, "cy": 0.78, "w": 0.56, "h": 0.42, "angle": -3, "z": 3},
        ],
        "text_anchor": {"x": 0.07, "y": 0.07},
    },
    "4-image-v2": {
        "slots": [
            # Support: upper-right
            {"pos": 1, "cx": 0.70, "cy": 0.30, "w": 0.42, "h": 0.28, "angle":  6, "z": 1},
            # Support: mid-right
            {"pos": 2, "cx": 0.70, "cy": 0.48, "w": 0.44, "h": 0.32, "angle": -4, "z": 2},
            # Support: lower-right
            {"pos": 3, "cx": 0.70, "cy": 0.72, "w": 0.42, "h": 0.30, "angle":  5, "z": 3},
            # Hero: left column, tall
            {"pos": 4, "cx": 0.27, "cy": 0.62, "w": 0.50, "h": 0.60, "angle": -3, "z": 4},
        ],
        "text_anchor": {"x": 0.07, "y": 0.07},
    },
}
