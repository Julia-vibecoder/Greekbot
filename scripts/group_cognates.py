#!/usr/bin/env python3
"""Rearrange CSV so that cognate words (sharing the same Greek root) are placed next to each other."""

import csv
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'notion_part6_glossary.csv')

# Cognate groups defined by 1-indexed line numbers (line 1 = header).
# The order within each group is the desired output order.
COGNATE_GROUPS = {
    1:  [407, 408, 19],
    2:  [18, 185],
    3:  [284, 285, 286, 287],
    4:  [299, 300],
    5:  [303, 304],
    6:  [306, 307, 308],
    7:  [294, 295],
    8:  [296, 297],
    9:  [315, 317, 318, 319],
    10: [324, 325],
    11: [329, 330],
    12: [333, 334],
    13: [346, 347],
    14: [348, 349],
    15: [355, 356],
    16: [359, 360],
    17: [361, 362],
    18: [373, 374, 375, 376],
    19: [399, 400],
    20: [412, 413],
    21: [414, 415],
    22: [420, 421, 422],
    23: [423, 424],
    24: [425, 426],
    25: [427, 428],
    26: [433, 434],
    27: [435, 436, 437],
    28: [438, 439],
    29: [440, 441],
    30: [442, 443],
    31: [444, 445, 446],
    32: [449, 450, 453],
    33: [455, 456],
    34: [458, 459],
    35: [462, 466, 467, 468],
    36: [464, 465],
    37: [498, 499, 500],
    38: [518, 519, 520, 521, 522, 523, 524, 525, 526],
    39: [563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574],
    40: [575, 576],
    41: [577, 578],
    42: [579, 580],
    43: [581, 582],
    44: [588, 589],
    45: [590, 591],
    46: [592, 593, 594],
    47: [600, 601],
    48: [388, 389, 390],
    49: [634, 635],
    50: [636, 637],
    51: [639, 640],
    52: [631, 647],
    53: [665, 666],
    54: [662, 663, 664],
    55: [675, 676],
    56: [677, 678],
    57: [691, 692, 693],
    58: [700, 701, 702],
    59: [706, 707, 708],
    60: [711, 712, 713],
    61: [715, 716],
    62: [724, 725],
    63: [797, 798, 799],
    64: [803, 804],
    65: [814, 815],
    66: [548, 549],
    67: [552, 553],
    68: [554, 555],
    69: [546, 547],
    70: [482, 483],
    71: [486, 487],
    72: [755, 756],
    73: [759, 760],
    74: [749, 750, 751],
    75: [735, 736, 903, 904],
    76: [927, 928, 929, 930],
    77: [777, 778, 779, 780],
    78: [782, 783, 784],
    79: [771, 772],
    80: [957, 958],
    81: [840, 841],
    82: [871, 872, 873],
    83: [952, 953],
    84: [683, 684, 685, 686],
    85: [890, 891],
    86: [794, 795],
    87: [915, 916],
    88: [911, 912],
    89: [907, 908],
    90: [544, 775],
    91: [490, 491, 493],
    92: [822, 823],
    93: [291, 292],
    94: [728, 829, 884, 764],
    95: [332, 338],
    96: [595, 596, 597, 598],
    97: [418, 419],
}


def main():
    # Read the CSV file as raw lines to preserve exact formatting
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        all_rows = list(reader)

    old_count = len(all_rows)
    print(f"Old line count: {old_count}")

    header = all_rows[0]
    # data_rows is 0-indexed; line number N (1-indexed) corresponds to data_rows[N-2] for N>=2
    data_rows = all_rows[1:]

    # Build a mapping: 1-indexed line number -> group id
    line_to_group = {}
    for gid, lines in COGNATE_GROUPS.items():
        for ln in lines:
            assert ln >= 2, f"Line {ln} is header or invalid"
            line_to_group[ln] = gid

    # Track which groups have already been placed
    placed_groups = set()
    result = []

    for i, row in enumerate(data_rows):
        line_num = i + 2  # 1-indexed line number (header is line 1)

        if line_num in line_to_group:
            gid = line_to_group[line_num]
            if gid in placed_groups:
                # Already placed this group earlier, skip
                continue
            # Place the entire group now, in the defined order
            placed_groups.add(gid)
            for member_line in COGNATE_GROUPS[gid]:
                member_idx = member_line - 2  # convert to 0-indexed into data_rows
                result.append(data_rows[member_idx])
        else:
            # Not part of any cognate group, place as-is
            result.append(row)

    # Reassemble with header
    output = [header] + result
    new_count = len(output)
    print(f"New line count: {new_count}")
    assert old_count == new_count, f"Line count mismatch: {old_count} vs {new_count}"

    # Write back
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(output)

    print(f"Groups consolidated: {len(placed_groups)}")
    print("Done. File written successfully.")


if __name__ == '__main__':
    main()
