import cv2
import numpy as np
from skimage.measure import ransac
from skimage.transform import FundamentalMatrixTransform

np.set_printoptions(suppress=True)


def add_ones(x):
    """Turn [[x, y]] into [[x, y, 1]"""
    return np.concatenate([x, np.ones((x.shape[0], 1))], axis=1)


class Extractor:
    def __init__(self, K):
        self.orb = cv2.ORB_create()
        self.bf = cv2.BFMatcher_create(cv2.NORM_HAMMING)
        self.last = None
        self.K = K
        self.Kinv = np.linalg.inv(self.K)

    def normalise(self, pts):
        return np.dot(self.Kinv, add_ones(pts).T).T[:, 0:2]

    def denormalise(self, pt):
        ret = np.dot(self.K, np.array([pt[0], pt[1], 1.0]))
        return int(round(ret[0])), int(round(ret[1]))

    def extract(self, img):
        # detection
        grey = np.mean(img, axis=2).astype(np.uint8)
        feats = cv2.goodFeaturesToTrack(grey, 3000, 0.01, 3)

        # extraction
        kps = [cv2.KeyPoint(f[0][0], f[0][1], 20) for f in feats]
        kps, des = self.orb.compute(img, kps)

        # matching
        ret = []
        if self.last is not None:
            matches = self.bf.knnMatch(des, self.last['des'], k=2)
            for m, n in matches:
                if m.distance < 0.75 * n.distance:
                    kp1 = kps[m.queryIdx].pt
                    kp2 = self.last['kps'][m.trainIdx].pt
                    ret.append((kp1, kp2))

        # filter
        if len(ret) > 0:
            ret = np.array(ret)

            # normalise coords: subtract to move to 0
            ret[:, 0, :] = self.normalise(ret[:, 0, :])
            ret[:, 1, :] = self.normalise(ret[:, 1, :])

            model, inliers = ransac((ret[:, 0], ret[:, 1]),
                                    FundamentalMatrixTransform,
                                    min_samples=8,
                                    residual_threshold=1,
                                    max_trials=100)
            ret = ret[inliers]
            s, v, d = np.linalg.svd(model.params)
            print(v)

        self.last = {'kps': kps, 'des': des}
        return ret
