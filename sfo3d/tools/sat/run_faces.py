from faces import *
FACES = [
 # label, image, axis, c (face line), a0, a1, out
 ('A west',  'd82848c4', 't', -799.0, -1330, -975, -1),
 ('A east',  'd82848c4', 't', -760.3, -1330, -975, +1),
 ('B east',  'b1d51b0f', 't', -384.4, -1290, -900, +1),
 ('B west',  'b1d51b0f', 't', -435.9, -1290, -990, -1),
 ('C north', '03dcd4ae', 's', -665.2, -490, -310, +1),
 ('C south', '03dcd4ae', 's', -697.5, -490, -310, -1),
 ('E east',  'c235f3b8', 't', -687.5, -460, -280, +1),
 ('E west',  'c235f3b8', 't', -732.3, -460, -280, -1),
 ('F north', '39176bb8', 's', -368.1, -1290, -1030, +1),
 ('F south', '39176bb8', 's', -406.7, -1290, -1030, -1),
 ('F stem E','39176bb8', 't', -990.1, -360, -260, +1),
 ('F stem W','39176bb8', 't', -1016.5, -360, -260, -1),
 ('G north', '151ec51d', 's', -733.1, -1420, -1000, +1),
 ('G south', '151ec51d', 's', -771.4, -1420, -1000, -1),
]
if __name__ == '__main__':
    res = {}
    for lbl, img, axis, c, a0, a1, o in FACES:
        coord, prof, cover, pk = face_profile(img, axis, c, a0, a1, o)
        out = []
        for p in pk:
            nd = nose_along(img, axis, c, p[0], o)
            out.append((round(p[0], 1), round(p[1], 2), None if nd is None else round(nd, 1)))
        res[lbl] = out
        print(f'{lbl:9s}', out)
    json.dump(res, open(LSP + 'faces.json', 'w'), indent=1)
