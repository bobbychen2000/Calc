"""Register screenshot B from SIFT correspondences pooled over several georeferenced screenshots (each match gives a
world point from its reference's registration). Similarity fit with RANSAC over the pooled set."""
import sys, math
import numpy as np, cv2
from common import *
from featreg import load
from manual import fit_points, save
from rectify import sim_of
def pooled(b, refs, ratio=0.78):
    B, mB = load(b)
    sift = cv2.SIFT_create(nfeatures=20000)
    kB, dB = sift.detectAndCompute(cv2.cvtColor(B, cv2.COLOR_BGR2GRAY), mB)
    Wall, Pall, src = [], [], []
    for a in refs:
        A, mA = load(a)
        kA, dA = sift.detectAndCompute(cv2.cvtColor(A, cv2.COLOR_BGR2GRAY), mA)
        ms = cv2.BFMatcher(cv2.NORM_L2).knnMatch(dA, dB, k=2)
        good = [m for m, n in ms if m.distance < ratio * n.distance]
        if len(good) < 10: print('  ', a, 'too few matches', len(good)); continue
        pA = np.float32([kA[m.queryIdx].pt for m in good]); pB = np.float32([kB[m.trainIdx].pt for m in good])
        M, inl = cv2.estimateAffinePartial2D(pA, pB, method=cv2.RANSAC, ransacReprojThreshold=5.0, maxIters=20000, confidence=0.999)
        if M is None or inl.sum() < 10: print('  ', a, 'no consistent set', len(good)); continue
        k = inl[:, 0] > 0
        Wa = sim_of(a).inv(pA[k].astype(np.float64)); Pb = pB[k].astype(np.float64)
        print('  ', a, 'inliers', int(k.sum()), 'of', len(good), 'scale ratio', round(math.hypot(M[0, 0], M[1, 0]), 3))
        Wall.append(Wa); Pall.append(Pb); src += [a] * len(Wa)
    W = np.concatenate(Wall); P = np.concatenate(Pall)
    # robust similarity: iterative reweighting
    keep = np.ones(len(W), bool)
    for it in range(6):
        S = fit_points(W[keep], P[keep]); r = np.linalg.norm(S.fwd(W) - P, axis=1)
        thr = max(3.0, 2.5 * np.median(r[keep])); keep = r < thr
    S = fit_points(W[keep], P[keep]); r = np.linalg.norm(S.fwd(W) - P, axis=1)
    per = {a: float(np.median(r[np.array(src) == a])) for a in set(src)}
    return S, int(keep.sum()), float(np.median(r[keep])), per
if __name__ == '__main__':
    b = sys.argv[1]; refs = sys.argv[2].split(','); do_save = len(sys.argv) > 3
    S, nk, med, per = pooled(b, refs)
    print(f'{b}: s {S.s:.4f} th {S.th:.3f} kept {nk} median residual {med:.2f} px; per-ref median residual', {k: round(v, 1) for k, v in per.items()})
    if do_save: save(b, S, None, f'SIFT pooled over {refs}: {nk} pts, median {med:.2f} px')
