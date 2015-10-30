import numpy as np

from numba import jit

#---------------------------------

def index_to_zyx(index, MC):
    ny, nx = MC['ny'], MC['nx']
    z = index // (ny*nx)
    index = index % (ny*nx)
    y = index // nx
    x = index % nx
    return np.array((z, y, x))

def zyx_to_index(z, y, x, MC):
    ny, nx = MC['ny'], MC['nx']
    return ny*nx*z + nx*y + x

#---------------------------------

# @jit(nopython=True)
def expand_indexes(indexes, MC):
    # Expand a given set of indexes to include the nearest
    # neighbour points in all directions.
    # indexes is an array of grid indexes
    
    nz, ny, nx = MC['nz'], MC['ny'], MC['nx']
                    
    K_J_I = index_to_zyx( indexes, MC )

    stack_list = [K_J_I, ]
    for item in ((-1, 0, 0), (1, 0, 0),
                 (0, -1, 0), (0, 1, 0), 
                 (0, 0, -1), (0, 0, 1)):
        stack_list.append( K_J_I + np.array(item)[:, np.newaxis] )
    
    expanded_index = np.hstack(stack_list)

    # re-entrant domain
    expanded_index[0, expanded_index[0, :] == nz] = nz-1
    expanded_index[0, expanded_index[0, :] < 0] = 0
    expanded_index[1, :] = expanded_index[1, :]%ny
    expanded_index[2, :] = expanded_index[2, :]%nx

    # convert back to indexes
    expanded_index = zyx_to_index(expanded_index[0, :],
                                  expanded_index[1, :],
                                  expanded_index[2, :],
                                  MC)

    expanded_index = np.unique(expanded_index).astype(np.int)

    return expanded_index

#---------------------------

def find_halo(indexes, MC):
    # Expand the set of core points to include the nearest 
    # neighbour points in all directions.
    new_indexes = expand_indexes(indexes, MC)

    # From the expanded mask, select the points outside the core
    # expand_index_list returns only unique values,
    # so we don't have to check for duplicates.
    halo = np.setdiff1d(new_indexes, indexes, assume_unique=True)

    return halo

#---------------------------

def calc_distance(point1, point2, MC):
    # Calculate distances corrected for reentrant domain
    ny, nx = MC['ny'], MC['nx']
        
    delta_x = np.abs(point2[2, :] - point1[2, :])
    mask = delta_x >= (nx/2)
    delta_x[mask] = nx - delta_x[mask]
                    
    delta_y = np.abs(point2[1, :] - point1[1, :])
    mask = delta_y >= (ny/2)
    delta_y[mask] = ny - delta_y[mask]
                                
    delta_z = point2[0, :] - point1[0, :]
                                    
    return np.sqrt(delta_x**2 + delta_y**2 + delta_z**2)
                                        
#---------------------------

def calc_radii(data, reference, MC):
    ny, nx = MC['ny'], MC['nx']
    data_points = index_to_zyx(data, MC)
    ref_points = index_to_zyx(reference, MC)
    
    result = np.ones(data.shape, np.float)*(nx + ny)

    k_values = np.unique(ref_points[0,:])
    
    for k in k_values:
        data_mask = data_points[0, :] == k
        ref_mask = ref_points[0, :] == k
        
        k_data = data_points[:, data_mask]
        k_ref = ref_points[:, ref_mask]
        
        m = k_data.shape[1]
        n = k_ref.shape[1]
        
        k_data = k_data[:, :, np.newaxis] * np.ones((3, m, n))
        k_ref = k_ref[:, np.newaxis, :] * np.ones((3, m, n))
        
        distances = calc_distance(k_data, k_ref, MC)
        
        result[data_mask] = distances.min(1)

    return result
