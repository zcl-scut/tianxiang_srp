'''
@function 头部姿态评估函数库
'''
import numpy as np

def get_euler_angles_from_rotation_matrix(matrix_lst):
    """
    根据旋转矩阵(rotation_matrix)获取欧拉角(euler_angle)
    Args:
        matrix_lst: 列表形式的旋转矩阵
    return: 
        Euler angles：欧拉角
    """
    euler_angles_lst = []
    for matrix in matrix_lst:
        m00 = matrix[0][0]
        m02 = matrix[0][2]
        m10 = matrix[1][0]
        m11 = matrix[1][1]
        m12 = matrix[1][2]
        m20 = matrix[2][0]
        m22 = matrix[2][2]

        if m10 > 0.998:
            roll = 0
            pitch = np.pi/2
            yaw = np.arctan2(m02, m22)
        elif m10 < -0.998:
            roll = 0
            pitch = -np.pi/2
            yaw = np.arctan2(m02, m22)
        else:
            roll = np.arctan2(-m12, m11)
            pitch = np.arcsin(m10)
            yaw = np.arctan2(-m20, m00)
        euler_angles_lst.append(np.rad2deg(np.array([pitch, yaw, roll])))
    return  np.array(euler_angles_lst)


def naive_pca(data):
    """A simplified pca

    Args:
        data: input data
    Return:
        components
    """
    X = np.copy(data)
    X -= np.mean(X, axis=0)
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    return vt


def get_direction_from_landmarks(landmarks_lst: np.ndarray) -> np.ndarray:
    """
    根据脸部特征点获取朝向
    Args:
        landmarks_lst: 脸部关键点数据集
    Returns:
        N x 3 vector which can indicate faces' directions.
    """
    direction_lst = []
    for landmarks in landmarks_lst:
        components = naive_pca(landmarks[17:])
        direction_h = components[1]
        if np.dot(direction_h, landmarks[45]-landmarks[36]) < 0:
            direction_h *= -1
        direction_h /= np.linalg.norm(direction_h)

        direction_v = components[0]
        if np.dot(direction_v, landmarks[30]-landmarks[8]) < 0:
            direction_v *= -1
        direction_v /= np.linalg.norm(direction_v)

        direction_d = components[2]
        if np.dot(direction_d, landmarks[30] - (landmarks[31]+landmarks[35]) / 2) < 0:
            direction_d *= -1
        direction_d /= np.linalg.norm(direction_d)
        direction_lst.append(np.array([direction_h, direction_v, direction_d]))
    return np.array(direction_lst)


def estimate_best_rotation(transformed_lst: np.ndarray) -> np.ndarray:
    """Find optimal rotation between corresponding 3d points.
    Args:
        transformed_lst: batch of rotated points.
    Returns:
        Rotation matrix：旋转矩阵
    """
    rotation_matrix_lst = []
    origin = np.identity(3)
    for transformed in transformed_lst:
        transformed = np.asarray(transformed)
        if transformed.ndim != 2 or transformed.shape[-1] != 3:
            raise ValueError("Expected input `transformed` to have shape (N, 3), "
                                "got {}".format(transformed.shape))
        origin = np.asarray(origin)
        if origin.ndim != 2 or origin.shape[-1] != 3:
            raise ValueError("Expected input `origin` to have shape (N, 3), "
                                "got {}.".format(origin.shape))

        if transformed.shape != origin.shape:
            raise ValueError("Expected inputs `transformed` and `origin` to have same shapes"
                                ", got {} and {} respectively.".format(
                                transformed.shape, origin.shape))

        H = np.einsum('ji,jk->ik', transformed, origin)
        u, s, vt = np.linalg.svd(H)

        # Correct improper rotation if necessary (as in Kabsch algorithm)
        if np.linalg.det(u @ vt) < 0:
            s[-1] = -s[-1]
            u[:, -1] = -u[:, -1]
        rotation_matrix_lst.append(np.dot(u, vt))
    return np.array(rotation_matrix_lst)


def estimate_head_pose(landmarks_lst: np.ndarray, debug=False) -> np.ndarray:
    """
    头部姿态进行评估
    Args:
        landmarks_lst: 脸部的3D特征点
        debug: if true, return detail information.
    Returns:
        头部的yaw, pitch, roll
    """
    directions_lst = get_direction_from_landmarks(landmarks_lst)
    rotation_matrix_lst = estimate_best_rotation(directions_lst)
    euler_angle_lst = get_euler_angles_from_rotation_matrix(rotation_matrix_lst)
    if debug:
        return euler_angle_lst, directions_lst, landmarks_lst
    else:
        return euler_angle_lst
