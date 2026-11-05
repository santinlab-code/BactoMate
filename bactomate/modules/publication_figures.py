"""Publication layouts for cell profiles and explicitly defined intensity maxima."""
import numpy as np
import pandas as pd


def maxima_points(base, coords, u, v, intensity, foci, *, normal_distance=None):
    """Keep raw pixel coordinates alongside normalized cell coordinates.

    Maxima are brightest *pixels*, not inferred foci. Equal maxima use the first
    pixel in row-major order. Detected foci are separate rows and never invented.
    """
    rows=[]
    brightest=int(np.nanargmax(intensity)) if np.isfinite(intensity).any() else None
    selected=[] if brightest is None else [('maximum',brightest,None)]
    if foci is not None and not foci.empty:
        lookup={tuple(map(int,p)):i for i,p in enumerate(coords)}
        for _,focus in foci.iterrows():
            if int(focus.get('frame',0))!=base['frame']:continue
            xy=np.array([float(focus['y']),float(focus['x'])])
            distances=np.sum((coords-xy)**2,axis=1)
            idx=int(np.argmin(distances))
            # Only foci inside this cell; no dilation into neighbouring cells.
            if distances[idx]>.51:continue
            selected.append(('focus',idx,focus))
    for kind,idx,focus in selected:
        pu,pv=u[idx],v[idx]
        raw_normal=float(normal_distance[idx]) if normal_distance is not None else np.nan
        if focus is not None:
            # Interpolate the measured nonlinear cell coordinates locally. An
            # affine fit over the entire curved cell displaces its pole foci.
            y,x=float(focus['y']),float(focus['x']);y0,x0=int(np.floor(y)),int(np.floor(x))
            weights=[];values=[]
            for yy,wy in ((y0,1-(y-y0)),(y0+1,y-y0)):
                for xx,wx in ((x0,1-(x-x0)),(x0+1,x-x0)):
                    k=lookup.get((yy,xx))
                    if k is not None and wy*wx>0:
                        weights.append(wy*wx);values.append((u[k],v[k]))
            if weights:
                pu,pv=np.average(values,axis=0,weights=weights)
                if normal_distance is not None:
                    normal_values=[]
                    for yy,wy in ((y0,1-(y-y0)),(y0+1,y-y0)):
                        for xx,wx in ((x0,1-(x-x0)),(x0+1,x-x0)):
                            k=lookup.get((yy,xx))
                            if k is not None and wy*wx>0:normal_values.append(normal_distance[k])
                    raw_normal=float(np.average(normal_values,weights=weights))
        rows.append(dict(**base,profile=kind,position=float(pu),transverse=float(pv),
                         relative_position=float((pu+1)/2),relative_width=float(pv/2),
                         x_px=float(coords[idx,1] if focus is None else focus['x']),
                         y_px=float(coords[idx,0] if focus is None else focus['y']),
                         axis_position_um=float((pu+1)/2*base.get('axis_length_um',np.nan)),
                         normal_distance_um=raw_normal,
                         intensity=float(intensity[idx]),pixel_count=1))
    return rows


def prepare_maxima(data,spec):
    if 'profile' in data:data=data[data.profile==spec.maxima_profile].copy()
    for column in (spec.x,spec.y):
        if not column or column not in data:raise ValueError('Maxima map needs relative width and relative position columns.')
    result=pd.DataFrame({'x':pd.to_numeric(data[spec.x],errors='coerce'),
                         'y':pd.to_numeric(data[spec.y],errors='coerce')},index=data.index)
    finite=np.isfinite(result).all(axis=1)
    if spec.minimum is not None:finite&=result.x.ge(spec.minimum)
    if spec.maximum is not None:finite&=result.x.le(spec.maximum)
    data=data.loc[finite].copy();result=result.loc[finite]
    if result.empty:raise ValueError('No maxima match this population. Build spatial profiles or choose another source.')
    if not result.x.between(-.5,.5).all() or not result.y.between(0,1).all():
        raise ValueError('Maxima coordinates must be normalized: width −0.5…0.5, length 0…1.')
    return data,result,dict(xlabel='Relative cell width',ylabel='Relative cell length',colorlabel='Relative point density')


def draw_maxima(figure,ax,plot,spec,labels):
    from scipy.ndimage import gaussian_filter
    from bactomate.modules.cell_coordinates import capsule_radius, capsule_outline
    density,xe,ye=np.histogram2d(plot.x,plot.y,bins=int(spec.density_bins),range=[[-.55,.55],[-.05,1.05]])
    density=gaussian_filter(density.astype(float),sigma=spec.density_sigma)
    xx,yy=np.meshgrid((xe[:-1]+xe[1:])/2,(ye[:-1]+ye[1:])/2,indexing='ij')
    density[np.abs(xx)>capsule_radius(yy)]=0
    if density.max()>0:density/=density.max()
    density[density<.01]=np.nan
    im=ax.imshow(density.T,extent=[xe[0],xe[-1],ye[0],ye[-1]],origin='lower',
                 cmap=spec.cmap,vmin=0,vmax=1,aspect='auto',interpolation='nearest')
    if spec.show_points:ax.scatter(plot.x,plot.y,s=spec.point_size,c='white' if spec.map_background=='black' else 'black',alpha=spec.point_alpha,rasterized=False)
    # Limit the displayed density kernel to the reference; measured points stay untouched.
    x,y=capsule_outline()
    ax.plot(x,y,color='white' if spec.map_background=='black' else '.25',linewidth=spec.line_width)
    ax.set_xlim(-.58,.58);ax.set_ylim(1.05,-.05)
    cax=ax.inset_axes([1.04,0,.04,1])
    figure.colorbar(im,cax=cax,label=labels['colorlabel'])
    return im
