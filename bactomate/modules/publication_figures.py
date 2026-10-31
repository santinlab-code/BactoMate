"""Publication layouts for cell profiles and explicitly defined intensity maxima."""
import numpy as np
import pandas as pd


def maxima_points(base, coords, u, v, intensity, foci):
    """Keep raw pixel coordinates alongside normalized cell coordinates.

    Maxima are brightest *pixels*, not inferred foci. Equal maxima use the first
    pixel in row-major order. Detected foci are separate rows and never invented.
    """
    rows=[]
    brightest=int(np.nanargmax(intensity)) if np.isfinite(intensity).any() else None
    selected=[] if brightest is None else [('maximum',brightest,None)]
    if foci is not None and not foci.empty:
        transform=np.linalg.lstsq(np.c_[coords,np.ones(len(coords))],np.c_[u,v],rcond=None)[0]
        for _,focus in foci.iterrows():
            if int(focus.get('frame',0))!=base['frame']:continue
            xy=np.array([float(focus['y']),float(focus['x'])])
            distances=np.sum((coords-xy)**2,axis=1)
            idx=int(np.argmin(distances))
            # Only foci inside this cell; no dilation into neighbouring cells.
            if distances[idx]>.51:continue
            selected.append(('focus',idx,focus))
    for kind,idx,focus in selected:
        pu,pv=(u[idx],v[idx]) if focus is None else np.clip(np.r_[float(focus['y']),float(focus['x']),1]@transform,-1,1)
        # Medial-axis coordinates are non-linear: use the nearest measured pixel.
        if base['profile_method']=='medial axis':pu,pv=u[idx],v[idx]
        rows.append(dict(**base,profile=kind,position=float(pu),transverse=float(pv),
                         relative_position=float((pu+1)/2),relative_width=float(pv/2),
                         x_px=float(coords[idx,1] if focus is None else focus['x']),
                         y_px=float(coords[idx,0] if focus is None else focus['y']),
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
    density,xe,ye=np.histogram2d(plot.x,plot.y,bins=spec.density_bins,range=[[-.55,.55],[-.05,1.05]])
    density=gaussian_filter(density.astype(float),sigma=spec.density_sigma)
    if density.max()>0:density/=density.max()
    density[density<.01]=np.nan
    im=ax.imshow(density.T,extent=[xe[0],xe[-1],ye[0],ye[-1]],origin='lower',
                 cmap=spec.cmap,vmin=0,vmax=1,aspect='auto',interpolation='nearest')
    if spec.show_points:ax.scatter(plot.x,plot.y,s=5,c='black',alpha=.65,rasterized=False)
    # A schematic capsule only: never clip or move measured points to its outline.
    angle=np.linspace(0,np.pi,100)
    x=np.r_[.5*np.cos(angle),.5*np.cos(angle+np.pi),.5]
    y=np.r_[1-1/6+np.sin(angle)/6,1/6+np.sin(angle+np.pi)/6,1-1/6]
    ax.plot(x,y,color='.25',linewidth=1)
    ax.set_xlim(-.58,.58);ax.set_ylim(1.05,-.05)
    cax=ax.inset_axes([1.04,0,.04,1])
    figure.colorbar(im,cax=cax,label=labels['colorlabel'])
    return im
