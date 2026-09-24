"""Register screenshot B via SIFT feature matches to an already georeferenced screenshot A (same imagery source)."""
import sys, json, math
import numpy as np, cv2
from common import *
from manual import fit_points, save
from rectify import sim_of
U = open(SP + 'uniq.txt').read().split()
def load(n):
    img = cv2.imread([u for u in U if n in u][0])
    m = np.zeros(img.shape[:2], np.uint8); m[340:2200, 10:1280] = 255
    m[330:910, 1070:] = 0; m[1880:, 1020:] = 0
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ui = ((hsv[..., 1] > 150) & (hsv[..., 2] > 150)) | (img.min(2) > 245)
    ui = cv2.dilate(ui.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    m[ui] = 0
    return img, m
def register(a, b, ratio=0.75):
    A, mA = load(a); B, mB = load(b)
    sift = cv2.SIFT_create(nfeatures=12000)
    kA, dA = sift.detectAndCompute(cv2.cvtColor(A, cv2.COLOR_BGR2GRAY), mA)
    kB, dB = sift.detectAndCompute(cv2.cvtColor(B, cv2.COLOR_BGR2GRAY), mB)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    ms = bf.knnMatch(dA, dB, k=2)
    good = [m for m, n in ms if m.distance < ratio * n.distance]
    pA = np.float32([kA[m.queryIdx].pt for m in good]); pB = np.float32([kB[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(pA, pB, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=20000, confidence=0.999)
    ni = int(inl.sum()) if inl is not None else 0
    if M is None or ni < 12: return None, ni, len(good)
    sAB = math.hypot(M[0, 0], M[1, 0])
    # world points from inliers in A -> B pixel coordinates
    SA = sim_of(a)
    WA = SA.inv(pA[inl[:, 0] > 0].astype(np.float64))
    PB = (pB[inl[:, 0] > 0]).astype(np.float64)
    sim = fit_points(WA, PB)
    res = np.linalg.norm(sim.fwd(WA) - PB, axis=1)
    return sim, ni, len(good), float(np.median(res)), sAB
if __name__ == '__main__':
    a, b = sys.argv[1], sys.argv[2]
    r = register(a, b)
    if r[0] is None: print('FAILED', r); sys.exit(1)
    sim, ni, ng, med, sAB = r
    print(f'{b} via {a}: inliers {ni}/{ng}, median residual {med:.2f} px, scale ratio {sAB:.3f} -> s {sim.s:.4f} th {sim.th:.3f}')
    if len(sys.argv) > 3 and sys.argv[3] == 'save': save(b, sim, None, f'SIFT via {a}: {ni} inliers, median {med:.2f}px')
