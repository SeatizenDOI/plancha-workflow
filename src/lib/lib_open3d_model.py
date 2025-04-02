# -*- coding: utf-8 -*-
"""
Created on Tue Aug  9 12:27:48 2022

@author: mjulien
"""
import numpy as np
import open3d as o3d

import matplotlib as mpl
from matplotlib import cm
import matplotlib.pyplot as plt

class MplColorHelper:

  def __init__(self, cmap_name, start_val, stop_val):
    self.cmap_name = cmap_name
    self.cmap = plt.get_cmap(cmap_name)
    self.norm = mpl.colors.Normalize(vmin=start_val, vmax=stop_val)
    self.scalarMap = cm.ScalarMappable(norm=self.norm, cmap=self.cmap)

  def get_rgb(self, val):
    rgbval = self.scalarMap.to_rgba(val)
    return rgbval

def build_o3d_pointcloud(xyz,center=True):
    # recenter shapes to (0,0,0) by substracting min values
    if center == True:
        xyz[:,0] = xyz[:,0] - np.min(xyz[:,0])
        xyz[:,1] = xyz[:,1] - np.min(xyz[:,1])
        
    # build point cloud from xyz matrix
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    print(pcd)
    # calc some data set characteristics
    print('Estimating point cloud normals')
    pcd.estimate_normals()
    print('Computing point to point distance')
    avgdist     = np.mean(pcd.compute_nearest_neighbor_distance())
    stddist     = np.std(pcd.compute_nearest_neighbor_distance())
    stddist_rel = 100.0*stddist/avgdist
    print('--> avg dist = {0:.3f}m  and  rel std dev = {1:.3f}%'.format(avgdist,stddist_rel))
    # warning message to tell that that are not enough uniformly distributed 
    if stddist_rel > 10:
        print('--> warning : rel std dev > 10%, consider uniform resampling before surface reconstruction'.format(avgdist,stddist_rel))
    return pcd, avgdist , stddist

def build_o3d_trimesh(pcd,avgdist,method='ballpivot'):
    
    if method == 'alphashape':
        alpha = avgdist*5
        print('Starting reconstruction algo : alpha shape')
        print('alpha =',alpha)
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(pcd, alpha)
    elif method == 'ballpivot':
        print('Starting reconstruction algo : ball pivoting')
        # --> Typical rules to define the radius is : radii = 1.25*(pt avergae distance)/2
        radii =  o3d.utility.DoubleVector([avgdist/8,avgdist/4,avgdist/2,
                                           avgdist,avgdist*2,avgdist*4,avgdist*8])
        print('radii =',radii)
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, radii)
    else:
        print('[warning] unknown method. Using default algo : ball pivoting')
        # --> Typical rules to define the radius is : radii = 1.25*(pt avergae distance)/2
        radii =  o3d.utility.DoubleVector([avgdist/16,avgdist/8,avgdist/4,avgdist/2,
                                           avgdist,avgdist*2,avgdist*4,avgdist*8,avgdist*16])
        print('radii =',radii)
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, radii)
         
    print('Computing vertex normals')
    mesh.compute_vertex_normals()
    
    print('Coloring mesh according to z coordinates')
    xyz = np.asarray(pcd.points)
    # instanciate color helper
    colhelper = MplColorHelper('Spectral', np.min(xyz[:,2]), np.max(xyz[:,2]))
    # assign color to mesh
    meshcol = colhelper.get_rgb(xyz[:,2])[:,[0,1,2]]
    mesh.vertex_colors = o3d.utility.Vector3dVector(meshcol)

    return mesh