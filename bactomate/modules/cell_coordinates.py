"""Straighten rod-shaped masks using arc length and signed local cross-sections.

Coordinates describe a geometric reference cell, not pole age or tracking.
The original pixel coordinates and physical distances remain available.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d, map_coordinates, distance_transform_edt
from scipy.spatial import cKDTree

GEOMETRY_VERSION = 'arc-length-local-width-capsule-v2'


def capsule_radius(position):
    """Half-width in the normalized reference: x=-.5..+.5, y=0..1."""
    y = np.asarray(position, dtype=float)
    cap = 1 / 6
    end = np.minimum(y, 1-y)
    radius = .5 * np.sqrt(np.clip(1-((cap-end)/cap)**2, 0, 1))
    return np.where((y >= 0) & (y <= 1), np.where(end >= cap, .5, radius), 0.)


def capsule_outline():
    y = np.linspace(0, 1, 257)
    r = capsule_radius(y)
    return np.r_[-r, r[::-1], -r[0]], np.r_[y, y[::-1], y[0]]


def _ordered_skeleton(mask):
    from skimage.morphology import skeletonize
    points = np.argwhere(skeletonize(mask))
    lookup = {tuple(p): i for i, p in enumerate(points)}
    neighbors = [[] for _ in points]
    for i, (y, x) in enumerate(points):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if not (dy or dx): continue
                j = lookup.get((y+dy, x+dx))
                # Remove diagonal shortcuts across an existing orthogonal corner.
                if j is not None and not (dy and dx and
                    ((y+dy, x) in lookup or (y, x+dx) in lookup)):
                    neighbors[i].append(j)
    ends = [i for i, adjacent in enumerate(neighbors) if len(adjacent) == 1]
    if len(ends) != 2 or any(len(n) > 2 for n in neighbors):
        raise ValueError('medial axis is branched, cyclic or too short. Curate this mask before straightening it.')
    chain = [ends[0]]
    previous = -1
    while chain[-1] != ends[1]:
        options = [i for i in neighbors[chain[-1]] if i != previous]
        if not options: raise ValueError('Disconnected medial axis.')
        previous = chain[-1]
        chain.append(options[0])
        if len(chain) > len(points): raise ValueError('Cyclic medial axis.')
    if len(chain) != len(points): raise ValueError('Disconnected medial axis.')
    return points[chain].astype(float)


def _resample(line):
    keep = np.r_[True, np.linalg.norm(np.diff(line, axis=0), axis=1) > 1e-6]
    line = line[keep]
    distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))]
    if len(line) < 2 or distance[-1] <= 0: raise ValueError('Cell axis is too short.')
    s = np.linspace(0, distance[-1], max(3, int(np.ceil(distance[-1]*2))+1))
    return np.column_stack([np.interp(s, distance, line[:, k]) for k in (0, 1)])


def _sample_mask(mask, points):
    shape = points.shape[:-1]
    padded = np.pad(mask.astype(float), 1)
    return map_coordinates(padded, (points.reshape(-1, 2)+1).T,
                           order=1, mode='constant', cval=0).reshape(shape)


def _cross_sections(mask, line, normal):
    reach = max(2., float(distance_transform_edt(mask).max())*3+2)
    steps = np.arange(0, reach+.25, .25)
    widths = []
    for sign in (-1, 1):
        points = line[:, None, :] + sign*normal[:, None, :]*steps[None, :, None]
        values = _sample_mask(mask, points)
        outside = values < .5
        first = np.argmax(outside, axis=1)
        first[~outside.any(axis=1)] = len(steps)-1
        low = np.maximum(first-1, 0)
        a = values[np.arange(len(line)), low]
        b = values[np.arange(len(line)), first]
        fraction = np.divide(a-.5, a-b, out=np.zeros_like(a), where=np.abs(a-b)>1e-12)
        widths.append(steps[low]+np.clip(fraction, 0, 1)*(steps[first]-steps[low]))
    return widths


def cell_coordinates(region, method='auto'):
    """Return per-pixel axial position, reference width and physical geometry."""
    if method not in ('auto', 'medial axis', 'principal axis'):
        raise ValueError('Unknown profile coordinate method.')
    pixels = region.coords.astype(float)
    origin = np.asarray(region.bbox[:2], float)
    coords = pixels-origin
    local = region.image
    centered = coords-coords.mean(axis=0)
    _, vectors = np.linalg.eigh(centered.T@centered)
    axis = vectors[:, -1]
    if axis[np.argmax(np.abs(axis))] < 0: axis = -axis
    requested = method
    skeleton = None
    if method != 'principal axis':
        try:
            skeleton = _ordered_skeleton(local)
        except ValueError:
            if method == 'medial axis' or region.solidity < .9:
                raise
        if skeleton is not None:
            sigma = max(.6, float(distance_transform_edt(local).max())*.3)
            skeleton = gaussian_filter1d(skeleton, sigma=sigma, axis=0, mode='nearest')
            if (skeleton[-1]-skeleton[0])@axis < 0: skeleton = skeleton[::-1]
            chord = skeleton[-1]-skeleton[0]
            length = np.linalg.norm(np.diff(skeleton, axis=0), axis=1).sum()
            deviation = np.abs(np.cross(chord, skeleton-skeleton[0]))/max(np.linalg.norm(chord), 1e-12)
            curved = length > 1.015*np.linalg.norm(chord) and deviation.max() > .75
            if method == 'auto': method = 'medial axis' if curved else 'principal axis'
        else:
            method = 'principal axis'
    if method == 'principal axis':
        axial = centered@axis
        line = coords.mean(axis=0)+np.array([axial.min()-.5, axial.max()+.5])[:, None]*axis
    else:
        line = skeleton
        # Smooth tangents at the tips, then extend beyond all pixel centres. The
        # old skeleton-only endpoints stopped inside caps and displaced pole foci.
        count = min(len(line)-1, max(2, int(distance_transform_edt(local).max())))
        before = line[count]-line[0]
        after = line[-1]-line[-1-count]
        before /= max(np.linalg.norm(before), 1e-12)
        after /= max(np.linalg.norm(after), 1e-12)
        reach = max(3., float(distance_transform_edt(local).max())*3)
        first_cap = coords[np.linalg.norm(coords-line[0], axis=1) <= reach]
        last_cap = coords[np.linalg.norm(coords-line[-1], axis=1) <= reach]
        low = min(0., ((first_cap-line[0])@before).min()-.5)
        high = max(0., ((last_cap-line[-1])@after).max()+.5)
        line = np.vstack([line[0]+low*before, line, line[-1]+high*after])
    line = _resample(line)
    ds = np.linalg.norm(np.diff(line, axis=0), axis=1)
    arclength = np.r_[0., np.cumsum(ds)]
    tangent = np.gradient(line, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1)[:, None], 1e-12)
    normal = np.c_[-tangent[:, 1], tangent[:, 0]]
    left, right = _cross_sections(local, line, normal)
    # Continuous segment projection, not a nearest-skeleton-vertex snap.
    segments = np.diff(line, axis=0)
    tree = cKDTree((line[:-1]+line[1:])/2)
    _, nearest = tree.query(coords, k=min(8, len(segments)))
    if nearest.ndim == 1: nearest = nearest[:, None]
    start = line[nearest]
    vector = segments[nearest]
    fraction = np.clip(np.sum((coords[:, None]-start)*vector, axis=2) /
                       np.maximum(np.sum(vector*vector, axis=2), 1e-12), 0, 1)
    projected = start+fraction[..., None]*vector
    pick = np.argmin(np.sum((coords[:, None]-projected)**2, axis=2), axis=1)
    idx = nearest[np.arange(len(coords)), pick]
    f = fraction[np.arange(len(coords)), pick]
    s = arclength[idx]+f*ds[idx]
    point = projected[np.arange(len(coords)), pick]
    n = normal[idx]*(1-f[:, None])+normal[idx+1]*f[:, None]
    n /= np.maximum(np.linalg.norm(n, axis=1)[:, None], 1e-12)
    transverse = np.sum((coords-point)*n, axis=1)
    negative = np.interp(s, arclength, left)
    positive = np.interp(s, arclength, right)
    radius = np.where(transverse < 0, negative, positive)
    lateral = np.clip(transverse/np.maximum(radius, .5), -1, 1)
    position = s/arclength[-1]
    width = 2*capsule_radius(position)*lateral
    return dict(u=2*position-1, v=width, length=arclength[-1], method=method,
                requested_method=requested, transverse_pixels=transverse,
                axis_s=arclength/arclength[-1], axis_width=left+right,
                centerline=line+origin, geometry_version=GEOMETRY_VERSION)


def interpolate_cell_map(u, v, intensity, bins, across):
    """Linear interpolation within measured support, never extrapolation/zero fill."""
    from scipy.interpolate import LinearNDInterpolator
    from scipy.spatial import QhullError
    x = -1+(np.arange(bins)+.5)*2/bins
    y = -1+(np.arange(across)+.5)*2/across
    xx, yy = np.meshgrid(x, y, indexing='ij')
    try:
        # NaN-valued source vertices stay in the triangulation so missing signal
        # is not silently bridged by triangulating only the finite pixels.
        values = LinearNDInterpolator(np.c_[u, v], intensity)(xx, yy)
    except (QhullError, ValueError):
        values = np.full(xx.shape, np.nan)
    values[np.abs(yy) > 2*capsule_radius((xx+1)/2)] = np.nan
    return x, y, values
