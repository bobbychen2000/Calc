"""Consistency of registrations: SIFT matches between two registered screenshots -> world discrepancy of the same features."""
import sys, math, json
import numpy as np, cv2
from common import *
from featreg import load
from rectify import sim_of, REG
def matches(a, b, ratio=0.75):
    A, mA = load(a); B, mB = load(b)
    sift = cv2.SIFT_create(nfeatures=12000)
    kA, dA = sift.detectAndCompute(cv2.cvtColor(A, cv2.COLOR_BGR2GRAY), mA)
    kB, dB = sift.detectAndCompute(cv2.cvtColor(B, cv2.COLOR_BGR2GRAY), mB)
    if dA is None or dB is None: return None
    ms = cv2.BFMatcher(cv2.NORM_L2).knnMatch(dA, dB, k=2)
    good = [m for m, n in ms if m.distance < ratio * n.distance]
    if len(good) < 12: return None
    pA = np.float32([kA[m.queryIdx].pt for m in good]); pB = np.float32([kB[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(pA, pB, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=20000, confidence=0.999)
    if M is None or inl.sum() < 12: return None
    k = inl[:, 0] > 0
    return pA[k].astype(np.float64), pB[k].astype(np.float64)
if __name__ == '__main__':
    names = sys.argv[1:]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            r = matches(names[i], names[j])
            if r is None: print(names[i], names[j], 'no overlap'); continue
            pA, pB = r
            wA = sim_of(names[i]).inv(pA); wB = sim_of(names[j]).inv(pB)
            d = np.linalg.norm(wA - wB, axis=1)
            print(f'{names[i]} {names[j]}: {len(d)} matches, world discrepancy median {np.median(d):.1f} m, p90 {np.percentile(d, 90):.1f} m, mean offset {np.mean(wB - wA, 0).round(1)}')
