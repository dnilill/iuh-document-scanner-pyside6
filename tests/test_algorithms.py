import itertools
import numpy as np
import cv2
import pytest
from scan_app import algorithms as alg
from scan_app.image_io import read_image, write_image
from tests.reference import resize_rotate as rr, perspective as pp


@pytest.fixture
def image():
    return np.random.default_rng(2026).integers(0, 256, (60, 90, 3), dtype=np.uint8)


@pytest.mark.parametrize('interp', list(alg.INTERPOLATIONS))
@pytest.mark.parametrize('args', [{'scale': .5}, {'width': 45}, {'height': 120},
                                 {'width': 80, 'height': 40, 'keep_aspect_ratio': False}])
def test_resize_matches_notebook(image, interp, args):
    assert np.array_equal(alg.resize_image(image, interpolation=interp, **args),
                          rr.resize_image(image, interpolation=interp, **args))


def test_resize_aspect_bug(image):
    assert rr.resize_image(image, width=80, height=80).shape == (80, 80, 3)
    result = alg.resize_image(image, width=80, height=80)
    assert result.shape == (53, 80, 3)


@pytest.mark.parametrize('kwargs', [{}, {'scale': 0}, {'scale': -1}, {'scale': float('nan')},
    {'width': 0}, {'width': 5.5}, {'width': 90, 'keep_aspect_ratio': False}, {'scale': 1000}])
def test_invalid_resize(image, kwargs):
    with pytest.raises(ValueError):
        alg.resize_image(image, **kwargs)


@pytest.mark.parametrize('shape', [(4, 7, 3), (5, 6, 3), (1, 8, 3)])
@pytest.mark.parametrize('turns', [0, 1, 2, 3])
def test_rotation_preserves_pixels_at_right_angles(shape, turns):
    image = np.arange(np.prod(shape), dtype=np.uint8).reshape(shape)
    assert np.array_equal(alg.rotate_image(image, angle=turns*90), np.rot90(image, turns))


def test_rotation_clipping_fixed(image):
    result = alg.rotate_image(image, angle=17)
    corners = np.array([[-.5, -.5], [89.5, -.5], [89.5, 59.5], [-.5, 59.5]])
    M = cv2.getRotationMatrix2D((44.5, 29.5), 17, 1)
    M[0, 2] += (result.shape[1]-1)/2 - 44.5
    M[1, 2] += (result.shape[0]-1)/2 - 29.5
    transformed = corners @ M[:, :2].T + M[:, 2]
    assert transformed.min() >= -.500001
    assert transformed[:, 0].max() <= result.shape[1]-.5
    assert transformed[:, 1].max() <= result.shape[0]-.5


@pytest.mark.parametrize('interp', list(alg.PERSPECTIVE_INTERPOLATIONS))
@pytest.mark.parametrize('border', list(alg.BORDER_MODES))
def test_perspective_matches_notebook(image, interp, border):
    points = [[5, 4], [80, 2], [84, 54], [3, 57]]
    original = pp.perspective_transform(image, points, interpolation=interp, border_mode=border)
    actual = alg.perspective_transform(image, points, interpolation=interp, border_mode=border)
    for expected, result in zip(original[:4], actual[:4]):
        np.testing.assert_array_equal(expected, result)


def test_diamond_order_is_unique_and_permutation_invariant():
    diamond = [[30, 0], [60, 30], [30, 60], [0, 30]]
    assert len(np.unique(pp.order_points(diamond), axis=0)) < 4
    expected = alg.order_points(diamond)
    for points in itertools.permutations(diamond):
        actual = alg.order_points(points)
        np.testing.assert_array_equal(expected, actual)
        assert len(np.unique(actual, axis=0)) == 4


@pytest.mark.parametrize('points', [
    [[0, 0], [0, 0], [20, 20], [0, 20]],
    [[0, 0], [10, 0], [20, 0], [30, 0]],
    [[0, 0], [30, 0], [10, 10], [0, 30]],
    [[0, 0], [30, 0], [30, .1], [0, .1]],
    [[0, 0], [30, 0], [30, 30], [0, np.nan]],
])
def test_invalid_corners(points):
    with pytest.raises(ValueError):
        alg.order_points(points)


def test_perspective_identity_and_reprojection(image):
    pts = [[0, 0], [89, 0], [89, 59], [0, 59]]
    result, info = alg.scan_perspective(image, pts, output_width=90, output_height=60)
    np.testing.assert_array_equal(result, image)
    assert info['reprojection_max_px'] < 1e-3
    with pytest.raises(ValueError):
        alg.scan_perspective(image, pts, output_width=1)
    with pytest.raises(ValueError):
        alg.scan_perspective(image, [[0, 0], [99, 0], [99, 59], [0, 59]])


def test_resize_metrics_match_notebook(image):
    result = alg.resize_image(image, scale=.5)
    before, after = rr.evaluate_resize(image, result), alg.evaluate_resize(image, result)
    assert before['MSE'] == after['MSE']
    assert before['PSNR (dB)'] == after['PSNR (dB)']
    assert before['SSIM'] == after['SSIM (cửa sổ)']


@pytest.mark.parametrize('size', [1, 2, 3, 4, 5, 6])
def test_small_metrics(size):
    image = np.zeros((size, size, 3), np.uint8)
    info = alg.evaluate_resize(image, image)
    assert info['SSIM (cửa sổ)'] == (None if size < 3 else 1.0)


def test_global_metrics_preserved(image):
    other = cv2.GaussianBlur(image, (3, 3), 0)
    for name in ['mse', 'psnr', 'ssim_global', 'laplacian_variance']:
        args = (image,) if name == 'laplacian_variance' else (image, other)
        assert getattr(alg, name)(*args) == pytest.approx(getattr(pp, name)(*args))


def test_unicode_io(tmp_path, image):
    path = tmp_path / 'tài liệu tiếng Việt.png'
    write_image(path, image)
    np.testing.assert_array_equal(read_image(path), image)


def test_synthetic_ground_truth():
    doc = pp.make_synthetic_document()
    src = np.float32([[0, 0], [699, 0], [699, 499], [0, 499]])
    points = np.float32([[120, 80], [760, 40], [820, 610], [80, 650]])
    distorted = cv2.warpPerspective(doc, cv2.getPerspectiveTransform(src, points), (900, 700),
                                    borderValue=(220, 220, 220))
    restored, info = alg.scan_perspective(distorted, points, output_width=700, output_height=500)
    assert info['reprojection_max_px'] < 1e-3
    assert alg.psnr(doc, restored) > 20
    assert alg.ssim_global(doc, restored) > .9
