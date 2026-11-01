"""Native longitudinal measurements and explicit resampling to a common grid."""
import numpy as np
import pandas as pd


def native_profile(u,intensity,length_pixels,bins):
    count=max(2,int(np.ceil(length_pixels)))
    indices=np.minimum(((u+1)*count/2).astype(int),count-1)
    table=pd.DataFrame({'bin':indices,'intensity':intensity}).groupby('bin').intensity.agg(['mean','count'])
    positions=-1+(table.index.to_numpy()+.5)*2/count
    target=-1+(np.arange(bins)+.5)*2/bins
    valid=np.isfinite(table['mean'])
    values=np.interp(target,positions[valid],table['mean'][valid]) if valid.any() else np.full(bins,np.nan)
    return positions,table,target,values
