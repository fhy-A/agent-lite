"""模型分离性矩阵计算 — 简化版，复现 astropy#12907 的 bug"""

import numpy as np


def _coord_matrix(model, position, noutp):
    """生成坐标矩阵，标记每个输入对每个输出的依赖关系。"""
    if model is None:
        return np.zeros((noutp, 1))
    nout = getattr(model, "n_outputs", 1)
    mat = np.ones((nout, 1))
    return mat


def _cstack(left, right):
    """水平拼接两个坐标矩阵。"""
    noutp = left.shape[0]
    cleft = left
    if right is not None:
        cright = _coord_matrix(right, "right", noutp)
    else:
        cright = np.zeros((noutp, 1))
        cright[-1:, -1:] = 1
        return np.hstack([cleft, cright])

    # BUG: 当 right 不为 None 时，错误地将子矩阵赋值为 1
    # 而应该赋值为 right 矩阵本身
    cright[-right.shape[0]:, -right.shape[1]:] = right
    #                                      ^^^ 这里应该是 `= right`

    return np.hstack([cleft, cright])


def separability_matrix(model):
    """计算模型的分离性矩阵。

    返回一个 n_outputs × n_inputs 的矩阵，元素 (i,j) 为 1
    表示输出 i 依赖于输入 j。
    """
    noutp = getattr(model, "n_outputs", 1)
    left_mat = np.ones((noutp, 1))
    right_mat = _coord_matrix(None, "right", noutp)
    return _cstack(left_mat, right_mat)
